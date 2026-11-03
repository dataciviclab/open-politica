#!/usr/bin/env python3
"""Scarica e normalizza i CSV delle elezioni comunali da Eligendo.

Uso: python preprocess.py <anno> <output.csv>
"""

import csv
import io
import os
import re
import sys
import urllib.request
import zipfile

BASE_URL = "https://dait.interno.gov.it/documenti/opendata/comunali"

# Tornate con dati testuali (CSV/TXT) compatibili con il parser unificato.
# Esclusi perché solo XLSX: 1964, 1970, 1975, 1980, 1985, 1990, 2022, 2023,
# 2025, 2026. Esclusa 2024-11-17 (formato per sezione).
DATES: dict[int, list[str]] = {
    1989: ["19890101", "19890108", "19890115", "19890122", "19890129", "19890305", "19890312", "19890319", "19890409", "19890423", "19890507", "19890528", "19890611", "19890702", "19890706", "19890709", "19890716", "19890723", "19890730", "19890903", "19890917", "19890924", "19891008", "19891015", "19891022", "19891029", "19891105", "19891112", "19891126", "19891203", "19891210"],
    1991: ["19910113", "19910120", "19910224", "19910310", "19910317", "19910324", "19910331", "19910407", "19910421", "19910512", "19910519", "19910602", "19910609", "19910616", "19910623", "19910630", "19910707", "19910714", "19910728", "19910922", "19910929", "19911124", "19911212", "19911215"],
    1992: ["19920607", "19920627", "19920705", "19920926", "19920927", "19921213"],
    1993: ["19930606", "19931121"],
    1994: ["19940612", "19941120"],
    1995: ["19950423", "19950528", "19951119"],
    1996: ["19960602", "19960609", "19961117", "19961201"],
    1997: ["19970427", "19971116", "19971130"],
    1998: ["19980524", "19981129"],
    1999: ["19990613"],
    2000: ["20000416", "20000430", "20000604", "20001112"],
    2001: ["20010513"],
    2002: ["20020526"],
    2003: ["20030525", "20030608", "20030622"],
    2004: ["20040612", "20040626"],
    2005: ["20050403", "20050417", "20050508", "20051127"],
    2006: ["20060528", "20060604", "20060611", "20060618", "20060709", "20060716", "20061001"],
    2007: ["20070527", "20070610", "20070617", "20070715"],
    2008: ["20080413", "20080427", "20080608", "20080615"],
    2009: ["20090607", "20091129"],
    2010: ["20100328", "20100411", "20100418", "20100530", "20101128"],
    2011: ["20110515", "20110522", "20111127"],
    2012: ["20120506", "20120610", "20120617", "20120624", "20121028"],
    2013: ["20130526", "20131117"],
    2014: ["20140525", "20141026"],
    2015: ["20150531", "20151115"],
    2016: ["20160605", "20161113"],
    2017: ["20170611", "20171105"],
    2018: ["20180610", "20180729", "20181021"],
    2019: ["20190526", "20190616", "20190623", "20190707", "20190714", "20191110"],
    2020: ["20200920", "20201025"],
    2021: ["20211003", "20211010", "20211107"],
    2024: ["20240609", "20240728"],
}

SOURCES: dict[int, list[tuple[str, str, bool]]] = {
    year: [
        (f"{BASE_URL}/comunali-{d}.zip", f"{d[:4]}-{d[4:6]}-{d[6:]}", True)
        for d in dates
    ]
    for year, dates in DATES.items()
}

COL_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^DATAELEZIONE$", re.I), "data_elezione_raw"),
    (re.compile(r"^REG(IONE)?$", re.I), "regione"),
    (re.compile(r"^PROV(INCIA)?$", re.I), "provincia"),
    (re.compile(r"^COMUNE$", re.I), "comune"),
    (re.compile(r"^TURNO$", re.I), "turno"),
    (re.compile(r"^(ELETTORI(TOT)?|ELETTORITOTALI)$", re.I), "elettori"),
    (re.compile(r"^(ELETTORI_MASCHI|ELETTORIMASCHI)$", re.I), "elettori_maschi"),
    (re.compile(r"^(VOTANTI(TOT)?|NUMVOTANTITOTALI|VOTANTITOTALI)$", re.I), "votanti"),
    (re.compile(r"^(VOTANTI_MASCHI|VOTANTIMASCHI|NUMVOTANTIMASCHI)$", re.I), "votanti_maschi"),
    (re.compile(r"^(SCHEDE_BIANCHE|SKBIANCHE|SCHEDEBIANCHE)$", re.I), "schede_bianche"),
    (re.compile(r"^(COGNOME|COGNOME_CANDIDATO)$", re.I), "cognome"),
    (re.compile(r"^(NOME|NOME_CANDIDATO)$", re.I), "nome"),
    (re.compile(r"^(DATANASCITA|DATA_NASCITA)$", re.I), "data_nascita"),
    (re.compile(r"^(LUOGONASCITA|LUOGO_NASCITA)$", re.I), "luogo_nascita"),
    (re.compile(r"^SESSO$", re.I), "sesso"),
    (re.compile(r"^(CODTIPOELETTO|ELETTO)$", re.I), "cod_tipo_elettore"),
    (re.compile(r"^(VOTI_CANDIDATO|VOTICAND(IDATO)?|VOTICANDIDSINDACO)$", re.I), "voti_candidato"),
    (re.compile(r"^(LISTA|DESCR_LISTA|DESCRLISTA)$", re.I), "lista"),
    (re.compile(r"^(VOTI_LISTA|VOTILISTA)$", re.I), "voti_lista"),
    (re.compile(r"^(SEGGI_LISTA|SEGGILISTA|seggilista)$", re.I), "seggi_lista"),
    (re.compile(r"^votivalidiliste$", re.I), "voti_validi_liste"),
    (re.compile(r"^votivalidicandidsindaco$", re.I), "voti_validi_candidato"),
    (re.compile(r"^codtipoinvalidita$", re.I), "cod_tipo_invalidita"),
]


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def normalize_number(val: str) -> str:
    val = val.strip().strip('"')
    if not val or val in ("***", "-", "N.D."):
        return ""
    if "," in val:
        val = val.replace(".", "").replace(",", ".")
        if val.endswith(".0"):
            val = val[:-2]
    else:
        val = val.replace(".", "")
    return val


def smart_decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_csv(content: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(content), delimiter=";")
    return [row for row in reader if any(cell.strip() for cell in row)]


TEXT_SUFFIXES = (".csv", ".txt")


def iter_text_entries(zf: zipfile.ZipFile):
    """Yield ``(basename, rows)`` per le sole entry testuali dello zip.

    L'archivio DAIT non contiene solo CSV: dal 2024 include anche fogli XLSX
    (``Comunali_*_ListeLivSez.xlsx``). Passare un binario a ``csv.reader``
    solleva ``_csv.Error``; filtrare qui tiene il contratto in un punto solo.
    """
    for name in zf.namelist():
        base = os.path.basename(name)
        if base.startswith("~") or base.startswith("."):
            continue
        if not base.lower().endswith(TEXT_SUFFIXES):
            continue
        yield base, parse_csv(smart_decode(zf.read(name)))


def normalize_columns(header: list[str]) -> tuple[list[str], list[int]]:
    norm = []
    indices = []
    for i, col in enumerate(header):
        col = col.strip().strip('"')
        mapped = None
        for pattern, name in COL_MAP:
            if pattern.match(col):
                mapped = name
                break
        if mapped:
            norm.append(mapped)
            indices.append(i)
    return norm, indices


def extract_scrutini_from_txt(zf: zipfile.ZipFile) -> list[list[str]]:
    for base, rows in iter_text_entries(zf):
        if "preferenze" in base.lower():
            continue
        if rows:
            return rows
    return []


def process_2016_2020(url: str, election_date: str) -> list[dict]:
    raw = download(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        raw_rows = extract_scrutini_from_txt(zf)

    if not raw_rows:
        return []

    header = raw_rows[0]
    col_names, col_indices = normalize_columns(header)

    records = []
    for row in raw_rows[1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        rec = {"data_elezione": election_date}
        for name, idx in zip(col_names, col_indices):
            if idx < len(row):
                val = row[idx].strip().strip('"')
                if name in ("elettori", "elettori_maschi", "votanti", "votanti_maschi",
                            "schede_bianche", "voti_candidato", "voti_lista",
                            "seggi_lista", "turno"):
                    val = normalize_number(val)
                rec[name] = val
        if "cognome" in rec and "nome" in rec:
            rec["candidato"] = f"{rec.pop('cognome', '')} {rec.pop('nome', '')}".strip()
        records.append(rec)

    return records


def process_2021(url: str, election_date: str) -> list[dict]:
    raw = download(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        raw_rows = extract_scrutini_from_txt(zf)

    if not raw_rows:
        return []

    header = raw_rows[0]
    col_names, col_indices = normalize_columns(header)

    records = []
    for row in raw_rows[1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        rec = {"data_elezione": election_date}
        for name, idx in zip(col_names, col_indices):
            if idx < len(row):
                val = row[idx].strip().strip('"')
                if name in ("elettori", "elettori_maschi", "votanti", "votanti_maschi",
                            "schede_bianche", "voti_candidato", "voti_lista",
                            "seggi_lista", "turno", "voti_validi_liste",
                            "voti_validi_candidato", "turno"):
                    val = normalize_number(val)
                rec[name] = val
        if "cognome" in rec and "nome" in rec:
            rec["candidato"] = f"{rec.pop('cognome', '')} {rec.pop('nome', '')}".strip()
        records.append(rec)

    return records


def process_2024(url: str, election_date: str) -> list[dict]:
    raw = download(url)

    scrutini = []
    liste = []

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for base, rows in iter_text_entries(zf):
            if not rows:
                continue
            if "scrutini" in base.lower():
                scrutini = rows
            elif "liste" in base.lower() or "candidati" in base.lower():
                liste = rows

    if not liste:
        return []

    # Parse scrutini into lookup: (regione, provincia, comune, turno) -> turnout
    turnout_lookup = {}
    if scrutini:
        s_header = scrutini[0]
        s_names, s_indices = normalize_columns(s_header)
        for row in scrutini[1:]:
            if not row or not any(cell.strip() for cell in row):
                continue
            vals = {}
            for name, idx in zip(s_names, s_indices):
                if idx < len(row):
                    val = row[idx].strip().strip('"')
                    if name in ("elettori", "elettori_maschi", "votanti",
                                "votanti_maschi", "schede_bianche", "turno"):
                        val = normalize_number(val)
                    vals[name] = val
            key = (vals.get("regione", ""), vals.get("provincia", ""),
                   vals.get("comune", ""), vals.get("turno", ""))
            turnout_lookup[key] = vals

    # Parse liste+candidati
    l_header = liste[0]
    l_names, l_indices = normalize_columns(l_header)

    records = []
    for row in liste[1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        rec = {"data_elezione": election_date}
        for name, idx in zip(l_names, l_indices):
            if idx < len(row):
                val = row[idx].strip().strip('"')
                if name in ("voti_candidato", "voti_lista", "seggi_lista", "turno"):
                    val = normalize_number(val)
                rec[name] = val
        if "cognome" in rec and "nome" in rec:
            rec["candidato"] = f"{rec.pop('cognome', '')} {rec.pop('nome', '')}".strip()

        # Merge turnout from scrutini
        tkey = (rec.get("regione", ""), rec.get("provincia", ""),
                rec.get("comune", ""), rec.get("turno", ""))
        if tkey in turnout_lookup:
            tv = turnout_lookup[tkey]
            rec["elettori"] = tv.get("elettori", "")
            rec["elettori_maschi"] = tv.get("elettori_maschi", "")
            rec["votanti"] = tv.get("votanti", "")
            rec["votanti_maschi"] = tv.get("votanti_maschi", "")
            rec["schede_bianche"] = tv.get("schede_bianche", "")

        records.append(rec)

    return records


# Colonne attese da clean.sql: garantite anche per le tornate storiche che non
# le portano (es. 1989-1992 senza turno/candidato).
CANONICAL_COLS = [
    "data_elezione",
    "regione",
    "provincia",
    "comune",
    "turno",
    "candidato",
    "lista",
    "voti_candidato",
    "voti_lista",
    "seggi_lista",
    "elettori",
    "elettori_maschi",
    "votanti",
    "votanti_maschi",
    "schede_bianche",
]


def ensure_canonical(records: list[dict]) -> None:
    """Garantisce le colonne attese da clean.sql su ogni record."""
    for rec in records:
        for col in CANONICAL_COLS:
            rec.setdefault(col, "")


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    output = sys.argv[2] if len(sys.argv) > 2 else "raw_input.csv"

    sources = SOURCES.get(year)
    if not sources:
        print(f"Nessuna fonte configurata per l'anno {year}", file=sys.stderr)
        sys.exit(1)

    all_records: list[dict] = []
    for url, election_date, is_zip in sources:
        print(f"  {election_date} -> download...", file=sys.stderr)
        if election_date == "2024-06-09":
            records = process_2024(url, election_date)
        elif year == 2021:
            records = process_2021(url, election_date)
        else:
            records = process_2016_2020(url, election_date)
        print(f"    {len(records)} righe", file=sys.stderr)
        all_records.extend(records)

    if not all_records:
        print("Nessun dato estratto!", file=sys.stderr)
        sys.exit(1)

    ensure_canonical(all_records)

    fieldnames: list[str] = []
    seen: set[str] = set()
    for rec in all_records:
        for key in rec:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(all_records)

    print(f"Fatto: anno={year} totale={len(all_records)} righe -> {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
