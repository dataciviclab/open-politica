#!/usr/bin/env python3
"""Estrazione iter legislativo Camera (Leg16-19) — SPARQL dati.camera.it.

Quattro classi OCD partizionate per prefisso URI (la legislatura non è
sempre nel grafo):
- ocd:assegnazione      a{leg}_{n}
- ocd:statoIter         si{leg}_{n}
- ocd:trasmissione      tr{leg}_{n}
- ocd:richiestaParere   rp{leg}_{n}

Il collegamento all'atto (attocamera ac{leg}_{n}) è estratto a parte:
- assegnazione: attocamera->rif_assegnazione, fallback dibattito->rif_attoCamera
- statoIter:    solo attocamera->rif_statoIter (Leg16 quasi assente nel LOD)
- trasmissione: attocamera->rif_trasmissione; numero Senato dal titolo se assente
- richiestaParere: dibattito->rif_attoCamera + organo/data dal dibattito

Robustezza:
- retry con backoff esponenziale e jitter; uscita pulita se l'endpoint è down
- cache incrementale per pagina/batch in _cache/ (ripresa dopo interruzione)
- verifica di completezza: ID estratti == COUNT DISTINCT nel LOD

Uso:
    python preprocess.py --legislature 19
    python preprocess.py --legislature 16 17 18 19 --batch 500
    python preprocess.py --legislature 19 --refresh
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import requests

OCD = "http://dati.camera.it/ocd/"
ENDPOINT = "https://dati.camera.it/sparql"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
DC_DATE = "http://purl.org/dc/elements/1.1/date"
DC_TYPE = "http://purl.org/dc/elements/1.1/type"
DC_TITLE = "http://purl.org/dc/elements/1.1/title"
DC_IDENT = "http://purl.org/dc/elements/1.1/identifier"
DCT_PROV = "http://purl.org/dc/terms/provenance"

PREFIX = {
    "assegnazione": "a",
    "statoIter": "si",
    "trasmissione": "tr",
    "richiestaParere": "rp",
}

CANONICAL_EVENT_COLUMNS = [
    "s", "org", "orgLabel", "date", "dataAsn", "sede", "ident", "dib",
    "dibLabel", "dibTitle", "dibDate", "dibDateRange", "ac", "esito",
    "label", "type", "prov", "senato", "_class", "_leg",
]
CANONICAL_LINK_COLUMNS = ["a", "e", "_class"]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("camera-iter")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 DataCivicLab/1.0"})


class EndpointUnavailable(RuntimeError):
    """L'endpoint non risponde dopo tutti i tentativi; la cache è preservata."""


def sparql(query: str, timeout: int = 240, max_retries: int = 8) -> list[dict]:
    last_error = ""
    for attempt in range(max_retries):
        try:
            resp = SESSION.post(
                ENDPOINT, data={"query": query},
                headers={"Accept": "application/sparql-results+json,application/json"},
                timeout=timeout,
            )
            if resp.status_code in (405, 414):
                resp = SESSION.get(
                    ENDPOINT, params={"query": query},
                    headers={"Accept": "application/sparql-results+json,application/json"},
                    timeout=timeout,
                )
            if resp.status_code == 200:
                rows = resp.json()["results"]["bindings"]
                time.sleep(0.25)
                return [{k: v.get("value") for k, v in r.items()} for r in rows]
            last_error = f"HTTP {resp.status_code}"
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)[:120]
        wait = min(120, 5 * (2 ** attempt)) + random.uniform(0, 3)
        log.warning("query fallita (%d/%d): %s — retry in %.0fs",
                    attempt + 1, max_retries, last_error, wait)
        time.sleep(wait)
    raise EndpointUnavailable(last_error)


def endpoint_alive(timeout: int = 30, tries: int = 3) -> bool:
    """Preflight rapido: evita di restare bloccati su un endpoint down."""
    for attempt in range(tries):
        try:
            resp = SESSION.post(
                ENDPOINT, data={"query": "SELECT (1 AS ?x) WHERE {}"},
                headers={"Accept": "application/sparql-results+json,application/json"},
                timeout=timeout,
            )
            if resp.status_code == 200:
                return True
            log.warning("preflight HTTP %s (%d/%d)", resp.status_code, attempt + 1, tries)
        except requests.RequestException as exc:
            log.warning("preflight errore %s (%d/%d)", str(exc)[:80], attempt + 1, tries)
        time.sleep(min(30, 5 * (2 ** attempt)))
    return False


def write_rows(rows: list[dict], path: Path, canonical: list[str]) -> None:
    if not rows:
        return
    keys = sorted(set(canonical) | {k for r in rows for k in r})
    cols = {k: [r.get(k) for r in rows] for k in keys}
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols), path, compression="snappy")


def read_rows(path: Path) -> list[dict]:
    with duckdb.connect() as con:
        cur = con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}')")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def cache_count(cls: str, leg: int, cache_dir: Path) -> int | None:
    """COUNT DISTINCT atteso, cachato su disco (per la verifica di completezza)."""
    path = cache_dir / f"count_{leg}_{cls}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["n"]
    rows = sparql(f"""
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{
          GRAPH <{OCD}> {{
            ?s a <{OCD}{cls}> .
            FILTER(STRSTARTS(STR(?s), "{OCD}{cls}.rdf/{PREFIX[cls]}{leg}_"))
          }}
        }}
    """)
    n = int(rows[0]["n"]) if rows else 0
    path.write_text(json.dumps({"n": n}), encoding="utf-8")
    return n


def fetch_ids(cls: str, leg: int, cache_dir: Path, page: int = 5000,
              verify: bool = True) -> list[str]:
    """Fase 1: URI con keyset pagination e salvataggio incrementale."""
    path = cache_dir / f"ids_{leg}_{cls}.parquet"
    done_path = cache_dir / f"ids_{leg}_{cls}.done"
    if path.exists():
        ids = [r["s"] for r in read_rows(path)]
    else:
        ids = []

    if not done_path.exists():
        prefix = f"{OCD}{cls}.rdf/{PREFIX[cls]}{leg}_"
        last = ids[-1] if ids else ""
        while True:
            cursor = f"FILTER(?s > <{last}>)" if last else ""
            rows = sparql(f"""
                SELECT ?s WHERE {{
                  GRAPH <{OCD}> {{
                    ?s a <{OCD}{cls}> .
                    FILTER(STRSTARTS(STR(?s), "{prefix}"))
                    {cursor}
                  }}
                }}
                ORDER BY ?s LIMIT {page}
            """)
            if not rows:
                break
            new = [r["s"] for r in rows if r["s"] not in set(ids)]
            ids.extend(new)
            write_rows([{"s": x} for x in ids], path, ["s"])
            last = rows[-1]["s"]
            log.info("  %s leg%d ids: %d", cls, leg, len(ids))
            if len(rows) < page:
                break
            time.sleep(0.3)
        done_path.write_text("ok", encoding="utf-8")

    if verify:
        expected = cache_count(cls, leg, cache_dir)
        if expected is not None and len(ids) != expected:
            raise RuntimeError(
                f"{cls} leg{leg}: estratti {len(ids)} URI, attesi {expected}"
            )
    log.info("  %s leg%d ids totali: %d", cls, leg, len(ids))
    return ids


def details_dir(cache_dir: Path, leg: int, cls: str) -> Path:
    return cache_dir / f"details_{leg}_{cls}"


def fetch_details(cls: str, leg: int, ids: list[str], template: str,
                  cache_dir: Path, batch: int, verify: bool = True) -> list[dict]:
    """Fase 2: dettagli in batch IN-list, cache per batch (ripresa esatta)."""
    folder = details_dir(cache_dir, leg, cls)
    folder.mkdir(parents=True, exist_ok=True)
    batches = [ids[i:i + batch] for i in range(0, len(ids), batch)]
    rows: list[dict] = []

    for idx, chunk in enumerate(batches):
        path = folder / f"batch_{idx:05d}.parquet"
        if path.exists():
            rows.extend(read_rows(path))
            continue
        in_list = "<" + ">,<".join(chunk) + ">"
        body = template.replace("{filter}", f"FILTER(?s IN ({in_list}))")
        part = sparql(body)
        for row in part:
            row["_class"] = cls
            row["_leg"] = leg
        write_rows(part, path, CANONICAL_EVENT_COLUMNS)
        rows.extend(part)
        log.info("  %s leg%d: batch %d/%d (%d righe)",
                 cls, leg, idx + 1, len(batches), len(rows))
        time.sleep(0.25)

    if verify:
        got = {r["s"] for r in rows if r.get("s")}
        missing = set(ids) - got
        if missing:
            raise RuntimeError(
                f"{cls} leg{leg}: {len(missing)} URI senza dettagli "
                f"(es. {sorted(missing)[:3]})"
            )
    return rows


def fetch_links(leg: int, cache_dir: Path, batch: int) -> list[dict]:
    """Link atto->evento con keyset (a,e) e salvataggio incrementale."""
    all_rows: list[dict] = []
    for cls, predicate in [
        ("assegnazione", "rif_assegnazione"),
        ("statoIter", "rif_statoIter"),
        ("trasmissione", "rif_trasmissione"),
    ]:
        path = cache_dir / f"links_{leg}_{cls}.parquet"
        done_path = cache_dir / f"links_{leg}_{cls}.done"
        rows = read_rows(path) if path.exists() else []
        if not done_path.exists():
            last_a = rows[-1]["a"] if rows else ""
            last_e = rows[-1]["e"] if rows else ""
            while True:
                if last_a:
                    cursor = (f"FILTER(?a > <{last_a}> || "
                              f"(?a = <{last_a}> && ?e > <{last_e}>))")
                else:
                    cursor = ""
                chunk = sparql(f"""
                    SELECT ?a ?e WHERE {{
                      GRAPH <{OCD}> {{
                        ?a a <{OCD}atto> ;
                           <{OCD}rif_leg> <{OCD}legislatura.rdf/repubblica_{leg}> ;
                           <{OCD}{predicate}> ?e .
                        {cursor}
                      }}
                    }}
                    ORDER BY ?a ?e LIMIT {batch}
                """)
                if not chunk:
                    break
                for r in chunk:
                    r["_class"] = cls
                rows.extend(chunk)
                write_rows(rows, path, CANONICAL_LINK_COLUMNS)
                log.info("  link %s leg%d: %d", cls, leg, len(rows))
                if len(chunk) < batch:
                    break
                last_a, last_e = chunk[-1]["a"], chunk[-1]["e"]
                time.sleep(0.25)
            done_path.write_text("ok", encoding="utf-8")
        all_rows.extend(rows)
    return all_rows


def fetch_organi(leg: int, cache_dir: Path) -> list[dict]:
    """Elenco organi della legislatura con label (per mappare i pareri orfani)."""
    path = cache_dir / f"organi_{leg}.parquet"
    if path.exists():
        return read_rows(path)
    rows = sparql(f"""
        SELECT ?o ?label WHERE {{
          GRAPH <{OCD}> {{
            ?o a <{OCD}organo> .
            FILTER(STRSTARTS(STR(?o), "{OCD}organo.rdf/o{leg}_"))
            OPTIONAL {{ ?o <{RDFS_LABEL}> ?label }}
          }}
        }}
    """)
    write_rows(rows, path, ["o", "label"])
    log.info("  organi leg%d: %d", leg, len(rows))
    return rows


EVENT_QUERIES = {
    "assegnazione": f"""
        SELECT ?s ?org ?orgLabel ?date ?dataAsn ?sede ?ident ?dib ?ac ?label WHERE {{
          GRAPH <{OCD}> {{
            ?s a <{OCD}assegnazione> .
            {{filter}}
            OPTIONAL {{ ?s <{OCD}rif_organo> ?org .
                        OPTIONAL {{ ?org <{RDFS_LABEL}> ?orgLabel }} }}
            OPTIONAL {{ ?s <{DC_DATE}> ?date }}
            OPTIONAL {{ ?s <{OCD}dataAssegnazione> ?dataAsn }}
            OPTIONAL {{ ?s <{OCD}sede> ?sede }}
            OPTIONAL {{ ?s <{DC_IDENT}> ?ident }}
            OPTIONAL {{ ?s <{RDFS_LABEL}> ?label }}
            OPTIONAL {{ ?s <{OCD}rif_dibattito> ?dib .
                        OPTIONAL {{ ?dib <{OCD}rif_attoCamera> ?ac }} }}
          }}
        }}""",
    "statoIter": f"""
        SELECT ?s ?label ?date ?type WHERE {{
          GRAPH <{OCD}> {{
            ?s a <{OCD}statoIter> .
            {{filter}}
            OPTIONAL {{ ?s <{RDFS_LABEL}> ?label }}
            OPTIONAL {{ ?s <{DC_DATE}> ?date }}
            OPTIONAL {{ ?s <{DC_TYPE}> ?type }}
          }}
        }}""",
    "trasmissione": f"""
        SELECT ?s ?label ?date ?type ?prov ?senato WHERE {{
          GRAPH <{OCD}> {{
            ?s a <{OCD}trasmissione> .
            {{filter}}
            OPTIONAL {{ ?s <{RDFS_LABEL}> ?label }}
            OPTIONAL {{ ?s <{DC_DATE}> ?date }}
            OPTIONAL {{ ?s <{DC_TYPE}> ?type }}
            OPTIONAL {{ ?s <{DCT_PROV}> ?prov }}
            OPTIONAL {{ ?s <{OCD}rif_attoSenato> ?senato }}
          }}
        }}""",
    "richiestaParere": f"""
        SELECT ?s ?dib ?dibLabel ?dibTitle ?dibDate ?dibDateRange ?ac ?esito ?label WHERE {{
          GRAPH <{OCD}> {{
            ?s a <{OCD}richiestaParere> .
            {{filter}}
            OPTIONAL {{ ?s <{OCD}rif_dibattito> ?dib .
                        OPTIONAL {{ ?dib <{RDFS_LABEL}> ?dibLabel }}
                        OPTIONAL {{ ?dib <{DC_TITLE}> ?dibTitle }}
                        OPTIONAL {{ ?dib <{OCD}startDate> ?dibDate }}
                        OPTIONAL {{ ?dib <{DC_DATE}> ?dibDateRange }}
                        OPTIONAL {{ ?dib <{OCD}rif_attoCamera> ?ac }} }}
            OPTIONAL {{ ?s <{OCD}esito> ?esito }}
            OPTIONAL {{ ?s <{RDFS_LABEL}> ?label }}
          }}
        }}""",
}


def build_final(out_dir: Path, cache_dir: Path, legislature: list[int],
                verify: bool = True) -> Path:
    events: list[dict] = []
    links: list[dict] = []
    organi: list[dict] = []
    for leg in legislature:
        for cls in EVENT_QUERIES:
            folder = details_dir(cache_dir, leg, cls)
            for f in sorted(folder.glob("batch_*.parquet")):
                events.extend(read_rows(f))
        for cls in ("assegnazione", "statoIter", "trasmissione"):
            p = cache_dir / f"links_{leg}_{cls}.parquet"
            if p.exists():
                links.extend(read_rows(p))
        p = cache_dir / f"organi_{leg}.parquet"
        if p.exists():
            for row in read_rows(p):
                row["_leg"] = leg
                organi.append(row)

    if not events:
        raise RuntimeError("nessun evento in cache: esegui prima l'estrazione")

    events_path = out_dir / "_events.parquet"
    links_path = out_dir / "_links.parquet"
    organi_path = out_dir / "_organi.parquet"
    final_path = out_dir / "camera_iter.parquet"
    write_rows(events, events_path, CANONICAL_EVENT_COLUMNS)
    write_rows(links, links_path, CANONICAL_LINK_COLUMNS)

    with duckdb.connect() as con:
        con.execute(f"CREATE OR REPLACE TABLE eventi AS SELECT * FROM read_parquet('{events_path.as_posix()}')")
        con.execute(f"CREATE OR REPLACE TABLE link AS SELECT * FROM read_parquet('{links_path.as_posix()}')")
        con.execute(r"""
            CREATE OR REPLACE TABLE link_atto AS
            SELECT
                evento_uri,
                MIN(atto_num) AS atto_num,
                COUNT(DISTINCT atto_num) AS n_atti
            FROM (
                SELECT DISTINCT
                    e AS evento_uri,
                    TRY_CAST(regexp_extract(CAST(a AS VARCHAR), 'attocamera\.rdf/ac\d+_(\d+)', 1) AS BIGINT) AS atto_num
                FROM link
                WHERE a LIKE '%attocamera.rdf%' AND e IS NOT NULL
            )
            WHERE atto_num IS NOT NULL
            GROUP BY evento_uri
        """)
        con.execute(r"""
            CREATE OR REPLACE TABLE link_dib AS
            SELECT
                s AS evento_uri,
                MIN(TRY_CAST(regexp_extract(CAST(ac AS VARCHAR), 'attocamera\.rdf/ac\d+_(\d+)', 1) AS BIGINT)) AS atto_num,
                COUNT(DISTINCT regexp_extract(CAST(ac AS VARCHAR), 'attocamera\.rdf/ac\d+_(\d+)', 1)) AS n_atti
            FROM eventi
            WHERE ac LIKE '%attocamera.rdf%'
            GROUP BY s
        """)
        if organi:
            write_rows(organi, organi_path, ["o", "label", "_leg"])
            con.execute(f"CREATE OR REPLACE TABLE organi AS "
                        f"SELECT * FROM read_parquet('{organi_path.as_posix()}')")
        else:
            con.execute("CREATE OR REPLACE TABLE organi "
                        "(o VARCHAR, label VARCHAR, _leg INTEGER)")
        con.execute(r"""
            CREATE OR REPLACE MACRO label_key(x) AS
                regexp_replace(
                    replace(
                        upper(trim(translate(
                            replace(COALESCE(CAST(x AS VARCHAR), ''), '(', ' ('),
                            'àèéìòùÀÈÉÌÒÙ', 'aeeiouAEEIOU'))),
                        '''', ''),
                    ' +', ' ', 'g')
        """)
        con.execute(rf"""
            COPY (
                WITH raw AS (
                    SELECT
                        CAST(s AS VARCHAR)           AS s,
                        CAST(org AS VARCHAR)         AS org,
                        CAST(orgLabel AS VARCHAR)    AS orgLabel,
                        CAST(date AS VARCHAR)        AS date,
                        CAST(dataAsn AS VARCHAR)     AS dataAsn,
                        CAST(sede AS VARCHAR)        AS sede,
                        CAST(ident AS VARCHAR)       AS ident,
                        CAST(dib AS VARCHAR)         AS dib,
                        CAST(dibLabel AS VARCHAR)    AS dibLabel,
                        CAST(dibTitle AS VARCHAR)    AS dibTitle,
                        CAST(dibDate AS VARCHAR)     AS dibDate,
                        CAST(dibDateRange AS VARCHAR) AS dibDateRange,
                        CAST(ac AS VARCHAR)          AS ac,
                        CAST(esito AS VARCHAR)       AS esito,
                        CAST(label AS VARCHAR)       AS label,
                        CAST(type AS VARCHAR)        AS type,
                        CAST(prov AS VARCHAR)        AS prov,
                        CAST(senato AS VARCHAR)      AS senato,
                        CAST(_class AS VARCHAR)      AS _class,
                        CAST(_leg AS BIGINT)         AS _leg,
                        -- Il numero "standard" è l'ultimo segmento numerico
                        -- (a19_19153). Gli URI non standard (a19_19VII0743,
                        -- a19_123_bis) devono usare lo slug completo: altrimenti
                        -- più eventi collidono sullo stesso evento_id e il dedup
                        -- li perde. La regex standard è ancorata a fine stringa; senza `$`
                        -- estrarrebbe le cifre iniziali (19 da a19_19VII0743).
                        -- Fallback: se il numero non è un segmento finale, tutto lo slug.
                        CASE _class
                            WHEN 'assegnazione' THEN 'asn_' || COALESCE(
                                NULLIF(regexp_extract(CAST(s AS VARCHAR), 'a\d+_(\d+)$', 1), ''),
                                regexp_extract(CAST(s AS VARCHAR), 'a\d+_(.*)$', 1))
                            WHEN 'statoIter' THEN 'stt_' || COALESCE(
                                NULLIF(regexp_extract(CAST(s AS VARCHAR), 'si\d+_(\d+)$', 1), ''),
                                regexp_extract(CAST(s AS VARCHAR), 'si\d+_(.*)$', 1))
                            WHEN 'trasmissione' THEN 'trs_' || COALESCE(
                                NULLIF(regexp_extract(CAST(s AS VARCHAR), 'tr\d+_(\d+)$', 1), ''),
                                regexp_extract(CAST(s AS VARCHAR), 'tr\d+_(.*)$', 1))
                            ELSE 'rqp_' || COALESCE(
                                NULLIF(regexp_extract(CAST(s AS VARCHAR), 'rp\d+_(\d+)$', 1), ''),
                                regexp_extract(CAST(s AS VARCHAR), 'rp\d+_(.*)$', 1))
                        END || '_' || CAST(_leg AS VARCHAR)
                            || COALESCE('_' || regexp_extract(CAST(org AS VARCHAR), '(\d+)$', 1), '')
                            AS evento_id
                    FROM eventi
                ),
                asn_map AS (
                    SELECT
                        CAST(_leg AS INTEGER) AS leg,
                        label_key(orgLabel) AS label_key,
                        MIN(CAST(org AS VARCHAR)) AS organo_id,
                        MAX(CAST(orgLabel AS VARCHAR)) AS organo_label
                    FROM raw
                    WHERE _class = 'assegnazione'
                      AND org IS NOT NULL
                      AND orgLabel IS NOT NULL
                    GROUP BY 1, 2
                ),
                organi_map AS (
                    SELECT
                        CAST(_leg AS INTEGER) AS leg,
                        label_key(label) AS label_key,
                        MIN(CAST(o AS VARCHAR)) AS organo_id,
                        MAX(CAST(label AS VARCHAR)) AS organo_label
                    FROM organi
                    WHERE label IS NOT NULL
                    GROUP BY 1, 2
                ),
                parere_org AS (
                    SELECT
                        e.s AS evento_uri,
                        COALESCE(am.organo_id, om.organo_id) AS organo_id,
                        COALESCE(am.organo_label, om.organo_label) AS organo_label
                    FROM raw e
                    LEFT JOIN asn_map am
                      ON CAST(e._leg AS INTEGER) = am.leg
                     AND label_key(COALESCE(e.dibLabel, e.dibTitle)) = am.label_key
                    LEFT JOIN organi_map om
                      ON CAST(e._leg AS INTEGER) = om.leg
                     AND label_key(COALESCE(e.dibLabel, e.dibTitle)) = om.label_key
                    WHERE e._class = 'richiestaParere'
                ),
                resolved AS (
                    SELECT
                        r.evento_id,
                        r.s AS evento_uri,
                        r._class AS tipo_evento,
                        r._leg AS legislatura,
                        COALESCE(
                            CASE WHEN la.n_atti = 1 THEN la.atto_num END,
                            CASE WHEN ld.n_atti = 1 THEN ld.atto_num END
                        ) AS atto_num,
                        CASE
                            WHEN la.n_atti = 1 THEN 'attocamera'
                            WHEN ld.n_atti = 1 THEN 'dibattito'
                            WHEN COALESCE(la.n_atti, ld.n_atti) > 1 THEN 'ambiguo'
                            ELSE NULL
                        END AS atto_source,
                        COALESCE(
                            r.dataAsn,
                            r.date,
                            r.dibDate,
                            CASE WHEN length(CAST(r.dibDateRange AS VARCHAR)) >= 8
                                 THEN substr(CAST(r.dibDateRange AS VARCHAR), 1, 8) END
                        ) AS data_raw,
                        COALESCE(CAST(r.org AS VARCHAR), po.organo_id) AS organo_id,
                        COALESCE(CAST(r.orgLabel AS VARCHAR), po.organo_label) AS organo_label,
                        r.sede,
                        CASE
                            WHEN r._class = 'statoIter' THEN COALESCE(r.label, r.type)
                            WHEN r._class = 'trasmissione' THEN COALESCE(r.type, r.label)
                            WHEN r._class = 'richiestaParere' THEN r.esito
                            ELSE r.sede
                        END AS esito,
                        CASE WHEN r._class = 'trasmissione' THEN r.senato END AS target_uri,
                        CASE WHEN r._class = 'trasmissione' THEN r.prov END AS provenienza,
                        CASE
                            WHEN r._class = 'trasmissione' AND r.senato IS NOT NULL
                                THEN regexp_extract(CAST(r.senato AS VARCHAR), '(\d+)$', 1)
                            WHEN r._class = 'trasmissione'
                                THEN regexp_extract(CAST(COALESCE(r.label, r.type) AS VARCHAR), '\(S\.\s*(\d+)', 1)
                        END AS senato_atto_num,
                        r.ident AS identifier
                    FROM raw r
                    LEFT JOIN link_atto la ON r.s = la.evento_uri
                    LEFT JOIN link_dib  ld ON r.s = ld.evento_uri
                    LEFT JOIN parere_org po ON r.s = po.evento_uri
                ),
                dedup AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY evento_id
                            ORDER BY atto_num NULLS LAST
                        ) AS rn
                    FROM resolved
                ),
                parsed AS (
                    SELECT
                        *,
                        CASE
                            WHEN data_raw IS NULL THEN NULL
                            WHEN regexp_matches(CAST(data_raw AS VARCHAR), '^\d{{8}}')
                                THEN TRY_CAST(substr(CAST(data_raw AS VARCHAR),1,4)||'-'||
                                              substr(CAST(data_raw AS VARCHAR),5,2)||'-'||
                                              substr(CAST(data_raw AS VARCHAR),7,2) AS DATE)
                            ELSE TRY_CAST(CAST(data_raw AS VARCHAR) AS DATE)
                        END AS data_parsed
                    FROM dedup
                    WHERE rn = 1
                )
                SELECT
                    evento_id,
                    evento_uri,
                    tipo_evento,
                    CAST(legislatura AS INTEGER) AS legislatura,
                    atto_num AS atto_id,
                    atto_source,
                    data_parsed AS data,
                    COALESCE(data_parsed < CASE legislatura
                        WHEN 16 THEN DATE '2008-04-29'
                        WHEN 17 THEN DATE '2013-03-15'
                        WHEN 18 THEN DATE '2018-03-23'
                        WHEN 19 THEN DATE '2022-10-13'
                    END, FALSE) AS data_anomala,
                    organo_id,
                    organo_label,
                    sede,
                    esito,
                    CAST(target_uri AS VARCHAR) AS target_uri,
                    CAST(provenienza AS VARCHAR) AS provenienza,
                    CAST(senato_atto_num AS VARCHAR) AS senato_atto_num,
                    CAST(identifier AS VARCHAR) AS identifier
                FROM parsed
            ) TO '{final_path.as_posix()}' (FORMAT PARQUET)
        """)
        n = con.execute(f"SELECT count(*) FROM read_parquet('{final_path.as_posix()}')").fetchone()[0]
        na = con.execute(f"SELECT count(*) FROM read_parquet('{final_path.as_posix()}') WHERE atto_id IS NOT NULL").fetchone()[0]
        nd = con.execute(f"SELECT count(*) FROM read_parquet('{final_path.as_posix()}') WHERE data IS NOT NULL").fetchone()[0]
        ndup = con.execute(f"SELECT count(*) - count(DISTINCT evento_id) FROM read_parquet('{final_path.as_posix()}')").fetchone()[0]

        if verify:
            # Completezza per classe/legislatura: il numero di evento_uri
            # distinti nel finale deve coincidere con il COUNT DISTINCT del
            # LOD (cache_count scritto da fetch_ids). Protegge da dedup
            # aggressivi su evento_id e da batch di dettagli incompleti.
            for leg in legislature:
                for cls in EVENT_QUERIES:
                    count_path = cache_dir / f"count_{leg}_{cls}.json"
                    if not count_path.exists():
                        log.warning("completezza %s leg%d: count cache assente", cls, leg)
                        continue
                    expected = int(json.loads(count_path.read_text(encoding="utf-8"))["n"])
                    got = con.execute(
                        "SELECT count(DISTINCT evento_uri) FROM read_parquet(?) "
                        "WHERE legislatura = ? AND tipo_evento = ?",
                        [final_path.as_posix(), leg, cls],
                    ).fetchone()[0]
                    if got != expected:
                        raise RuntimeError(
                            f"completezza {cls} leg{leg}: {got} eventi distinti, "
                            f"attesi {expected}"
                        )

    log.info("finale: %d eventi, %d con atto, %d con data, %d duplicati",
             n, na, nd, ndup)
    if ndup:
        raise RuntimeError(f"{ndup} evento_id duplicati nel finale")

    events_path.unlink(missing_ok=True)
    links_path.unlink(missing_ok=True)
    organi_path.unlink(missing_ok=True)
    return final_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legislature", nargs="+", type=int, default=[16, 17, 18, 19])
    parser.add_argument("--out", default=".")
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--refresh", action="store_true", help="ignora la cache")
    parser.add_argument("--no-verify", action="store_true", help="salta i controlli di completezza")
    parser.add_argument("--build-only", action="store_true", help="ricostruisce solo dai file in cache")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "_cache"
    if args.refresh and cache_dir.exists():
        for f in cache_dir.rglob("*"):
            if f.is_file():
                f.unlink()
    cache_dir.mkdir(exist_ok=True)

    if not args.build_only:
        if not endpoint_alive():
            log.error("endpoint non raggiungibile: nessuna richiesta inviata. "
                      "Riprova più tardi o usa --build-only con la cache esistente.")
            return 2
        try:
            for leg in args.legislature:
                log.info("=== Legislatura %d ===", leg)
                for cls, template in EVENT_QUERIES.items():
                    log.info("eventi %s Leg%d", cls, leg)
                    ids = fetch_ids(cls, leg, cache_dir, verify=not args.no_verify)
                    if ids:
                        fetch_details(cls, leg, ids, template, cache_dir,
                                      args.batch, verify=not args.no_verify)
                log.info("link Leg%d", leg)
                fetch_links(leg, cache_dir, args.batch)
                log.info("organi Leg%d", leg)
                fetch_organi(leg, cache_dir)
        except EndpointUnavailable as exc:
            log.error("endpoint non disponibile (%s). Cache salvata in %s.", exc, cache_dir)
            log.error("Rilancia lo stesso comando per riprendere.")
            return 2

    build_final(out_dir, cache_dir, args.legislature, verify=not args.no_verify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
