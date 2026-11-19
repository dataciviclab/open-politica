#!/usr/bin/env python3
"""Estrazione votazioni Senato con voti individuali — SPARQL paginato.

Per ogni graph della legislatura (es. /19: votazioni-fasi-1..5, sindisp, doc):
1. estrae i metadati di ogni votazione (seduta, esito, conteggi),
2. estrae i voti individuali (favorevole/contrario/astenuto) paginati
   (l'endpoint Senato capisce a 10k righe per query),
3. arricchisce con la data della seduta,
4. scrive un unico parquet long-format (una riga per senatore×votazione).

Uso:
    python preprocess.py                 # XIX legislatura
    python preprocess.py --legislature 18
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from lab_connectors.http import execute_sparql_rows_curl

OSR = "http://dati.senato.it/osr/"
ENDPOINT = "https://dati.senato.it/sparql"

# Retry WAF: attese fra i tentativi e budget complessivo per run.
# Il budget limita l'ATTESA, non i tentativi: l'ultimo tentativo avviene
# comunque dopo l'ultima pausa (prima veniva rifiutato a budget esaurito).
# Default: 480s in incrementale (il blocco misurato dura >=257s), nessun
# tetto nel full (un'estrazione completa deve poter finire).
_RETRY_ATTEMPTS = (5, 15, 45, 90, 180, 300)
# L'endpoint rifiuta (403 immediato, non rate-limit) le query sopra ~1,5 KB:
# misurato il 2026-11-19 — 1.508 B ok, 1.568 B → 403. Il batch è quindi per
# LUNGHEZZA, non per numero di URI: la query meta ha una base ~800 B più lunga
# di quella voti (20 sedute = 1.968 B → 403 anche con "20 URI").
# La full non ha IN-list (pagina per graph); l'incrementale sì.
_QUERY_MAX_CHARS = 1300
_RETRY_BUDGET_ENV = os.environ.get("SENATO_RETRY_BUDGET_S")
_RETRY_BUDGET_S: float | None = 480.0
_retry_spent = 0.0


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


def configura_budget(incrementale: bool) -> None:
    """Imposta il budget di retry del run (env override se presente).

    ``None`` = nessun tetto: si usa per il full, dove il ladder per-query
    (fino a 635s) è l'unico modo per far passare un'estrazione lunga.
    """
    global _RETRY_BUDGET_S
    if _RETRY_BUDGET_ENV is not None:
        _RETRY_BUDGET_S = float(_RETRY_BUDGET_ENV)
    else:
        _RETRY_BUDGET_S = 480.0 if incrementale else None


def query(sparql: str, timeout: int = 120) -> list[dict]:
    """Esegue una SELECT via curl condiviso (lab-connectors) e retry.

    Il WAF di dati.senato.it:
    - fa TLS-fingerprinting: le librerie Python ricevono 403/risposte vuote;
      il binario curl passa;
    - ha rate-limit per IP a burst: dopo ~8 query pesanti risponde 403
      (HTML) per diversi minuti. Il client condiviso solleva RuntimeError su
      risposta non-JSON/HTTP non-200.
    - serve risultati vuoti per query con variabili lunghe (vedi fetch_*).

    Il retry ha un **budget totale per run** (``SENATO_RETRY_BUDGET_S``,
    default 480s in incrementale, nessun tetto nel full): quando il WAF
    blocca, non si resta appesi 10 minuti *per ogni* query. Il budget limita
    l'attesa, non i tentativi: dopo l'ultima pausa si prova comunque. Esaurito
    il budget il run fallisce (e non scrive un parquet parziale); il successivo
    riparte dallo stesso ``max(data)``.
    """
    global _retry_spent
    ultimo: RuntimeError | None = None
    # Un tentativo in più rispetto alle pause: l'ultimo avviene dopo l'ultima
    # attesa (anche quando il budget è appena finito).
    for i in range(len(_RETRY_ATTEMPTS) + 1):
        if i > 0:
            wait = _RETRY_ATTEMPTS[i - 1]
            if _RETRY_BUDGET_S is None:
                pausa = wait
            else:
                residuo = _RETRY_BUDGET_S - _retry_spent
                if residuo <= 0:
                    break
                pausa = min(wait, residuo)
                _retry_spent += pausa
            log.warning(
                "query fallita (tentativo %d): %s — attesa %.0fs (%s)",
                i, ultimo, pausa,
                "nessun tetto" if _RETRY_BUDGET_S is None
                else f"budget {_retry_spent:.0f}/{_RETRY_BUDGET_S:.0f}s",
            )
            time.sleep(pausa)
        try:
            rows = execute_sparql_rows_curl(ENDPOINT, sparql, timeout=timeout)
            time.sleep(8)
            return rows
        except RuntimeError as exc:
            ultimo = exc
    raise RuntimeError(
        f"query fallita dopo {len(_RETRY_ATTEMPTS) + 1} tentativi: {sparql[:120]}..."
    )


def graphs_for_legislature(legislatura: int) -> list[str]:
    """Graph votazioni del Senato per legislatura (lista deterministica).

    Evita la query globale ``GRAPH ?g { ?s a osr:Votazione }`` — scansiona
    TUTTO lo store (tutte le legislature) a ogni run. Elenco verificato il
    2026-11-19 con ``SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s a osr:Votazione } }``:

    - leg 13-16 → ``votazioni/<leg>`` (graph unico)
    - leg 17-18 → ``votazioni-doc``, ``votazioni-fasi-1..4``, ``votazioni-sindisp``
    - leg 19    → come sopra + ``votazioni-fasi-5``

    Se il Senato aggiunge un graph, ``--discover-graphs`` ripristina la
    scoperta dinamica (una query in più, ma a prova di fonte nuova).
    """
    if legislatura <= 16:
        return [f"http://dati.senato.it/votazioni/{legislatura}"]
    nomi = [
        "votazioni-doc",
        "votazioni-fasi-1",
        "votazioni-fasi-2",
        "votazioni-fasi-3",
        "votazioni-fasi-4",
    ]
    if legislatura >= 19:
        nomi.append("votazioni-fasi-5")
    nomi.append("votazioni-sindisp")
    return [f"http://dati.senato.it/{n}/{legislatura}" for n in nomi]


def discover_graphs(legislatura: int) -> list[str]:
    """Scoperta dinamica dei graph (solo con ``--discover-graphs``)."""
    rows = query(f"""
        SELECT DISTINCT ?g WHERE {{
          GRAPH ?g {{ ?s a <{OSR}Votazione> }}
        }}
    """)
    return [r["g"] for r in rows if r["g"].endswith(f"/{legislatura}")]


_META_SELECT = """SELECT ?v
               (MAX(?s) AS ?seduta) (MAX(?l) AS ?legislatura)
               (MAX(?tipo) AS ?tipoVotazione) (MAX(?es) AS ?esito)
               (MAX(?fav) AS ?favorevoli) (MAX(?con) AS ?contrari)
               (MAX(?ast) AS ?astenuti) (MAX(?vot) AS ?votanti)
               (MAX(?pres) AS ?presenti) (MAX(?maj) AS ?maggioranza)
               (MAX(?cong) AS ?congedoMissione)"""
_META_OPTIONALS = """OPTIONAL { ?v osr:legislatura ?l . }
            OPTIONAL { ?v osr:tipoVotazione ?tipo . }
            OPTIONAL { ?v osr:esito ?es . }
            OPTIONAL { ?v osr:favorevoli ?fav . }
            OPTIONAL { ?v osr:contrari ?con . }
            OPTIONAL { ?v osr:astenuti ?ast . }
            OPTIONAL { ?v osr:votanti ?vot . }
            OPTIONAL { ?v osr:presenti ?pres . }
            OPTIONAL { ?v osr:maggioranza ?maj . }
            OPTIONAL { ?v osr:congedoMissione ?cong . }"""


def fetch_votazioni_meta(graph: str) -> list[dict]:
    """Metadati di tutte le votazioni di un graph (solo run full).

    In incrementale si usa :func:`fetch_votazioni_meta_union`: una query sola
    invece di una per graph, perché il WAF blocca dopo poche richieste.

    Nomi variabili corti: il WAF di dati.senato.it serve risultati vuoti
    per query con variabili lunghe (es. ?votazione) su alcuni pattern.
    """
    return query(f"""
        PREFIX osr: <{OSR}>
        {_META_SELECT}
        WHERE {{
          GRAPH <{graph}> {{
            ?v a osr:Votazione .
            OPTIONAL {{ ?v osr:seduta ?s . }}
            {_META_OPTIONALS}
          }}
        }}
        GROUP BY ?v
    """)


def _batches_per_lunghezza(
    items: list[str], build_query, max_chars: int = _QUERY_MAX_CHARS,
):
    """Raggruppa ``items`` in batch la cui query resta sotto ``max_chars``.

    Il limite dell'endpoint è sulla lunghezza della query, non sul numero di
    URI: la stessa N produce query di lunghezza diversa a seconda della base
    (meta vs voti). Un item da solo che sfonda viene comunque inviato: non c'è
    modo di spezzarlo ulteriormente.
    """
    batch: list[str] = []
    for item in items:
        if batch and len(build_query([*batch, item])) > max_chars:
            yield batch
            batch = [item]
        else:
            batch.append(item)
    if batch:
        yield batch


def _meta_union_query(items: list[str]) -> str:
    in_list = "<" + ">,<".join(items) + ">"
    return f"""
        PREFIX osr: <{OSR}>
        {_META_SELECT}
        WHERE {{
          ?v a osr:Votazione ; osr:seduta ?s .
          FILTER(?s IN ({in_list}))
          {_META_OPTIONALS}
        }}
        GROUP BY ?v
    """


def fetch_votazioni_meta_union(sedute: set[str]) -> list[dict]:
    """Metadati delle votazioni delle sedute indicate — unione dei graph.

    Il default graph di Virtuoso è l'unione dei graph: si evita ``GRAPH ?g``
    (e quindi l'elenco dei graph). I batch sono chiusi **per lunghezza** della
    query: con una baseline vecchia le sedute nuove possono essere decine e
    una IN-list lunga prende 403 anche con pochi URI.
    """
    meta: list[dict] = []
    for batch in _batches_per_lunghezza(sorted(sedute), _meta_union_query):
        meta.extend(query(_meta_union_query(batch)))
    return meta


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


def _voti_query(items: list[str], offset: int) -> str:
    in_list = "<" + ">,<".join(items) + ">"
    return f"""
        SELECT ?v ?sen ?p WHERE {{
          ?v ?p ?sen .
          FILTER(?p IN {VOTO_IN} && ?v IN ({in_list}))
        }}
        LIMIT 10000 OFFSET {offset}
    """


def fetch_voti_incrementali(votazioni: set[str]) -> list[dict]:
    """Voti individuali SOLO per un set di votazioni (incrementale).

    Un'unica query sull'unione dei graph invece di una per graph: il Senato
    blocca (403) le query lunghe. I batch sono chiusi **per lunghezza**;
    dentro il batch l'OFFSET è stabile (nessun overlap).
    """
    voti: list[dict] = []
    for batch in _batches_per_lunghezza(
        sorted(votazioni), lambda b: _voti_query(b, 0),
    ):
        offset = 0
        while True:
            rows = query(_voti_query(batch, offset))
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


def sedute_dal(sedute: list[dict], last_date) -> set[str]:
    """URI delle sedute con ``data >= last_date`` (confronto ISO su stringa).

    Confine ``>=`` incluso: l'ultima data già presente può ricevere votazioni
    nuove (pubblicazione a fine giornata).
    """
    return {
        s["s"] for s in sedute
        if s.get("d") and str(s["d"]) >= str(last_date)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legislature", type=int, default=19)
    parser.add_argument("--out", default=".")
    parser.add_argument("--merge-only", action="store_true",
                        help="salta l'estrazione SPARQL e ri-merge i parquet già estratti")
    parser.add_argument("--incremental", action="store_true",
                        help="estrae solo le votazioni successive alla max data già presente")
    parser.add_argument("--discover-graphs", action="store_true",
                        help="scopre i graph con una query globale invece della lista "
                             "deterministica per legislatura (usare se il Senato aggiunge un graph)")
    args = parser.parse_args()
    configura_budget(args.incremental)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / "senato_votazioni.parquet"

    all_meta: list[dict] = []
    voti_files: list[Path] = []
    last_date = None  # set in modalità incremental (per l'UNION nel merge)
    graph_falliti: list[str] = []

    if not args.merge_only:
        if args.discover_graphs:
            graphs = discover_graphs(args.legislature)
        else:
            graphs = graphs_for_legislature(args.legislature)
        if not graphs:
            log.error("nessun graph trovato per la legislatura %d", args.legislature)
            return 1
        log.info("legislatura %d — %d graph: %s", args.legislature, len(graphs),
                 ", ".join(g.split("/")[-1] for g in graphs))

        # Sedute caricate una volta sola (servono al filtro incrementale e al merge).
        sedute = fetch_sedute(args.legislature)
        log.info("sedute: %d", len(sedute))

        # ── Incremental: solo le sedute dal max(data) in poi ──
        new_sedute: set[str] | None = None
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
                new_sedute = sedute_dal(sedute, last_date)
                log.info("incremental: %d sedute dal %s", len(new_sedute), last_date)
                if not new_sedute:
                    # Nessuna seduta nuova → nessuna query metadati (prima se ne
                    # facevano una per graph, più una scoperta globale).
                    log.info("nessuna seduta nuova — parquet invariato: %s", final_path)
                    return 0

        incr = last_date is not None
        if incr:
            # ── Incrementale: 1 query metadati + 1 query voti (unione graph) ──
            all_meta.extend(fetch_votazioni_meta_union(new_sedute))
            new_votazioni = {m["v"] for m in all_meta}
            log.info("incremental: %d votazioni nuove (sedute dal %s)",
                     len(new_votazioni), last_date)
            if not new_votazioni:
                if new_sedute:
                    # L'endpoint può servire risposte vuote: una stallo silenzioso
                    # (sedute nuove, zero metadati) va reso visibile.
                    log.warning(
                        "incremental: %d sedute nuove ma 0 votazioni nei metadati "
                        "— possibile risposta vuota dal endpoint", len(new_sedute),
                    )
                log.info("niente di nuovo — parquet invariato: %s", final_path)
                return 0
            try:
                voti = fetch_voti_incrementali(new_votazioni)
            except Exception as exc:
                log.error("voti nuovi: ERRORE %s — run non valido, parquet invariato", exc)
                return 1
            voti = [v for v in voti if v["v"] in new_votazioni]
            if not voti:
                log.info("nessun voto nuovo — parquet invariato: %s", final_path)
                return 0
            f = out_dir / "voti_incr.parquet"
            pq.write_table(
                pa.table(
                    {
                        "votazione": [v["v"] for v in voti],
                        "senatore": [v["sen"] for v in voti],
                        "voto": [VOTO_LABEL[v["p"]] for v in voti],
                    }
                ),
                f,
            )
            voti_files.append(f)
            log.info("voti nuovi: %d → %s", len(voti), f.name)
        else:
            # ── Full: una query per graph (resta dentro la legislatura) ──
            for g in graphs:
                all_meta.extend(fetch_votazioni_meta(g))
            for g in graphs:
                graph_name = g.rstrip('/').split('/')[-2]
                f = out_dir / f"voti_{graph_name}.parquet"
                if f.exists():
                    log.info("  graph %s: già estratto, salto", graph_name)
                    voti_files.append(f)
                    continue
                try:
                    voti = fetch_voti(g)
                except Exception as exc:
                    log.error("  graph %s: ERRORE %s — salto", graph_name, exc)
                    graph_falliti.append(graph_name)
                    continue
                if not voti:
                    log.warning("  graph %s: nessun voto", graph_name)
                    continue
                table = pa.table(
                    {
                        "votazione": [v["v"] for v in voti],
                        "senatore": [v["sen"] for v in voti],
                        "voto": [VOTO_LABEL[v["p"]] for v in voti],
                    }
                )
                pq.write_table(table, f)
                voti_files.append(f)
                log.info("  graph %s: salvato %s (%d voti)", graph_name, f.name, len(voti))

        if graph_falliti:
            # Un graph fallito in full non deve produrre un parquet parziale e
            # "silenzioso": il prossimo run userebbe max(data) avanzato e
            # salterebbe per sempre le votazioni mancanti.
            # I `voti_*.parquet` già estratti NON si cancellano: sono la cache
            # di resume del full ("già estratto, salto" al run successivo).
            log.error("graph falliti: %s — run non valido, parquet invariato: %s",
                      ", ".join(graph_falliti), final_path)
            return 1

        if not voti_files:
            # Nessun graph ha prodotto voti (incrementale senza novità, o tutti
            # i graph falliti): non tentare il merge con read_parquet([]).
            log.info("nessun voto nuovo — parquet invariato: %s", final_path)
            return 0

        log.info("metadati: %d votazioni", len(all_meta))

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

    final_path = out_dir / "senato_votazioni.parquet"
    log.info("merge in %s", final_path)
    existing_union = (
        f"UNION ALL SELECT * FROM read_parquet('{final_path}')" if last_date is not None else ""
    )
    with duckdb.connect() as con:
        globs = ", ".join(f"'{p}'" for p in voti_files)
        con.execute(f"""
            CREATE OR REPLACE TABLE finale AS
            SELECT DISTINCT * FROM (
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

    # Pulizia: rimuovi file intermedi
    for f in out_dir.glob("voti_*.parquet"):
        f.unlink()
    meta_path = out_dir / "meta.parquet"
    sed_path = out_dir / "sedute.parquet"
    meta_path.unlink(missing_ok=True)
    sed_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
