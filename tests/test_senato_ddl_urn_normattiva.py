"""Contract URN_normattiva di senato-ddl.

policy: placeholder 2100-01-01 → NULL; costituzionale + data reale →
namespace legge.costituzionale; dati misti (placeholder + reale) → data reale.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEAN_SQL = REPO_ROOT / "datasets" / "senato-ddl" / "sql" / "clean.sql"


def _urn_from_agg(con: duckdb.DuckDBPyConnection, rows_sql: str) -> list[tuple]:
    """Esegue lo stesso pattern di clean.sql: agg GROUP BY + outer URN CASE."""
    sql = f"""
    WITH raw_input AS (
        {rows_sql}
    ),
    agg AS (
        SELECT
            ddl,
            MAX(idDdl) AS idDdl,
            MAX(natura) AS natura,
            MAX(CAST(numeroLegge AS BIGINT)) AS numero_legge,
            MAX(CASE
                WHEN TRY_CAST(dataLegge AS DATE) IS NOT NULL
                 AND TRY_CAST(dataLegge AS DATE) <> DATE '2100-01-01'
                    THEN TRY_CAST(dataLegge AS DATE)
            END) AS data_legge
        FROM raw_input
        WHERE ddl LIKE '%/ddl/%'
        GROUP BY ddl
    )
    SELECT ddl, natura, data_legge,
        CASE
            WHEN numero_legge IS NOT NULL
             AND data_legge IS NOT NULL
             AND CAST(data_legge AS DATE) <> DATE '2100-01-01'
                THEN CASE
                    WHEN LOWER(COALESCE(natura, '')) = 'costituzionale'
                        THEN 'urn:nir:stato:legge.costituzionale:'
                             || CAST(CAST(data_legge AS DATE) AS VARCHAR)
                             || ';' || CAST(numero_legge AS VARCHAR)
                    ELSE 'urn:nir:stato:legge:'
                         || CAST(CAST(data_legge AS DATE) AS VARCHAR)
                         || ';' || CAST(numero_legge AS VARCHAR)
                END
            ELSE NULL
        END AS urn_normattiva
    FROM agg
    ORDER BY ddl
    """
    return con.execute(sql).fetchall()


def test_clean_sql_esiste():
    """contract: clean.sql presente e contiene le regole URN."""
    text = CLEAN_SQL.read_text("utf-8")
    assert "urn_normattiva" in text
    assert "legge.costituzionale" in text
    assert "2100-01-01" in text
    # il placeholder non deve entrare in MAX(data_legge)
    assert "MAX(TRY_CAST(dataLegge AS DATE))" not in text
    assert "LOWER(COALESCE(natura" in text


def test_urn_placeholder_only_null():
    """policy: solo placeholder → NULL, non una stringa 2100."""
    con = duckdb.connect()
    rows = """
    SELECT '/ddl/1' AS ddl, 1 AS idDdl, 'costituzionale' AS natura,
           1 AS numeroLegge, DATE '2100-01-01' AS dataLegge
    """
    out = _urn_from_agg(con, rows)
    assert len(out) == 1
    assert out[0][3] is None


def test_urn_costituzionale_namespace():
    """policy: costituzionale + data reale → legge.costituzionale."""
    con = duckdb.connect()
    rows = """
    SELECT '/ddl/2' AS ddl, 2 AS idDdl, 'costituzionale' AS natura,
           1 AS numeroLegge, DATE '2026-05-18' AS dataLegge
    """
    out = _urn_from_agg(con, rows)
    assert out[0][3] == "urn:nir:stato:legge.costituzionale:2026-05-18;1"


def test_urn_ordinaria_namespace():
    """policy: atto ordinario + data reale → namespace legge."""
    con = duckdb.connect()
    rows = """
    SELECT '/ddl/3' AS ddl, 3 AS idDdl, 'ordinaria' AS natura,
           100 AS numeroLegge, DATE '2020-01-01' AS dataLegge
    """
    out = _urn_from_agg(con, rows)
    assert out[0][3] == "urn:nir:stato:legge:2020-01-01;100"


def test_urn_mixed_placeholder_and_real_keeps_real():
    """policy: dati misti (placeholder + reale) → data reale, non NULL."""
    con = duckdb.connect()
    rows = """
    SELECT '/ddl/4' AS ddl, 4 AS idDdl, 'costituzionale' AS natura,
           2 AS numeroLegge, DATE '2100-01-01' AS dataLegge
    UNION ALL
    SELECT '/ddl/4', 4, 'costituzionale', 2, DATE '2026-01-26'
    """
    out = _urn_from_agg(con, rows)
    assert out[0][3] == "urn:nir:stato:legge.costituzionale:2026-01-26;2"


def test_urn_natura_case_insensitive():
    """policy: natura con casing diverso non cade nel branch ordinario."""
    con = duckdb.connect()
    rows = """
    SELECT '/ddl/5' AS ddl, 5 AS idDdl, 'Costituzionale' AS natura,
           1 AS numeroLegge, DATE '2007-10-02' AS dataLegge
    """
    out = _urn_from_agg(con, rows)
    assert out[0][3] == "urn:nir:stato:legge.costituzionale:2007-10-02;1"
