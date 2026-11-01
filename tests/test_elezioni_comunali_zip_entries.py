"""Contract elezioni_comunali — lo zip DAIT non contiene solo CSV.

pure_unit: il 2024 il Ministero ha ri-zippato l'archivio aggiungendo un foglio
XLSX (``Comunali_*_ListeLivSez.xlsx``) accanto ai CSV. Il preprocess passava
ogni entry a ``csv.reader`` e moriva con ``_csv.Error: new-line character seen
in unquoted field``. ``iter_text_entries`` è il punto unico che filtra le entry
testuali: un revert a "parse tutto" deve fallire qui.
"""
from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "elezioni-comunali"

XLSX_ENTRY = "comunali-20240609/Comunali_20240609_ListeLivSez.xlsx"
LISTE_ENTRY = "comunali-20240609/Liste&candidati.csv"
SCRUTINI_ENTRY = "comunali-20240609/scrutini.csv"


def _load_preprocess():
    spec = importlib.util.spec_from_file_location(
        "elezioni_comunali_preprocess", DATASET / "preprocess.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip_bytes() -> bytes:
    """Zip sintetico nel layout reale: xlsx binario + due CSV + rumore."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("comunali-20240609/", "")
        zf.writestr(XLSX_ENTRY, b"PK\x03\x04\xff\xfe\x00\x01binary xlsx\x00\x00")
        zf.writestr(LISTE_ENTRY, "REGIONE;PROVINCIA;COMUNE;COGNOME;NOME\nLazio;Roma;Roma;Rossi;Mario\n")
        zf.writestr(SCRUTINI_ENTRY, "REGIONE;PROVINCIA;COMUNE;ELETTORI;VOTANTI\nLazio;Roma;Roma;1000;700\n")
        zf.writestr("comunali-20240609/~lock.csv", "REGIONE\nspazzatura\n")
        zf.writestr("comunali-20240609/._meta.csv", "REGIONE\nspazzatura\n")
    return buffer.getvalue()


def _entries():
    preprocess = _load_preprocess()
    with zipfile.ZipFile(io.BytesIO(_zip_bytes())) as zf:
        return list(preprocess.iter_text_entries(zf))


def test_binary_xlsx_non_viene_parsato_come_csv():
    entries = _entries()
    names = [base for base, _rows in entries]

    assert "Comunali_20240609_ListeLivSez.xlsx" not in names
    assert names == ["Liste&candidati.csv", "scrutini.csv"]


def test_entry_csv_e_temporanee_sono_escluse():
    names = [base for base, _rows in _entries()]

    assert "~lock.csv" not in names
    assert "._meta.csv" not in names


def test_le_righe_dei_csv_restano_leggibili():
    rows_by_name = {base: rows for base, rows in _entries()}

    assert rows_by_name["Liste&candidati.csv"][0][3] == "COGNOME"
    assert rows_by_name["scrutini.csv"][1] == ["Lazio", "Roma", "Roma", "1000", "700"]
