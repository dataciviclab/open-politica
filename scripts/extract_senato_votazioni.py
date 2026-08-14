#!/usr/bin/env python3
"""Estrazione votazioni Senato con voti individuali — SPARQL paginato.

Per ogni graph della legislatura (es. /19: votazioni-fasi-1..5, sindisp, doc):
1. estrae i metadati di ogni votazione (seduta, esito, conteggi),
2. estrae i voti individuali (favorevole/contrario/astenuto) paginati
   (l'endpoint Senato capisce a 10k righe per query),
3. arricchisce con la data della seduta,
4. scrive un unico parquet long-format (una riga per senatore×votazione).

Uso:
    python3 scripts/extract_senato_votazioni.py                 # XIX legislatura
    python3 scripts/extract_senato_votazioni.py --legislature 18
    python3 scripts/extract_senato_votazioni.py --out out/data/derived/senato_votazioni
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

OSR = "http://dati.senato.it/osr/"
ENDPOINT = "https://dati.senato.it/sparql"
VOTO_PROPS = [
    f"{OSR}favorevole",
    f"{OSR}contrario",
    f"{OSR}astenuto",
]
VOTO_LABEL = {
    f"{OSR}favorevole": "FAVOREVOLE",
    f"{OSR}contrario": "CONTRARIO",
    f"{OSR}astenuto": "ASTENUTO",
}
# FILTER IN valido: ogni IRI con le proprie parentesi angolari
VOTO_IN = "(" + ", ".join(f"<{p}>" for p in VOTO_PROPS) + ")"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("senato-votazioni")


def query(sparql: str, timeout: int = 120) -> list[dict]:
    """Esegue una SELECT via curl e restituisce i bindings con valori primitivi.

    Il WAF di dati.senato.it:
    - fa TLS-fingerprinting: le librerie Python ricevono 403/risposte vuote;
      il binario curl passa;
    - ha rate-limit per IP a burst: dopo poche query pesanti risponde 403
      (HTML) per ~1 minuto. Rileviamo l'HTML e attendiamo 90s prima di
      ritentare, con backoff progressivo.
    - serve risultati vuoti per query con variabili lunghe (vedi fetch_*).
    """
    attempts = [5, 15, 45, 90, 180, 300]
    for i, wait in enumerate(attempts):
        try:
            out = subprocess.run(
                ["curl", "-s", "--max-time", str(timeout), "-G", ENDPOINT,
                 "--data-urlencode", f"query={sparql}",
                 "-H", "Accept: application/sparql-results+json"],
                capture_output=True, text=True, check=True,
            ).stdout
            if out.lstrip().startswith("<") or out.lstrip().startswith("Virtuoso"):
                # HTML (403 WAF) o errore Virtuoso → throttle/limit: attesa lunga
                log.warning("risposta non-JSON (tentativo %d) — attesa %ds", i + 1, wait)
                time.sleep(wait)
                continue
            rows = json.loads(out)["results"]["bindings"]
            time.sleep(8)
            return [
                {k: v.get("value") for k, v in r.items()}
                for r in rows
            ]
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            log.warning("query fallita (tentativo %d): %s — attesa %ds", i + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"query fallita dopo {len(attempts)} tentativi: {sparql[:120]}...")


def discover_graphs(legislatura: int) -> list[str]:
    rows = query(f"""
        SELECT DISTINCT ?g WHERE {{
          GRAPH ?g {{ ?s a <{OSR}Votazione> }}
        }}
    """)
    return [r["g"] for r in rows if r["g"].endswith(f"/{legislatura}")]


def fetch_votazioni_meta(graph: str) -> list[dict]:
    """Metadati di tutte le votazioni in un graph (una riga per votazione).

    Nomi variabili corti: il WAF di dati.senato.it serve risultati vuoti
    per query con variabili lunghe (es. ?votazione) su alcuni pattern.
    """
    return query(f"""
        PREFIX osr: <{OSR}>
        SELECT ?v
               (MAX(?s) AS ?seduta) (MAX(?l) AS ?legislatura)
               (MAX(?tipo) AS ?tipoVotazione) (MAX(?es) AS ?esito)
               (MAX(?fav) AS ?favorevoli) (MAX(?con) AS ?contrari)
               (MAX(?ast) AS ?astenuti) (MAX(?vot) AS ?votanti)
               (MAX(?pres) AS ?presenti) (MAX(?maj) AS ?maggioranza)
               (MAX(?cong) AS ?congedoMissione)
        WHERE {{
          GRAPH <{graph}> {{
            ?v a osr:Votazione .
            OPTIONAL {{ ?v osr:seduta ?s . }}
            OPTIONAL {{ ?v osr:legislatura ?l . }}
            OPTIONAL {{ ?v osr:tipoVotazione ?tipo . }}
            OPTIONAL {{ ?v osr:esito ?es . }}
            OPTIONAL {{ ?v osr:favorevoli ?fav . }}
            OPTIONAL {{ ?v osr:contrari ?con . }}
            OPTIONAL {{ ?v osr:astenuti ?ast . }}
            OPTIONAL {{ ?v osr:votanti ?vot . }}
            OPTIONAL {{ ?v osr:presenti ?pres . }}
            OPTIONAL {{ ?v osr:maggioranza ?maj . }}
            OPTIONAL {{ ?v osr:congedoMissione ?cong . }}
          }}
        }}
        GROUP BY ?v
    """)


def fetch_voti(graph: str) -> list[dict]:
    """Voti individuali del graph, paginati (endpoint capisce a 10k righe)."""
    log.info("  voti individuali graph %s", graph.split("/")[-1])
    expected = query(f"""
        SELECT (COUNT(?sen) AS ?n) WHERE {{
          GRAPH <{graph}> {{
            ?v ?p ?sen .
            FILTER(?p IN {VOTO_IN})
          }}
        }}
    """)
    total = int(expected[0]["n"]) if expected and expected[0]["n"] else 0
    log.info("  graph %s: attesi %d voti", graph.split("/")[-1], total)
    if total == 0:
        return []

    voti: list[dict] = []
    offset = 0
    page = 10_000
    while True:
        rows = query(f"""
            SELECT ?v ?sen ?p WHERE {{
              GRAPH <{graph}> {{
                ?v ?p ?sen .
                FILTER(?p IN {VOTO_IN})
              }}
            }}
            LIMIT {page} OFFSET {offset}
        """)
        if not rows:
            # WAF può servire pagine vuote sotto rate-limit: attende e ritenta
            log.warning("  pagina vuota a OFFSET %d — retry", offset)
            time.sleep(10)
            rows = query(f"""
                SELECT ?v ?sen ?p WHERE {{
                  GRAPH <{graph}> {{
                    ?v ?p ?sen .
                    FILTER(?p IN {VOTO_IN})
                  }}
                }}
                LIMIT {page} OFFSET {offset}
            """)
            if not rows:
                raise RuntimeError(f"pagina vuota persistente a OFFSET {offset} ({graph})")
        voti.extend(rows)
        offset += page
        if offset % 100_000 == 0:
            log.info("  ... %d voti estratti", offset)
        if len(rows) < page:
            break
    log.info("  graph %s: %d voti estratti", graph.split("/")[-1], len(voti))
    if len(voti) != total:
        log.warning("  graph %s: estratti %d ma attesi %d — scarto", graph.split("/")[-1], len(voti), total)
    return voti


def fetch_voti_filtered(graph: str, votazioni: set[str], batch: int = 200) -> list[dict]:
    """Voti individuali SOLO per un set di votazioni (incremental).

    Deterministico: IN-list fissa per batch → OFFSET stabile dentro il batch
    (nessun overlap come la paginazione globale).
    """
    voti: list[dict] = []
    vlist = sorted(votazioni)
    for bi in range(0, len(vlist), batch):
        batch_v = vlist[bi:bi + batch]
        in_list = "<" + ">,<".join(batch_v) + ">"
        offset = 0
        while True:
            rows = query(f"""
                SELECT ?v ?sen ?p WHERE {{
                  GRAPH <{graph}> {{
                    ?v ?p ?sen .
                    FILTER(?p IN {VOTO_IN} && ?v IN ({in_list}))
                  }}
                }}
                LIMIT 10000 OFFSET {offset}
            """)
            voti.extend(rows)
            if len(rows) < 10000:
                break
            offset += 10000
    return voti


def fetch_sedute(legislatura: int) -> list[dict]:
    return query(f"""
        PREFIX osr: <{OSR}>
        SELECT ?s ?d WHERE {{
          ?s a osr:SedutaAssemblea ; osr:dataSeduta ?d .
          OPTIONAL {{ ?s osr:legislatura ?l . }}
          FILTER(?l = {legislatura})
        }}
    """)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legislature", type=int, default=19)
    parser.add_argument("--out", default="out/data/derived/senato_votazioni")
    parser.add_argument("--merge-only", action="store_true",
                        help="salta l'estrazione SPARQL e ri-merge i parquet già estratti")
    parser.add_argument("--incremental", action="store_true",
                        help="estrae solo le votazioni successive alla max data già presente")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / "senato_votazioni.parquet"

    all_meta: list[dict] = []
    voti_files: list[Path] = []
    last_date = None  # set in modalità incremental (per l'UNION nel merge)

    if not args.merge_only:
        graphs = discover_graphs(args.legislature)
        if not graphs:
            log.error("nessun graph trovato per la legislatura %d", args.legislature)
            return 1
        log.info("legislatura %d — %d graph: %s", args.legislature, len(graphs),
                 ", ".join(g.split("/")[-1] for g in graphs))

        # ── Incremental: determina le votazioni nuove (data > max esistente) ──
        last_date = None
        if args.incremental and final_path.exists():
            with duckdb.connect() as con:
                last_date = con.execute(
                    f"SELECT max(data) FROM read_parquet('{final_path}')"
                ).fetchone()[0]
            if last_date is None:
                log.info("incremental: parquet esistente senza date → full")
            else:
                log.info("incremental: max data esistente = %s", last_date)

        for g in graphs:
            meta = fetch_votazioni_meta(g)
            all_meta.extend(meta)

        # mappa votazione → data (via seduta) per filtrare le nuove
        if last_date is not None:
            sedute_map = {s["s"]: s["d"] for s in fetch_sedute(args.legislature)}
            new_votazioni = {
                m["v"] for m in all_meta
                if sedute_map.get(m["seduta"]) and str(sedute_map[m["seduta"]]) > str(last_date)
            }
            log.info("incremental: %d votazioni nuove (data > %s)", len(new_votazioni), last_date)
            if not new_votazioni:
                log.info("niente di nuovo — parquet invariato: %s", final_path)
                return 0
        else:
            new_votazioni = None

        for g in graphs:
            if last_date is not None:
                # solo i voti delle votazioni nuove presenti in questo graph
                meta_in_g = [m for m in all_meta if m["seduta"]]
                voti = fetch_voti_filtered(g, new_votazioni)
                voti = [v for v in voti if v["v"] in new_votazioni]
                log.info("  graph %s: %d voti nuovi", g.split("/")[-1], len(voti))
            else:
                meta_in_g = meta
                voti = fetch_voti(g)
            if not voti:
                log.warning("  graph %s: nessun voto", g.split("/")[-1])
                continue
            f = out_dir / f"voti_{g.rstrip('/').split('/')[-2]}.parquet"
            table = pa.table(
                {
                    "votazione": [v["v"] for v in voti],
                    "senatore": [v["sen"] for v in voti],
                    "voto": [VOTO_LABEL[v["p"]] for v in voti],
                }
            )
            pq.write_table(table, f)
            voti_files.append(f)

        log.info("metadati: %d votazioni", len(all_meta))
        sedute = fetch_sedute(args.legislature)
        log.info("sedute: %d", len(sedute))

        meta_t = pa.table(
            {
                "votazione": [m["v"] for m in all_meta],
                "seduta": [m["seduta"] for m in all_meta],
                "legislatura": [m["legislatura"] for m in all_meta],
                "tipo_votazione": [m["tipoVotazione"] for m in all_meta],
                "esito": [m["esito"] for m in all_meta],
                "n_favorevoli": [m["favorevoli"] for m in all_meta],
                "n_contrari": [m["contrari"] for m in all_meta],
                "n_astenuti": [m["astenuti"] for m in all_meta],
                "n_votanti": [m["votanti"] for m in all_meta],
                "n_presenti": [m["presenti"] for m in all_meta],
                "n_maggioranza": [m["maggioranza"] for m in all_meta],
                "n_congedo_missione": [m["congedoMissione"] for m in all_meta],
            }
        )
        sed_t = pa.table(
            {"seduta": [s["s"] for s in sedute], "data": [s["d"] for s in sedute]}
        )

        meta_path = out_dir / "meta.parquet"
        sed_path = out_dir / "sedute.parquet"
        pq.write_table(meta_t, meta_path)
        pq.write_table(sed_t, sed_path)
    else:
        voti_files = sorted(out_dir.glob("voti_*.parquet"))
        meta_path = out_dir / "meta.parquet"
        sed_path = out_dir / "sedute.parquet"
        log.info("merge-only: %d file voti", len(voti_files))
        if not voti_files:
            log.error("nessun file voti_*.parquet in %s", out_dir)
            return 1

    final_path = out_dir / f"senato_votazioni.parquet"
    log.info("merge in %s", final_path)
    existing_union = (
        f"UNION ALL SELECT * FROM read_parquet('{final_path}')" if last_date is not None else ""
    )
    with duckdb.connect() as con:
        globs = ", ".join(f"'{p}'" for p in voti_files)
        con.execute(f"""
            CREATE OR REPLACE TABLE finale AS
            SELECT * FROM (
            SELECT v.votazione,
                   TRY_CAST(REGEXP_EXTRACT(v.senatore, '(\\d+)$', 1) AS BIGINT) AS senatore_id,
                   v.voto,
                   m.seduta, m.legislatura, m.tipo_votazione, m.esito,
                   TRY_CAST(m.n_favorevoli AS INTEGER) AS n_favorevoli,
                   TRY_CAST(m.n_contrari AS INTEGER)   AS n_contrari,
                   TRY_CAST(m.n_astenuti AS INTEGER)   AS n_astenuti,
                   TRY_CAST(m.n_votanti AS INTEGER)    AS n_votanti,
                   TRY_CAST(m.n_presenti AS INTEGER)   AS n_presenti,
                   TRY_CAST(m.n_maggioranza AS INTEGER) AS n_maggioranza,
                   TRY_CAST(m.n_congedo_missione AS INTEGER) AS n_congedo_missione,
                   TRY_CAST(s.data AS DATE) AS data
            FROM read_parquet([{globs}]) v
            JOIN read_parquet('{meta_path}') m ON v.votazione = m.votazione
            LEFT JOIN read_parquet('{sed_path}') s ON m.seduta = s.seduta
            {existing_union}
            ) q
        """)
        con.execute(f"COPY (SELECT * FROM finale) TO '{final_path}' (FORMAT PARQUET)")
        n = con.execute("SELECT count(*) FROM finale").fetchone()[0]
        nv = con.execute("SELECT count(DISTINCT votazione) FROM finale").fetchone()[0]
    log.info("OK: %d righe, %d votazioni distinte → %s", n, nv, final_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
