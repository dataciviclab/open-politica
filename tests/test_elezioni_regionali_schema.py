"""Contract elezioni_regionali — schema storico unificato.

pure_unit: le tornate 1970-1990 non hanno candidato/circoscrizione, il 2008 usa
``VOTICANDIDLEADER`` e il 2001-06-24 usa nomi abbreviati (REG/CIRC/PROV).
``ensure_canonical`` e ``normalize_columns`` devono produrre le 12 colonne attese
da clean.sql, altrimenti il clean fallisce per colonna mancante.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "elezioni-regionali"


def _load_preprocess():
    spec = importlib.util.spec_from_file_location(
        "elezioni_regionali_preprocess", DATASET / "preprocess.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ensure_canonical_riempie_le_colonne_mancanti():
    preprocess = _load_preprocess()
    records = [{"data_elezione": "1970-06-07", "regione": "LIGURIA", "lista": "MSI"}]

    preprocess.ensure_canonical(records)

    assert set(preprocess.CANONICAL_COLS) <= set(records[0])
    assert records[0]["candidato"] == ""
    assert records[0]["circoscrizione"] == ""


def test_header_2008_mappa_voti_candidato():
    preprocess = _load_preprocess()
    header = [
        "REGIONE", "PROVINCIA", "COMUNE", "ELETTORI", "ELETTORI_M",
        "VOTANTI", "VOTANTI_M", "SCHEDE_BIANCHE", "COGNOME", "NOME",
        "VOTICANDIDLEADER", "LISTA", "VOTILISTA",
    ]

    names, _ = preprocess.normalize_columns(header)

    assert "voti_candidato" in names
    assert "voti_lista" in names
    assert "candidato" not in names  # cognome/nome restano separati qui


def test_header_2001_abbreviato_mappa_i_territori():
    preprocess = _load_preprocess()
    header = ["REG", "CIRC", "PROV", "COMUNE", "DESCRLISTA", "VOTILISTA"]

    names, _ = preprocess.normalize_columns(header)

    assert {"regione", "circoscrizione", "provincia", "comune", "lista", "voti_lista"} <= set(names)
