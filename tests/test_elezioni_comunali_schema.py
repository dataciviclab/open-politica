"""Contract elezioni_comunali — schema storico e date.

pure_unit: le tornate 1989-1992 non hanno turno/candidato; ``ensure_canonical``
deve garantire le 15 colonne attese da clean.sql. ``SOURCES`` è generato da
``DATES``: il formato data deve restare ``YYYY-MM-DD`` e le annualità XLSX
(es. 1990) non devono entrare nel perimetro.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "elezioni-comunali"


def _load_preprocess():
    spec = importlib.util.spec_from_file_location(
        "elezioni_comunali_preprocess", DATASET / "preprocess.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ensure_canonical_riempie_le_colonne_mancanti():
    preprocess = _load_preprocess()
    records = [{"data_elezione": "1989-06-11", "regione": "SARDEGNA", "lista": "MSI"}]

    preprocess.ensure_canonical(records)

    assert set(preprocess.CANONICAL_COLS) <= set(records[0])
    assert records[0]["turno"] == ""
    assert records[0]["candidato"] == ""


def test_sources_generati_dalle_date():
    preprocess = _load_preprocess()

    assert 1990 in preprocess.SOURCES
    url, election_date, is_zip = preprocess.SOURCES[1989][0]
    assert election_date == "1989-01-01"
    assert url.endswith("/comunali-19890101.zip")
    assert is_zip is True


def test_2024_esclude_la_tornata_a_formato_sezione():
    preprocess = _load_preprocess()
    dates = [d for _url, d, _zip in preprocess.SOURCES[2024]]

    assert dates == ["2024-06-09", "2024-07-28"]


def test_header_2022_text_mappa_seggi_e_leader():
    preprocess = _load_preprocess()
    header = [
        "REGIONE", "PROVINCIA", "COMUNE", "ELETTORITOT", "ELETTORIMASCHI",
        "VOTANTITOT", "VOTANTIMASCHI", "SKBIANCHE", "DESCRLISTA", "VOTILISTA",
        "SEGGI", "COGNOME", "NOME", "CODTIPOELETTO", "VOTICANDLEADER",
    ]

    names, _ = preprocess.normalize_columns(header)

    assert "seggi_lista" in names
    assert "voti_candidato" in names


def test_header_join_1970_1980():
    preprocess = _load_preprocess()

    names_1970, _ = preprocess.normalize_columns(
        ["REGIONE", "PROVINCIA", "COMUNE", "LISTA", "VOTI", "SEGGI"]
    )
    names_1980, _ = preprocess.normalize_columns(
        ["DataElezione", "Regione", "Provincia", "ComuneSut", "ElettoriTotali"]
    )

    assert {"lista", "voti_lista", "seggi_lista"} <= set(names_1970)
    assert {"regione", "provincia", "comune", "elettori"} <= set(names_1980)


