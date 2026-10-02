"""Contract camera_leggi — ponte Normattiva/atto per costituzionali."""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "camera-leggi" / "dataset.yml"
CLEAN_SQL = REPO_ROOT / "datasets" / "camera-leggi" / "sql" / "clean.sql"


def test_config_ha_source_costituzionali():
    """contract: source SPARQL LC* oltre alle legislature 13-19."""
    cfg = yaml.safe_load(DATASET.read_text("utf-8"))
    names = [s["name"] for s in cfg["raw"]["sources"]]
    assert "camera_leggi_sparql" in names
    assert "camera_leggi_costituzionali_sparql" in names
    cost = next(s for s in cfg["raw"]["sources"] if s["name"].endswith("costituzionali_sparql"))
    q = cost["args"]["query"]
    assert "legge.rdf/LC" in q
    assert "lavoriPreparatori" in q
    assert "rif_natura" in q
    # non deve filtrare solo su repubblica_{year}
    assert "repubblica_{year}" not in q


def test_clean_esporta_chiavi_ponte():
    """contract: clean espone atto, natura e chiavi URN per join."""
    text = CLEAN_SQL.read_text("utf-8")
    for col in (
        "atto_camera",
        "natura_atto",
        "legge_key_full",
        "legge_key_year",
        "urn_normattiva",
        "ddl_numero",
    ):
        assert col in text, col
    assert "legge.costituzionale" not in text or "urn_normattiva" in text
    # legge_key_year accetta forma year-only (2022;1)
    assert "legge_key_year" in text
