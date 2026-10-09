#!/usr/bin/env python3
"""Scarica e normalizza la serie storica annuale DAIT (amministratori comunali).

Per ogni anno 1986–2025 scarica il CSV dello snapshot al 31/12 dal portale DAIT,
gestisce encoding misti (utf-8 / latin-1) e unifica le due ere schema:
  - Era A (1986–2022): 28 colonne, DATA_NOMINA, PARTITO_LISTA_COALIZIONE
  - Era B (2023–2025): 34 colonne, DATA_INIZIO_CARICA, LISTA_APPARTENENZA, INCARICO/FUNZIONE

Output: un singolo CSV normalizzato (header snake_case, colonne unificate).

Uso:
  python preprocess.py --out .                        # tutti gli anni
  python preprocess.py --years 2023:2025 --out .      # sottoinsieme (pilot)
  python preprocess.py --years 2014,2016,2020 --out . # anni singoli
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://dait.interno.gov.it/documenti"

# Mappa anno → filename del CSV "comuni" sul portale DAIT.
# Il naming cambia nel tempo (4 pattern): _0, _1, _3112, 3112.
# Catturata via scraping delle pagine open-data il 2026-10-09.
URL_MAP: dict[int, str] = {
    1986: "storico_amministratori_comuni31121986_0.csv",
    1987: "storico_amministratori_comuni31121987_0.csv",
    1988: "storico_amministratori_comuni31121988_0.csv",
    1989: "storico_amministratori_comuni31121989_0.csv",
    1990: "storico_amministratori_comuni31121990_0.csv",
    1991: "storico_amministratori_comuni31121991_0.csv",
    1992: "storico_amministratori_comuni31121992_0.csv",
    1993: "storico_amministratori_comuni31121993_0.csv",
    1994: "storico_amministratori_comuni31121994_0.csv",
    1995: "storico_amministratori_comuni31121995_0.csv",
    1996: "storico_amministratori_comuni31121996_1.csv",
    1997: "storico_amministratori_comuni31121997.csv",
    1998: "storico_amministratori_comuni31121998.csv",
    1999: "storico_amministratori_comuni31121999_0.csv",
    2000: "storico_amministratori_comuni31122000.csv",
    2001: "storico_amministratori_comuni31122001_0.csv",
    2002: "storico_amministratori_comuni31122002_0.csv",
    2003: "storico_amministratori_comuni31122003.csv",
    2004: "storico_amministratori_comuni31122004_0.csv",
    2005: "storico_amministratori_comuni31122005_0.csv",
    2006: "storico_amministratori_comuni31122006.csv",
    2007: "storico_amministratori_comuni31122007_0.csv",
    2008: "storico_amministratori_comuni31122008_0.csv",
    2009: "storico_amministratori_comuni31122009_0.csv",
    2010: "storico_amministratori_comuni31122010.csv",
    2011: "storico_amministratori_comuni31122011.csv",
    2012: "storico_amministratori_comuni31122012.csv",
    2013: "storico_amministratori_comuni_31122013.csv",
    2014: "storico_amministratori_comuni_31122014.csv",
    2015: "storico_amministratori_comuni_31122015.csv",
    2016: "storico_amministratori_comuni_31122016.csv",
    2017: "storico_amministratori_comuni31122017.csv",
    2018: "storico_amministratori_comuni31122018.csv",
    2019: "storico_amministratori_comuni31122019.csv",
    2020: "storico_amministratori_comuni31122020.csv",
    2021: "storico_amministratori_comuni31122021.csv",
    2022: "storico_amministratori_comuni31122022.csv",
    2023: "storico_amministratori_comuni31122023.csv",
    2024: "storico_amministratori_comuni31122024.csv",
    2025: "storico_amministratori_comuni31122025.csv",
}

# Header raw (UPPER, entrambe le ere) → nome unificato snake_case.
# Gestisce le rinomine tra Era A e Era B.
COL_MAP: dict[str, str] = {
    # Territorio (identico in entrambe le ere)
    "CODICE_REGIONE": "codice_regione",
    "DESCRIZIONE_REGIONE": "descrizione_regione",
    "CODICE_PROVINCIA": "codice_provincia",
    "DESCRIZIONE_PROVINCIA": "descrizione_provincia",
    "CODICE_COMUNE": "codice_comune",
    "DESCRIZIONE_COMUNE": "descrizione_comune",
    "SIGLA_PROVINCIA": "sigla_provincia",
    "ISTAT_CODICE_COMUNE": "istat_codice_comune",
    # Popolazione (rinominata in Era B)
    "POPOLAZIONE_CENSITA": "popolazione_censita",
    "POPOLAZIONE_CENSITA_ALLA_DATA_ELEZIONE": "popolazione_censita",
    # Contesto elezione
    "MAGGIORITARIO_PROPORZIONALE": "maggioritario_proporzionale",
    "DESCRIZIONE_TEMPO_GESTIONE": "descrizione_tempo_gestione",
    "DATA_ELEZIONE": "data_elezione",
    "DATA_BALLOTTAGGIO": "data_ballottaggio",
    "CONSIGLIERI_SPETTANTI": "consiglieri_spettanti",
    "ASSESSORI_ASSEGNATI": "assessori_assegnati",
    # Persona
    "COGNOME": "cognome",
    "NOME": "nome",
    "SESSO": "sesso",
    "DATA_NASCITA": "data_nascita",
    "SEDE_NASCITA": "sede_nascita",
    # Carica
    "LIVELLO_CARICA": "livello_carica",
    "DESCRIZIONE_CARICA": "descrizione_carica",
    "DATA_NOMINA": "data_inizio_carica",  # Era A
    "DATA_INIZIO_CARICA": "data_inizio_carica",  # Era B
    "DATA_CESSAZIONE": "data_cessazione",
    # Solo Era B
    "CONSIGLIERI_ELETTI": "consiglieri_eletti",
    "INCARICO": "incarico",
    "DATA_INIZIO_INCARICO": "data_inizio_incarico",
    "DATA_FINE_INCARICO": "data_fine_incarico",
    "FUNZIONE": "funzione",
    "DATA_INIZIO_FUNZIONE": "data_inizio_funzione",
    "DATA_FINE_FUNZIONE": "data_fine_funzione",
    # Lista (rinominata in Era B)
    "PARTITO_LISTA_COALIZIONE": "lista_appartenenza",  # Era A
    "LISTA_APPARTENENZA/COLLEGAMENTO": "lista_appartenenza",  # Era B
    # Studio / professione
    "TITOLO_DI_STUDIO": "titolo_studio",
    "PROFESSIONE": "professione",
}

# Colonne droppate deliberatamente:
#   SIGLA_TITOLO_ACCADEMICO — solo Era A, superseded da titolo_studio
DROPPED = {"SIGLA_TITOLO_ACCADEMICO"}

# Ordine colonne di output
OUTPUT_COLS = [
    "anno_snapshot",
    "codice_regione", "descrizione_regione",
    "codice_provincia", "descrizione_provincia",
    "codice_comune", "descrizione_comune",
    "sigla_provincia", "istat_codice_comune",
    "popolazione_censita",
    "maggioritario_proporzionale", "descrizione_tempo_gestione",
    "data_elezione", "data_ballottaggio",
    "consiglieri_spettanti", "consiglieri_eletti", "assessori_assegnati",
    "cognome", "nome", "sesso", "data_nascita", "sede_nascita",
    "livello_carica", "descrizione_carica",
    "data_inizio_carica", "data_cessazione",
    "incarico", "data_inizio_incarico", "data_fine_incarico",
    "funzione", "data_inizio_funzione", "data_fine_funzione",
    "lista_appartenenza", "titolo_studio", "professione",
]


def smart_decode(data: bytes) -> str:
    """Decodifica con fallback: utf-8 → latin-1 → replace."""
    for enc in ("utf-8-sig", "utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def download(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def normalize_header_cell(cell: str) -> str:
    """Pulisce una cella di header: strip spazi e virgolette."""
    return cell.strip().strip('"').strip()


def map_header(header: list[str]) -> tuple[list[str], list[int]]:
    """Mappa header raw → colonne unificate. Ritorna (nomi, indici)."""
    names: list[str] = []
    indices: list[int] = []
    for i, raw in enumerate(header):
        cleaned = normalize_header_cell(raw)
        if cleaned in DROPPED:
            continue
        mapped = COL_MAP.get(cleaned)
        if mapped and mapped not in names:
            names.append(mapped)
            indices.append(i)
    return names, indices


def clean_cell(val: str) -> str:
    """Rimuove caratteri di riga embedded da una cella."""
    return val.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


def parse_year(year: int, filename: str):
    """Scarica e normalizza un anno. Genera record dict (streaming, yield)."""
    url = f"{BASE_URL}/{filename}"
    print(f"  {year}: download {filename} ...", flush=True)
    raw = download(url)
    content = smart_decode(raw)
    del raw  # libera subito i bytes grezzi

    # normalizza newline nel contenuto intero prima del parsing
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    reader = csv.reader(io.StringIO(content), delimiter=";")
    del content

    # Salta righe vuote iniziali, poi leggi header
    header = None
    for row in reader:
        if any(cell.strip() for cell in row):
            header = row
            break
    if not header:
        print(f"  {year}: WARNING — header non trovato, skip", file=sys.stderr)
        return

    col_names, col_indices = map_header(header)
    era = "B" if "consiglieri_eletti" in col_names else "A"

    n = 0
    for row in reader:
        if not row or not any(cell.strip() for cell in row):
            continue
        rec: dict = {"anno_snapshot": year}
        for name, idx in zip(col_names, col_indices):
            if idx < len(row):
                rec[name] = clean_cell(row[idx].strip().strip('"'))
            else:
                rec[name] = ""
        n += 1
        yield rec

    print(f"  {year}: era {era}, {len(col_names)} colonne, {n} righe", flush=True)


def parse_years_spec(spec: str | None) -> list[int]:
    """Parsing argomento --years: '2014:2025' | '2014,2016' | None (tutti)."""
    if not spec:
        return sorted(URL_MAP.keys())
    years: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if ":" in part:
            lo, hi = part.split(":", 1)
            years.extend(range(int(lo), int(hi) + 1))
        else:
            years.append(int(part))
    # mantieni solo anni con URL noto, ordina
    return sorted(y for y in years if y in URL_MAP)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=".", help="Directory di output")
    parser.add_argument("--years", default=None,
                        help="Sottoinsieme anni: '2014:2025' | '2014,2016' (default: tutti)")
    args = parser.parse_args()

    years = parse_years_spec(args.years)
    if not years:
        print("Nessun anno valido selezionato", file=sys.stderr)
        sys.exit(1)

    print(f"Serie storica DAIT amministratori comunali — {len(years)} anni "
          f"({years[0]}–{years[-1]})", flush=True)

    out_path = Path(args.out) / "storico_amministratori.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Streaming: apre il CSV una volta, scrive anno per anno senza accumulare.
    total = 0
    failed: list[int] = []
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLS, delimiter=";",
            quoting=csv.QUOTE_MINIMAL, restval="",
            lineterminator="\n",
        )
        writer.writeheader()
        for year in years:
            try:
                for rec in parse_year(year, URL_MAP[year]):
                    writer.writerow(rec)
                    total += 1
            except Exception as exc:
                print(f"  {year}: ERRORE {exc}", file=sys.stderr)
                failed.append(year)

    if total == 0:
        print("Nessuna riga prodotta", file=sys.stderr)
        sys.exit(1)

    print(f"\nOutput: {out_path} — {total} righe totali", flush=True)
    if failed:
        print(f"Anni falliti: {failed}", file=sys.stderr)
        # non fallire il run se almeno un anno è andato a buon fine
        # (gli anni mancanti saranno un gap documentato)


if __name__ == "__main__":
    main()
