"""Contratto compose atti (dimensione conformata del Parlamento).

marker: regression — protegge la chiave `atto_id` (in particolare
`camera:{legislatura}:{id_ddl}`: senza legislatura 34.313 atti Camera
collassano su 7.614), la clausura dell'enum `tipo` e il grain per atto.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

pytestmark = pytest.mark.regression

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTI_YML = REPO_ROOT / "compose" / "atti" / "dataset.yml"
ATTI_CLEAN = REPO_ROOT / "compose" / "atti" / "sql" / "clean.sql"
ATTI_MART = REPO_ROOT / "out" / "data" / "mart" / "atti" / "2026" / "mart_atti.parquet"
ATTI_MART_DL = REPO_ROOT / "out" / "data" / "mart" / "atti" / "2026" / "mart_dl.parquet"

LEGISLATURE = [13, 14, 15, 16, 17, 18, 19]


def _load_yml(path: Path) -> dict:
    return yaml.safe_load(path.read_text("utf-8"))


def _code(path: Path) -> str:
    """SQL senza commenti: i commenti spiegano i fix, non sono il contratto."""
    return "\n".join(
        line for line in path.read_text("utf-8").splitlines()
        if not line.strip().startswith("--")
    )


def _flat(path: Path) -> str:
    """SQL senza commenti e con whitespace collassato (per assert robusti)."""
    return " ".join(_code(path).split())


def test_atti_support_external_multi_legislatura():
    cfg = _load_yml(ATTI_YML)
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    for name in ("senato_ddl", "camera_ddl", "camera_leggi"):
        assert name in support, f"support mancante: {name}"
        assert support[name]["type"] == "external"
        assert "storage.googleapis.com" in support[name]["uri"]
        # Pattern C: path per legislatura, non anno calendario
        assert support[name]["years"] == LEGISLATURE


def test_atti_mart_dichiarato_con_pk():
    cfg = _load_yml(ATTI_YML)
    tables = [t["name"] for t in cfg["mart"]["tables"]]
    assert "mart_atti" in tables
    rules = cfg["mart"]["validate"]["table_rules"]["mart_atti"]
    assert rules["primary_key"] == ["atto_id"]


def test_atti_chiave_camera_include_legislatura():
    """Il collasso 34.313 → 7.614 nasce esattamente dalla chiave senza leg."""
    code = _flat(ATTI_CLEAN)
    assert "'camera:' || CAST(c.legislatura AS VARCHAR)" in code
    # la chiave Camera non deve mai essere solo id_ddl
    assert "'camera:' || CAST(c.id_ddl AS VARCHAR) AS atto_id" not in code
    assert "'senato:' || CAST(id_ddl AS VARCHAR) AS atto_id" in code


def test_atti_tipo_enum_chiuso():
    code = _code(ATTI_CLEAN)
    assert "ELSE 'ALTRO'" in code
    assert "natura_raw" in code  # il valore originale resta tracciabile


def test_atti_mart_pk_no_dup():
    if not ATTI_MART.exists():
        pytest.skip("mart atti non presente — esegui toolkit run")
    con = duckdb.connect()
    dups = con.execute(
        f"""
        SELECT COUNT(*) FROM (
          SELECT atto_id FROM read_parquet('{ATTI_MART}')
          GROUP BY 1 HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    assert dups == 0, f"atto_id duplicati: {dups}"


def test_atti_mart_camera_non_collassa():
    """Invariante del fix: una riga per (legislatura, numero_atto) Camera."""
    if not ATTI_MART.exists():
        pytest.skip("mart atti non presente")
    con = duckdb.connect()
    righe, chiavi = con.execute(
        f"""
        SELECT COUNT(*), COUNT(DISTINCT (legislatura, numero_atto))
        FROM read_parquet('{ATTI_MART}') WHERE ramo = 'camera'
        """
    ).fetchone()
    assert righe == chiavi, f"Camera: {righe} righe ma {chiavi} chiavi (leg, numero)"
    assert righe >= 34_000, f"Camera sotto soglia: {righe} (attesi ~34.300)"


def test_atti_mart_rowcount_e_rami():
    if not ATTI_MART.exists():
        pytest.skip("mart atti non presente")
    con = duckdb.connect()
    rami = dict(
        con.execute(
            f"SELECT ramo, COUNT(*) FROM read_parquet('{ATTI_MART}') GROUP BY 1"
        ).fetchall()
    )
    assert set(rami) == {"senato", "camera"}
    assert sum(rami.values()) >= 68_000, f"pochi atti: {rami}"


def test_atti_mart_urn_su_entrambi_i_rami():
    if not ATTI_MART.exists():
        pytest.skip("mart atti non presente")
    con = duckdb.connect()
    for ramo, soglia in (("senato", 2_000), ("camera", 2_000)):
        n = con.execute(
            f"""
            SELECT COUNT(*) FROM read_parquet('{ATTI_MART}')
            WHERE ramo = '{ramo}' AND urn_normattiva IS NOT NULL
            """
        ).fetchone()[0]
        assert n >= soglia, f"{ramo}: solo {n} atti con URN"


def test_atti_mart_dl_identity():
    """DL: numero+anno valorizzati insieme, e più atti possono condividere un DL."""
    if not ATTI_MART.exists():
        pytest.skip("mart atti non presente")
    con = duckdb.connect()
    incoerenti = con.execute(
        f"""
        SELECT COUNT(*) FROM read_parquet('{ATTI_MART}')
        WHERE (dl_numero IS NULL) <> (dl_anno IS NULL)
        """
    ).fetchone()[0]
    assert incoerenti == 0, f"{incoerenti} atti con dl_numero/dl_anno incoerenti"
    n_dl = con.execute(
        f"""
        SELECT COUNT(DISTINCT (dl_numero, dl_anno)) FROM read_parquet('{ATTI_MART}')
        WHERE dl_numero IS NOT NULL
        """
    ).fetchone()[0]
    assert n_dl >= 800, f"pochi DL distinti: {n_dl}"


def test_mart_dl_giorni_dalla_data_del_decreto():
    """`giorni_conversione` parte da `data_dl`, non dalla prima lettura.

    Per 458 DL su 894 la prima data dell'iter è successiva alla data del
    decreto (+16,9 giorni medi): partire dall'iter sottostimava i tempi
    (DL 200/2025: 3 giorni invece di 58). Review #113.
    """
    if not ATTI_MART_DL.exists():
        pytest.skip("mart_dl non presente — esegui toolkit run")
    con = duckdb.connect()
    incoerenti = con.execute(
        f"""
        SELECT COUNT(*) FROM read_parquet('{ATTI_MART_DL}')
        WHERE data_conversione IS NOT NULL
          AND data_dl IS NOT NULL
          AND giorni_conversione <> date_diff('day', data_dl, data_conversione)
        """
    ).fetchone()[0]
    assert incoerenti == 0, f"{incoerenti} DL con giorni non calcolati da data_dl"
    negativi = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{ATTI_MART_DL}') WHERE giorni_conversione < 0"
    ).fetchone()[0]
    assert negativi == 0, f"{negativi} DL con giorni negativi (data_dl dopo la conversione)"


def test_mart_dl_giorni_del_caso_200_2025():
    """Caso che aveva smascherato la base sbagliata: 58 giorni, non 3."""
    if not ATTI_MART_DL.exists():
        pytest.skip("mart_dl non presente")
    con = duckdb.connect()
    row = con.execute(
        f"""
        SELECT giorni_conversione FROM read_parquet('{ATTI_MART_DL}')
        WHERE dl_numero = 200 AND dl_anno = 2025
        """
    ).fetchone()
    if row is None:
        pytest.skip("DL 200/2025 non presente nella fonte")
    assert 55 <= row[0] <= 61, f"DL 200/2025: {row[0]} giorni (atteso ~58 dalla data del decreto)"
