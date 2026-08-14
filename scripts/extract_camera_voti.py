#!/usr/bin/env python3
"""Estrazione voti individuali della Camera (XIX leg.) — SPARQL per batch di votazione.

Deterministico e completo: invece di paginare con OFFSET (instabile su Virtuoso
senza ORDER BY), partiziona per VOTAZIONE: recupera l'elenco delle votazioni
della legislatura e le processa in batch via FILTER(?vr IN (...)). Ogni batch
ha un result-set fisso → niente overlap né buchi.

Uso:
    python3 scripts/extract_camera_voti.py --legislature 19
    python3 scripts/extract_camera_voti.py --legislature 19 --batch 200
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import requests

OCD = "http://dati.camera.it/ocd/"
ENDPOINT = "https://dati.camera.it/sparql"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("camera-voti")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 DataCivicLab/1.0"})


def query(sparql: str, timeout: int = 120) -> list[dict]:
    for attempt in range(5):
        try:
            # POST form-encoded: la query va nel BODY (niente limite URL →
            # evita il 414 con IN-list lunghe). Stesso pattern del toolkit.
            resp = SESSION.post(
                ENDPOINT, data={"query": sparql},
                headers={"Accept": "application/sparql-results+json,application/json"},
                timeout=timeout,
            )
            if resp.status_code in (405, 414):
                # fallback GET se POST non supportata
                resp = SESSION.get(
                    ENDPOINT, params={"query": sparql},
                    headers={"Accept": "application/sparql-results+json,application/json"},
                    timeout=timeout,
                )
            resp.raise_for_status()
            rows = resp.json()["results"]["bindings"]
            time.sleep(0.3)
            return [{k: v.get("value") for k, v in r.items()} for r in rows]
        except (requests.RequestException, ValueError) as exc:
            wait = 8 * (2 ** attempt)
            log.warning("query fallita (tentativo %d): %s — retry in %ds", attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"query fallita dopo 5 tentativi")


def fetch_votazioni(legislatura: int) -> list[str]:
    vot: set[str] = set()
    offset = 0
    page = 10_000
    while True:
        rows = query(f"""
            SELECT ?vr WHERE {{
              ?vr a <{OCD}votazione> ; <{OCD}rif_leg> <{OCD}legislatura.rdf/repubblica_{legislatura}> .
            }}
            LIMIT {page} OFFSET {offset}
        """)
        vot.update(r["vr"] for r in rows)
        if len(rows) < page:
            break
        offset += page
    return sorted(vot)


def fetch_batch(batch: list[str]) -> list[dict]:
    """Voti per un batch di votazioni (IN-list fissa → OFFSET stabile)."""
    in_list = "<" + ">,<".join(batch) + ">"
    voti: list[dict] = []
    offset = 0
    page = 10_000
    while True:
        rows = query(f"""
            SELECT ?v ?dep ?vr ?grp ?tipo ?sigla WHERE {{
              ?v a <{OCD}voto> ; <{OCD}rif_deputato> ?dep ; <{OCD}rif_votazione> ?vr .
              OPTIONAL {{ ?v <{OCD}rif_gruppoParlamentare> ?grp . }}
              OPTIONAL {{ ?v <http://purl.org/dc/elements/1.1/type> ?tipo . }}
              OPTIONAL {{ ?v <{OCD}siglaGruppo> ?sigla . }}
              FILTER(?vr IN ({in_list}))
            }}
            LIMIT {page} OFFSET {offset}
        """)
        voti.extend(rows)
        offset += page
        if len(rows) < page:
            break
    return voti


def fetch_votazione_dates(legislatura: int) -> list[dict]:
    """Mappa votazione → data (dc:date presente su tutte le votazioni XIX)."""
    dates: list[dict] = []
    offset = 0
    page = 10_000
    while True:
        rows = query(f"""
            SELECT ?vr (MAX(?d) AS ?d) WHERE {{
              ?vr a <{OCD}votazione> ; <{OCD}rif_leg> <{OCD}legislatura.rdf/repubblica_{legislatura}> ;
                  <http://purl.org/dc/elements/1.1/date> ?d .
            }}
            GROUP BY ?vr
            LIMIT {page} OFFSET {offset}
        """)
        dates.extend(rows)
        if len(rows) < page:
            break
        offset += page
    return dates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legislature", type=int, default=19)
    parser.add_argument("--out", default="out/data/derived/camera_voti")
    parser.add_argument("--batch", type=int, default=200)
    parser.add_argument("--incremental", action="store_true",
                        help="estrae solo le votazioni successive alla max data già presente nel parquet")
    args = parser.parse_args()

    out_dir = Path(args.out)
    chunk_dir = out_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / f"camera_voti.parquet"

    # ── Incremental: solo votazioni con data > max esistente ──────────
    incremental_existing = None
    if args.incremental and final_path.exists():
        import duckdb as _ddb
        with _ddb.connect() as con:
            last = con.execute(
                f"SELECT max(data) FROM read_parquet('{final_path}')"
            ).fetchone()[0]
        if last is None:
            log.info("incremental: parquet esistente ma senza date → full")
        else:
            incremental_existing = str(last)
            log.info("incremental: max data esistente = %s", last)

    votazioni = fetch_votazioni(args.legislature)
    if incremental_existing:
        # filtra solo le votazioni con data > last (mappa date prima del filtro)
        dates = fetch_votazione_dates(args.legislature)
        new_dates = {
            d["vr"] for d in dates
            if d["d"] and str(d["d"])[:8] > incremental_existing.replace("-", "")
        }
        votazioni = sorted(votazioni, key=lambda x: x)
        votazioni = [v for v in votazioni if v in new_dates]
        log.info("incremental: %d/%d votazioni nuove (data > %s)",
                 len(votazioni), len(dates), incremental_existing)
        if not votazioni:
            log.info("niente di nuovo — parquet invariato: %s", final_path)
            return 0
    else:
        log.info("votazioni XIX: %d", len(votazioni))
    if not votazioni:
        return 1

    total = 0
    idx = 0
    rows_acc: list[dict] = []
    n_batches = (len(votazioni) + args.batch - 1) // args.batch
    for bi in range(0, len(votazioni), args.batch):
        batch = votazioni[bi:bi + args.batch]
        rows = fetch_batch(batch)
        rows_acc.extend(rows)
        total += len(rows)
        if len(rows_acc) >= 200_000:
            idx += 1
            f = chunk_dir / f"chunk_{idx:04d}.parquet"
            pq.write_table(
                pa.table(
                    {
                        "voto": [r["v"] for r in rows_acc],
                        "deputato": [r["dep"] for r in rows_acc],
                        "votazione": [r["vr"] for r in rows_acc],
                        "gruppo": [r.get("grp") for r in rows_acc],
                        "tipo": [r.get("tipo") for r in rows_acc],
                        "sigla": [r.get("sigla") for r in rows_acc],
                    }
                ),
                f,
            )
            log.info("chunk %d scritto (batch %d/%d, tot %d)", idx, bi // args.batch + 1, n_batches, total)
            rows_acc = []
    if rows_acc:
        idx += 1
        f = chunk_dir / f"chunk_{idx:04d}.parquet"
        pq.write_table(
            pa.table(
                {
                    "voto": [r["v"] for r in rows_acc],
                    "deputato": [r["dep"] for r in rows_acc],
                    "votazione": [r["vr"] for r in rows_acc],
                    "gruppo": [r.get("grp") for r in rows_acc],
                    "tipo": [r.get("tipo") for r in rows_acc],
                    "sigla": [r.get("sigla") for r in rows_acc],
                }
            ),
            f,
        )
        log.info("chunk finale %d scritto (tot %d)", idx, total)

    log.info("totale: %d voti, %d votazioni", total, len(votazioni))

    final_path = out_dir / f"camera_voti.parquet"
    dates = fetch_votazione_dates(args.legislature)
    log.info("date votazioni: %d", len(dates))
    dates_path = out_dir / "votazione_dates.parquet"
    pq.write_table(
        pa.table({"votazione": [d["vr"] for d in dates], "data_raw": [d["d"] for d in dates]}),
        dates_path,
    )
    globs = ", ".join(f"'{p}'" for p in sorted(chunk_dir.glob("chunk_*.parquet")))
    # UNION con l'esistente SOLO in incremental (il file esiste per definizione);
    # in full non va referenziato: su un runner fresco non c'è.
    existing_union = (
        f"UNION ALL SELECT * FROM read_parquet('{final_path}')" if incremental_existing else ""
    )
    with duckdb.connect() as con:
        con.execute(f"""
            CREATE OR REPLACE TABLE finale AS
            SELECT DISTINCT * FROM (
                SELECT DISTINCT
                    v.voto AS voto_uri,
                    TRY_CAST(REGEXP_EXTRACT(v.deputato, 'deputato\\.rdf/d(\\d+)_', 1) AS BIGINT) AS deputato_id,
                    v.votazione,
                    v.tipo AS voto,
                    v.sigla,
                    v.gruppo,
                    TRY_CAST(
                        CASE WHEN length(d.data_raw) = 8
                             THEN substr(d.data_raw,1,4)||'-'||substr(d.data_raw,5,2)||'-'||substr(d.data_raw,7,2)
                        END AS DATE
                    ) AS data
                FROM read_parquet([{globs}]) v
                LEFT JOIN read_parquet('{dates_path}') d ON v.votazione = d.votazione
                {existing_union}
            ) q
        """)
        con.execute(f"COPY (SELECT * FROM finale) TO '{final_path}' (FORMAT PARQUET)")
        n = con.execute("SELECT count(*) FROM finale").fetchone()[0]
        nd = con.execute("SELECT count(DISTINCT deputato_id) FROM finale").fetchone()[0]
        nv = con.execute("SELECT count(DISTINCT votazione) FROM finale").fetchone()[0]
        null_data = con.execute("SELECT count(*) FROM finale WHERE data IS NULL").fetchone()[0]
    log.info("OK: %d voti, %d deputati, %d votazioni, NULL data %d → %s",
             n, nd, nv, null_data, final_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
