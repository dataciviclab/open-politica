"""Contract camera_leggi — ponte Normattiva/atto per costituzionali."""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "camera-leggi" / "dataset.yml"
CLEAN_SQL = REPO_ROOT / "datasets" / "camera-leggi" / "sql" / "clean.sql"


def test_config_ha_source_costituzionali_e_mode_all():
    """contract: source SPARQL LC* + read.mode=all per union multi-sorgente."""
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
    # multi-source → union, non latest
    assert cfg["clean"]["read"]["mode"] == "all"
    # PK = URI, non id_legge
    assert cfg["clean"]["validate"]["primary_key"] == ["legge_camera"]


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
    # dedup PK = URI legge_camera
    assert "PARTITION BY normalize_string(leg)" in text
    assert "PARTITION BY" in text and "id_legge" not in text.split("ROW_NUMBER")[1].split("FROM")[0]


def test_dedup_preserva_lc_stesso_id_legge():
    """policy: LC con stesso id_legge (anno diverso) restano righe distinte."""
    con = duckdb.connect()
    # fixture: due costituzionali, stesso n finale, anni diversi
    rows = """
    SELECT * FROM (VALUES
      ('http://dati.camera.it/ocd/legge.rdf/LC2013_1', 'LC2013_1', 1, 'Costituzionale',
       DATE '2013-02-07', 'urn:nir:stato:legge.costituzionale:2013-02-07;1', 'ac16_5148'),
      ('http://dati.camera.it/ocd/legge.rdf/LC2022_1', 'LC2022_1', 1, 'Costituzionale',
       DATE '2022-02-11', 'urn:nir:stato:legge.costituzionale:2022;1', 'ac18_3156')
    ) AS t(legge_camera, leg, id_legge, tipo, data_promulgazione, urn_normattiva, atto_camera)
    """
    # stessa logica di clean.sql: PARTITION BY URI
    out = con.execute(f"""
    WITH raw AS ({rows}),
    ranked AS (
      SELECT *,
        ROW_NUMBER() OVER (
          PARTITION BY legge_camera
          ORDER BY CASE WHEN UPPER(tipo)='COSTITUZIONALE' THEN 0 ELSE 1 END,
                   data_promulgazione DESC
        ) AS _rn
      FROM raw
    )
    SELECT legge_camera, id_legge FROM ranked WHERE _rn = 1 ORDER BY legge_camera
    """).fetchall()
    assert len(out) == 2
    assert {r[0] for r in out} == {
        "http://dati.camera.it/ocd/legge.rdf/LC2013_1",
        "http://dati.camera.it/ocd/legge.rdf/LC2022_1",
    }


def test_dedup_id_legge_sbagliato_collassa():
    """policy: se si partiziona su id_legge, le LC collassano (bug del fix)."""
    con = duckdb.connect()
    rows = """
    SELECT * FROM (VALUES
      ('http://dati.camera.it/ocd/legge.rdf/LC2013_1', 1, 'Costituzionale', DATE '2013-02-07'),
      ('http://dati.camera.it/ocd/legge.rdf/LC2022_1', 1, 'Costituzionale', DATE '2022-02-11')
    ) AS t(legge_camera, id_legge, tipo, data_promulgazione)
    """
    out = con.execute(f"""
    WITH raw AS ({rows}),
    ranked AS (
      SELECT *, ROW_NUMBER() OVER (
        PARTITION BY id_legge
        ORDER BY data_promulgazione DESC
      ) AS _rn
      FROM raw
    )
    SELECT COUNT(*) FROM ranked WHERE _rn = 1
    """).fetchone()[0]
    assert out == 1, "id_legge non è PK: deve collassare (comportamento del bug)"
