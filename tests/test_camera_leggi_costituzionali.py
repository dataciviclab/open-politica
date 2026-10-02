"""Contract camera_leggi — ponte Normattiva/atto + partizione multi-anno.

policy: una legge (URI) deve comparire in UN solo file year del clean.
La source LC* è year-less e, senza filtro {year}, viene riscritta a ogni
run 13–19 → nel union del consumatore ogni LC moltiplica per 7.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "camera-leggi" / "dataset.yml"
CLEAN_SQL = REPO_ROOT / "datasets" / "camera-leggi" / "sql" / "clean.sql"

# fixture: stessa forma del clean dopo raw_norm/raw_dedup
_FIXTURE = """
CREATE TABLE raw_dedup AS
SELECT * FROM (VALUES
  ('http://dati.camera.it/ocd/legge.rdf/LC2001_3', 3, 'Costituzionale',
   DATE '2001-10-18', 13,
   'urn:nir:stato:legge.costituzionale:2001-10-18;3', 'ac13_6376'),
  ('http://dati.camera.it/ocd/legge.rdf/LC1947_1', 1, 'Costituzionale',
   DATE '1947-02-21', NULL,
   'urn:nir:stato:legge.costituzionale:1947-02-21;1', 'accostituente_21bis'),
  ('http://dati.camera.it/ocd/legge.rdf/L2019_100', 100, 'Ordinaria',
   DATE '2019-06-01', 19, NULL, NULL)
) AS t(legge_camera, id_legge, tipo, data_promulgazione, legislatura,
        urn_normattiva, atto_camera);
"""


def _legs_for_year(con: duckdb.DuckDBPyConnection, year: int) -> set[str]:
    """Stessa regola WHERE di clean.sql con {year} sostituito."""
    rows = con.execute(
        f"""
        SELECT legge_camera FROM raw_dedup
        WHERE legislatura = {year}
           OR (
                UPPER(COALESCE(tipo, '')) = 'COSTITUZIONALE'
            AND {year} = 19
            AND (legislatura IS NULL OR legislatura < 13 OR legislatura > 19)
           )
        """
    ).fetchall()
    return {r[0] for r in rows}


def test_config_ha_source_costituzionali_e_mode_all():
    """contract: source SPARQL LC* + read.mode=all + PK URI."""
    cfg = yaml.safe_load(DATASET.read_text("utf-8"))
    names = [s["name"] for s in cfg["raw"]["sources"]]
    assert "camera_leggi_sparql" in names
    assert "camera_leggi_costituzionali_sparql" in names
    cost = next(s for s in cfg["raw"]["sources"] if s["name"].endswith("costituzionali_sparql"))
    q = cost["args"]["query"]
    assert "legge.rdf/LC" in q
    assert "repubblica_{year}" not in q
    assert cfg["clean"]["read"]["mode"] == "all"
    assert cfg["clean"]["validate"]["primary_key"] == ["legge_camera"]


def test_clean_partiziona_per_anno():
    """policy: il clean usa {year} — una legge in un solo file year."""
    text = CLEAN_SQL.read_text("utf-8")
    assert "{year}" in text
    assert "legislatura = {year}" in text
    assert "{year} = 19" in text


def test_anni_distinti_non_duplicano_lc():
    """policy: LC2001 solo in leg 13; LC1947 orfana solo in leg 19; ordinaria solo nella sua leg."""
    con = duckdb.connect()
    con.execute(_FIXTURE)
    y13 = _legs_for_year(con, 13)
    y19 = _legs_for_year(con, 19)

    assert "http://dati.camera.it/ocd/legge.rdf/LC2001_3" in y13
    assert "http://dati.camera.it/ocd/legge.rdf/LC2001_3" not in y19

    assert "http://dati.camera.it/ocd/legge.rdf/LC1947_1" in y19
    assert "http://dati.camera.it/ocd/legge.rdf/LC1947_1" not in y13

    assert "http://dati.camera.it/ocd/legge.rdf/L2019_100" in y19
    assert "http://dati.camera.it/ocd/legge.rdf/L2019_100" not in y13

    assert not (y13 & y19), f"URI in entrambi gli anni: {y13 & y19}"


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
    assert "PARTITION BY normalize_string(leg)" in text
    assert "PARTITION BY id_legge" not in text


def test_dedup_preserva_lc_stesso_id_legge():
    """policy: LC con stesso id_legge (anno diverso) restano righe distinte."""
    con = duckdb.connect()
    out = con.execute("""
    WITH raw AS (
      SELECT * FROM (VALUES
        ('http://dati.camera.it/ocd/legge.rdf/LC2013_1', 1, 'Costituzionale', DATE '2013-02-07'),
        ('http://dati.camera.it/ocd/legge.rdf/LC2022_1', 1, 'Costituzionale', DATE '2022-02-11')
      ) AS t(legge_camera, id_legge, tipo, data_promulgazione)
    ),
    ranked AS (
      SELECT *, ROW_NUMBER() OVER (
        PARTITION BY legge_camera
        ORDER BY CASE WHEN UPPER(tipo)='COSTITUZIONALE' THEN 0 ELSE 1 END,
                 data_promulgazione DESC
      ) AS _rn
      FROM raw
    )
    SELECT legge_camera FROM ranked WHERE _rn = 1 ORDER BY legge_camera
    """).fetchall()
    assert len(out) == 2


def test_out_clean_local_multi_anno_univoco():
    """policy: clean locali multi-anno — ogni URI in un solo file year."""
    clean_dir = REPO_ROOT / "out" / "data" / "clean" / "camera_leggi"
    if not clean_dir.exists():
        return
    files = sorted(clean_dir.glob("*/camera_leggi_*_clean.parquet"))
    if len(files) < 2:
        return
    con = duckdb.connect()
    parts = [
        f"SELECT legge_camera, '{p.parent.name}' AS year FROM read_parquet('{p}')"
        for p in files
    ]
    rows = con.execute(
        f"""
        SELECT legge_camera, COUNT(DISTINCT year) AS n_years
        FROM ({' UNION ALL '.join(parts)})
        GROUP BY 1
        HAVING n_years > 1
        """
    ).fetchall()
    assert rows == [], f"URI presenti in più file year: {rows[:5]}"
