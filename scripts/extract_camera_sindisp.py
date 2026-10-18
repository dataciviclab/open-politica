#!/usr/bin/env python3
"""Estrazione deterministica del sindacato ispettivo della Camera (ocd:aic).

Perché uno script e non il source `sparql` del toolkit:
il plugin keyset inietta `FILTER(?key > ...)` DOPO la WHERE (prima di
ORDER BY), sintassi che Virtuoso rifiuta. Qui la paginazione keyset è
implementata a mano, con il FILTER dentro la WHERE.

Uso:
    python preprocess.py --legislature 19 --mode ato --out camera_sindisp.csv
    python preprocess.py --legislature 19 --mode firmatari --out ...
    python preprocess.py --legislature 19 --mode destinatari --out ...

Il file di output è un CSV con le colonne SPARQL originali; il clean SQL
fa parsing, normalizzazione e dedup.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

ENDPOINT = "https://dati.camera.it/sparql"
PAGE_SIZE = 10000
MAX_ATTEMPTS = 6

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("camera-sindisp")

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 DataCivicLab/1.0",
        "Accept": "application/sparql-results+json",
    }
)

PREFIXES = """PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

LEG_IRI = "http://dati.camera.it/ocd/legislatura.rdf/repubblica_{leg}"

# Nota: il filtro (!STRENDS e keyset) sta in una sottoquery SENZA OPTIONAL.
# Su questo Virtuoso, FILTER + OPTIONAL nella stessa WHERE può essere ignorato
# dall'ottimizzatore (verificato 2026-10-18): la sottoquery isola il filtro.
QUERY_ATO = PREFIXES + """
SELECT DISTINCT ?atto ?tipo ?numero ?data ?titolo ?descrizione ?ramo
       ?primo ?primo_label ?concluso ?risposta
WHERE {
  {
    SELECT DISTINCT ?atto WHERE {
      ?atto a ocd:aic ;
            ocd:rif_leg <LEG_IRI> .
      FILTER(!STRENDS(STR(?atto), "_S"))
      {filter}
    }
    ORDER BY STR(?atto)
    LIMIT PAGE_SIZE
  }
  OPTIONAL { ?atto dc:type ?tipo }
  OPTIONAL { ?atto dc:identifier ?numero }
  OPTIONAL { ?atto dc:date ?data }
  OPTIONAL { ?atto dc:title ?titolo }
  OPTIONAL { ?atto dc:description ?descrizione }
  OPTIONAL { ?atto ocd:ramo ?ramo }
  OPTIONAL {
    ?atto ocd:primo_firmatario ?primo .
    OPTIONAL { ?primo rdfs:label ?primo_label }
  }
  OPTIONAL { ?atto ocd:concluso ?concluso }
  OPTIONAL { ?atto ocd:risposta ?risposta }
}
ORDER BY STR(?atto)
"""

QUERY_FIRMATARI = PREFIXES + """
SELECT ?key ?atto ?firm ?ruolo ?label
WHERE {
  {
    SELECT DISTINCT ?key ?atto ?firm ?ruolo WHERE {
      {
        ?atto a ocd:aic ;
              ocd:primo_firmatario ?firm ;
              ocd:rif_leg <LEG_IRI> .
        BIND("primo" AS ?ruolo)
      }
      UNION
      {
        ?atto a ocd:aic ;
              ocd:altro_firmatario ?firm ;
              ocd:rif_leg <LEG_IRI> .
        BIND("altro" AS ?ruolo)
      }
      FILTER(!STRENDS(STR(?atto), "_S"))
      BIND(CONCAT(STR(?atto), "|", STR(?firm), "|", ?ruolo) AS ?key)
      {filter}
    }
    ORDER BY ?key
    LIMIT PAGE_SIZE
  }
  OPTIONAL { ?firm rdfs:label ?label }
}
ORDER BY ?key
"""

QUERY_DESTINATARI = PREFIXES + """
SELECT ?key ?atto ?dest ?label ?risposta
WHERE {
  {
    SELECT DISTINCT ?key ?atto ?dest WHERE {
      ?atto a ocd:aic ;
            ocd:destinatario ?dest ;
            ocd:rif_leg <LEG_IRI> .
      FILTER(!STRENDS(STR(?atto), "_S"))
      BIND(CONCAT(STR(?atto), "|", STR(?dest)) AS ?key)
      {filter}
    }
    ORDER BY ?key
    LIMIT PAGE_SIZE
  }
  OPTIONAL { ?dest rdfs:label ?label }
  OPTIONAL { ?atto ocd:risposta ?risposta }
}
ORDER BY ?key
"""


def query(sparql: str, timeout: int = 240) -> list[dict]:
    """Esegue una SELECT e restituisce i bindings (valori primitivi)."""
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = SESSION.post(ENDPOINT, data={"query": sparql}, timeout=timeout)
            if resp.status_code in (405, 414):
                resp = SESSION.get(ENDPOINT, params={"query": sparql}, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
            return [
                {k: v.get("value", "") for k, v in row.items()}
                for row in payload["results"]["bindings"]
            ]
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
            wait = min(60, 4 * (2**attempt))
            log.warning("query fallita (tentativo %d): %s — retry in %ds", attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"query fallita dopo {MAX_ATTEMPTS} tentativi: {last_error}")


def _replace_query(template: str, leg: int) -> str:
    return (
        template.replace("LEG_IRI", LEG_IRI.replace("{leg}", str(leg)))
        .replace("PAGE_SIZE", str(PAGE_SIZE))
    )


def fetch_pages(
    template: str,
    leg: int,
    key_expr: str,
    key_col: str,
    key_is_uri: bool,
) -> list[dict]:
    """Paginazione keyset manuale con FILTER dentro la WHERE.

    ``key_expr`` è l'espressione SPARQL usata in FILTER/ORDER BY
    (es. ``?key`` oppure ``STR(?atto)``); ``key_col`` è la colonna del
    binding da cui leggere l'ultimo valore (es. ``key`` o ``atto``).
    """
    base = _replace_query(template, leg)
    rows: list[dict] = []
    last: str | None = None
    page = 0
    while True:
        page += 1
        if last is None:
            filtro = ""
        else:
            literal = f"<{last}>" if key_is_uri else json.dumps(last)
            filtro = f"FILTER({key_expr} > {literal})"
        q = base.replace("{filter}", filtro) + f" LIMIT {PAGE_SIZE}"
        log.info("pagina %d (last=%s)", page, (last or "-")[:80])
        bindings = query(q)
        if not bindings:
            # Pagina vuota: può essere throttle. Ritenta qualche volta.
            for attempt in range(3):
                wait = 10 * (attempt + 1)
                log.warning("pagina vuota — retry in %ds", wait)
                time.sleep(wait)
                bindings = query(q)
                if bindings:
                    break
            if not bindings:
                break
        rows.extend(bindings)
        keys = [b[key_col] for b in bindings if b.get(key_col)]
        if not keys:
            break
        last = max(keys)
        if len(bindings) < PAGE_SIZE:
            break
    return rows


def write_parquet(path: Path, rows: list[dict], columns: list[str]) -> None:
    """Scrive parquet (non CSV): i testi lunghi con virgole/newline non
    vengono reinterpretati dal profiler raw del toolkit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    table = pa.table({col: [r.get(col, "") for r in rows] for col in columns})
    pq.write_table(table, tmp)
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legislature", type=int, required=True)
    parser.add_argument("--mode", choices=["ato", "firmatari", "destinatari"], required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.mode == "ato":
        rows = fetch_pages(
            QUERY_ATO, args.legislature, "STR(?atto)", "atto", key_is_uri=False
        )
        columns = [
            "atto", "tipo", "numero", "data", "titolo", "descrizione",
            "ramo", "primo", "primo_label", "concluso", "risposta",
        ]
    elif args.mode == "firmatari":
        rows = fetch_pages(
            QUERY_FIRMATARI, args.legislature, "?key", "key", key_is_uri=False
        )
        columns = ["key", "atto", "firm", "ruolo", "label"]
    else:
        rows = fetch_pages(
            QUERY_DESTINATARI, args.legislature, "?key", "key", key_is_uri=False
        )
        columns = ["key", "atto", "dest", "label", "risposta"]

    log.info("righe estratte: %d", len(rows))
    write_parquet(Path(args.out), rows, columns)
    log.info("scritto %s", args.out)


if __name__ == "__main__":
    main()
