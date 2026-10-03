"""Regression compose ponti-parlamento + voti-ddl-dettaglio (PR #60).

marker: regression — protegge join ddl_id/atto_id, PK mart, row-count,
e aggregatori deterministici su senato_ddl multi-fase.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PONTI_YML = REPO_ROOT / "compose" / "ponti-parlamento" / "dataset.yml"
VOTI_YML = REPO_ROOT / "compose" / "voti-ddl-dettaglio" / "dataset.yml"
VOTI_CLEAN = REPO_ROOT / "compose" / "voti-ddl-dettaglio" / "sql" / "clean.sql"
PONTI_CLEAN = REPO_ROOT / "compose" / "ponti-parlamento" / "sql" / "clean.sql"

PONTI_MART = (
    REPO_ROOT
    / "out"
    / "data"
    / "mart"
    / "ponti_parlamento"
    / "2026"
    / "mart_ponti_sintesi.parquet"
)
VOTI_MART = (
    REPO_ROOT
    / "out"
    / "data"
    / "mart"
    / "voti_ddl_dettaglio"
    / "2026"
    / "mart_voti_ddl.parquet"
)
VOTI_SINTESI = (
    REPO_ROOT
    / "out"
    / "data"
    / "mart"
    / "voti_ddl_dettaglio"
    / "2026"
    / "mart_voti_ddl_sintesi.parquet"
)


def _load_yml(path: Path) -> dict:
    return yaml.safe_load(path.read_text("utf-8"))


def test_ponti_support_external_gcs():
    cfg = _load_yml(PONTI_YML)
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    for name in (
        "senato_ddl",
        "senato_votazioni",
        "senato_relatori",
        "camera_firmatari",
        "camera_atti_dibattito",
        "camera_ddl",
    ):
        assert name in support, f"support mancante: {name}"
        assert support[name]["type"] == "external", f"{name} non external"
        assert "storage.googleapis.com" in support[name]["uri"]
    # multi-leg: votazioni_oggetto copre 13–19 → ddl join deve usare le stesse legislature
    assert support["senato_ddl"]["years"] == [13, 14, 15, 16, 17, 18, 19]


def test_voti_support_external_gcs():
    cfg = _load_yml(VOTI_YML)
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    for name in ("senato_votazioni", "senato_ddl", "senato_anagrafica"):
        assert name in support
        assert support[name]["type"] == "external"
        assert "storage.googleapis.com" in support[name]["uri"]


def test_voti_clean_no_any_value():
    """ANY_VALUE su senato_ddl multi-fase è non deterministico (review #60)."""
    sql = VOTI_CLEAN.read_text("utf-8")
    # solo codice, non i commenti che spiegano il fix
    code = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )
    assert "ANY_VALUE" not in code
    assert "arg_max(" in code
    assert "{support.senato_ddl.clean}" in code
    assert "GROUP BY id_ddl" in code


def test_ponti_clean_uses_support_clean_placeholders():
    sql = PONTI_CLEAN.read_text("utf-8")
    assert "{support.senato_relatori.clean}" in sql
    assert "{support.camera_firmatari.clean}" in sql
    # no quote sul placeholder multi-anno (lista URL SQL)
    assert "read_parquet('{support." not in sql


def test_ponti_mart_kpi_min_rows():
    if not PONTI_MART.exists():
        pytest.skip("mart ponti_parlamento non presente — esegui toolkit run")
    con = duckdb.connect()
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{PONTI_MART}')").fetchone()[0]
    assert n >= 15, f"mart_ponti_sintesi troppe poche righe: {n}"
    cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{PONTI_MART}')").fetchall()}
    assert {"ponte", "metrica", "valore", "fonte"} <= cols


def test_ponti_ddl_join_senato_ddl_threshold():
    """ddl_in_senato_ddl multi-leg: soglia minima (review; 828 su dati attuali)."""
    if not PONTI_MART.exists():
        pytest.skip("mart ponti_parlamento non presente")
    con = duckdb.connect()
    row = con.execute(
        f"""
        SELECT valore FROM read_parquet('{PONTI_MART}')
        WHERE metrica = 'ddl_in_senato_ddl'
        """
    ).fetchone()
    assert row is not None, "metrica ddl_in_senato_ddl assente"
    assert row[0] >= 700, f"ddl_in_senato_ddl troppo basso: {row[0]} (atteso multi-leg)"


def test_voti_ddl_pk_no_dup():
    if not VOTI_MART.exists():
        pytest.skip("mart voti_ddl_dettaglio non presente")
    con = duckdb.connect()
    dups = con.execute(
        f"""
        SELECT COUNT(*) FROM (
          SELECT votazione_id, senatore_id
          FROM read_parquet('{VOTI_MART}')
          GROUP BY 1, 2 HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    assert dups == 0, f"PK duplicate in mart_voti_ddl: {dups}"


def test_voti_ddl_rowcount_min():
    if not VOTI_MART.exists():
        pytest.skip("mart voti_ddl_dettaglio non presente")
    con = duckdb.connect()
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{VOTI_MART}')").fetchone()[0]
    assert n >= 100_000, f"mart_voti_ddl sotto soglia: {n}"


def test_voti_ddl_sintesi_arithmetic():
    if not VOTI_SINTESI.exists():
        pytest.skip("mart_voti_ddl_sintesi non presente")
    con = duckdb.connect()
    bad = con.execute(
        f"""
        SELECT COUNT(*) FROM read_parquet('{VOTI_SINTESI}')
        WHERE n_fav + n_contr + n_ast <> n_voti
        """
    ).fetchone()[0]
    assert bad == 0, f"sintesi con F+C+A != n_voti: {bad} DDL"
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{VOTI_SINTESI}')").fetchone()[0]
    assert n >= 50, f"sintesi troppe poche righe: {n}"
