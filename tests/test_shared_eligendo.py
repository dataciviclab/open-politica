"""Contract helper condiviso Eligendo (datasets/_shared/eligendo.py).

pure_unit: download/selezione entry e lettura tabellare CSV/XLSX sono usati dai
preprocess dei dataset elettorali; un errore qui rompe tutte le tornate XLSX.
"""
from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "datasets"))

from _shared.eligendo import merge_on, read_table, select_entries  # noqa: E402


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _xlsx_bytes(header: list[str], rows: list[list]) -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buf = io.BytesIO()
    workbook.save(buf)
    return buf.getvalue()


def test_select_entries_per_nome_ed_estensione():
    payload = _zip_bytes(
        {
            "a/Scrutini Primo Turno.xlsx": b"x",
            "a/Votanti Primo Turno.xlsx": b"y",
            "b/Liste.xlsx": b"z",
        }
    )

    out = select_entries(payload, match="*Scrutini*", only_ext=[".xlsx"])

    assert list(out) == ["Scrutini Primo Turno.xlsx"]


def test_read_table_csv():
    header, rows = read_table(b"REGIONE;COMUNE\nPiemonte;Torino\n", "x.txt")

    assert header == ["REGIONE", "COMUNE"]
    assert rows == [["Piemonte", "Torino"]]


def test_read_table_xlsx_normalizza_i_tipi():
    data = _xlsx_bytes(
        ["REGIONE", "ELETTORI", "DATA"],
        [["Piemonte", 17873.0, datetime(2023, 5, 14)]],
    )

    header, rows = read_table(data, "x.xlsx")

    assert header == ["REGIONE", "ELETTORI", "DATA"]
    assert rows == [["Piemonte", "17873", "2023-05-14"]]


def test_merge_on_aggiunge_le_colonne_mancanti():
    scrutini = [{"comune": "Torino", "elettori": "100"}]
    liste = [{"comune": "Torino", "lista": "PD", "voti_lista": "40"}]

    merged = merge_on(liste, scrutini, keys=["comune"])

    assert merged == [
        {"comune": "Torino", "lista": "PD", "voti_lista": "40", "elettori": "100"}
    ]
