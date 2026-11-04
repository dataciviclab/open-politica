"""Contract elezioni_referendum — ZIP storici senza riga di intestazione.

pure_unit: il referendum 1985 è pubblicato dal DAIT senza header: la prima riga
del .txt è già un record. Prima del fix il parser la trattava come header, non
mappava nessuna colonna e l'anno produceva 0 righe. ``parse_zip_bytes`` deve
riconoscere l'assenza di header e usare lo schema posizionale ``HEADERLESS_COLS``.
"""
from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "elezioni-referendum"

HEADERLESS_ROW = (
    '"PIEMONTE";"ALESSANDRIA";"ACQUI TERME";1;"Indennita\' di contingenza";'
    '"17873";"0";14833;0;6678;7660;231'
)
HEADERED_CSV = (
    '"REGIONE";"PROVINCIA";"COMUNE";"NUM_REFERENDUM";"QUESITO";"ELETTORI";'
    '"ELETTORI_MASCHI";"VOTANTI";"VOTANTI_MASCHI";"NUMVOTISI";"NUMVOTINO";"SCHEDE_BIANCHE"\n'
    '"LOMBARDIA";"MILANO";"MILANO";1;"Divorzio";"1000";"400";"800";"380";"600";"150";"10"\n'
)


def _load_preprocess():
    spec = importlib.util.spec_from_file_location(
        "elezioni_referendum_preprocess", DATASET / "preprocess.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip_bytes(content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("referendum/referendum.txt", content)
    return buffer.getvalue()


def test_zip_senza_header_usa_schema_posizionale():
    preprocess = _load_preprocess()
    records = preprocess.parse_zip_bytes(_zip_bytes(HEADERLESS_ROW), "1985-06-09")

    assert len(records) == 1
    rec = records[0]
    assert rec["data_elezione"] == "1985-06-09"
    assert rec["regione"] == "PIEMONTE"
    assert rec["provincia"] == "ALESSANDRIA"
    assert rec["comune"] == "ACQUI TERME"
    assert rec["num_quesito"] == "1"
    assert rec["elettori"] == "17873"
    assert rec["voti_si"] == "6678"
    assert rec["voti_no"] == "7660"


def test_zip_con_header_resta_invariato():
    preprocess = _load_preprocess()
    records = preprocess.parse_zip_bytes(_zip_bytes(HEADERED_CSV), "2022-06-12")

    assert len(records) == 1
    rec = records[0]
    assert rec["regione"] == "LOMBARDIA"
    assert rec["comune"] == "MILANO"
    assert rec["voti_si"] == "600"
    assert rec["voti_no"] == "150"
