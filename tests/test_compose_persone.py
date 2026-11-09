"""Contratto compose persone (dimensione persona × legislatura × ramo).

marker: regression — protegge la chiave `persona_key` (persona_id Camera o
`sen:{senatore_id}`), il ponte Camera↔Senato, il perimetro Repubblica 13-19
e la separazione dei namespace `persona_id` (Camera numerico vs Senato `pNNN`).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

pytestmark = pytest.mark.regression

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONE_YML = REPO_ROOT / "compose" / "persone" / "dataset.yml"
PERSONE_CLEAN = REPO_ROOT / "compose" / "persone" / "sql" / "clean.sql"
PERSONE_MART = (
    REPO_ROOT / "out" / "data" / "mart" / "persone" / "2026" / "mart_persone.parquet"
)


def _yml(path: Path) -> dict:
    return yaml.safe_load(path.read_text("utf-8"))


def _flat(path: Path) -> str:
    code = "\n".join(
        line for line in path.read_text("utf-8").splitlines()
        if not line.strip().startswith("--")
    )
    return " ".join(code.split())


@pytest.fixture(scope="module")
def con():
    if not PERSONE_MART.exists():
        pytest.skip("mart persone non presente — esegui toolkit run")
    db = duckdb.connect()
    db.execute(f"create view per as select * from read_parquet('{PERSONE_MART}')")
    yield db
    db.close()


def test_persone_support():
    cfg = _yml(PERSONE_YML)
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    assert {"senato_anagrafica", "senato_dibattito", "camera_deputati",
            "camera_firmatari", "ponte_persona"} <= set(support)
    # il dibattito è cross-repo (senato-akn) e serve per i 110 senatori
    # che l'anagrafica non ha
    assert support["senato_dibattito"]["repo"] == "senato-akn"


def test_persone_pk():
    cfg = _yml(PERSONE_YML)
    rules = cfg["mart"]["validate"]["table_rules"]["mart_persone"]
    assert rules["primary_key"] == ["persona_key", "ramo", "sistema", "legislatura"]


def test_persone_non_usa_persona_id_del_senato():
    """`senato_dibattito.persona_id` è `pNNN`: non deve finire in persona_key."""
    code = _flat(PERSONE_CLEAN)
    assert "sen:' || CAST(d.senatore_id" in code
    assert "p1103" not in code  # nessun valore hardcoded


def test_persone_perimetro_repubblica():
    code = _flat(PERSONE_CLEAN)
    assert "LIKE 'repubblica_%'" in code
    assert "BETWEEN 13 AND 19" in code


def test_persone_pk_no_dup(con):
    dup = con.execute("""
        SELECT COUNT(*) FROM (
          SELECT persona_key, ramo, sistema, legislatura FROM per
          GROUP BY 1,2,3,4 HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert dup == 0, f"chiavi duplicate: {dup}"


def test_persone_due_rami(con):
    rami = dict(con.execute("SELECT ramo, COUNT(*) FROM per GROUP BY 1").fetchall())
    assert rami.get("camera", 0) >= 4_000, f"camera: {rami.get('camera')}"
    assert rami.get("senato", 0) >= 2_200, f"senato: {rami.get('senato')}"


def test_persone_solo_repubblica_13_19(con):
    bad = con.execute("""
        SELECT COUNT(*) FROM per
        WHERE sistema <> 'repubblica' OR legislatura NOT BETWEEN 13 AND 19
    """).fetchone()[0]
    assert bad == 0, f"{bad} righe fuori perimetro"


def test_persone_persona_id_numerico(con):
    """Il namespace Camera è numerico: mai `pNNN` (Senato)."""
    bad = con.execute("""
        SELECT COUNT(*) FROM per
        WHERE persona_id IS NOT NULL AND NOT regexp_matches(CAST(persona_id AS VARCHAR), '^[0-9]+$')
    """).fetchone()[0]
    assert bad == 0, f"{bad} persona_id non numerici"


def test_persone_ponte_unisce_i_rami(con):
    """Chi ha il ponte compare con la stessa chiave su ramo camera e senato."""
    n = con.execute("""
        SELECT COUNT(*) FROM (
          SELECT persona_key FROM per GROUP BY 1 HAVING COUNT(DISTINCT ramo) > 1
        )
    """).fetchone()[0]
    assert n >= 100, f"solo {n} persone condivise tra i rami"
    # e ogni chiave condivisa ha ponte=true su entrambe le righe
    bad = con.execute("""
        SELECT COUNT(*) FROM per
        WHERE persona_key IN (
            SELECT persona_key FROM per GROUP BY 1 HAVING COUNT(DISTINCT ramo) > 1
        ) AND NOT ponte
    """).fetchone()[0]
    assert bad == 0, f"{bad} righe di persone condivise senza ponte"


def test_persone_nomi_coperti(con):
    """Almeno l'80% delle righe ha un nome mostrabile.

    Il resto sono senatori Leg13-16 senza nome in anagrafica e senza ponte
    Camera (fonte: 440 righe al 2026-11).
    """
    tot, senza = con.execute("""
        SELECT COUNT(*), COUNT(*) FILTER (WHERE nome_completo IS NULL OR nome_completo = '')
        FROM per
    """).fetchone()
    assert senza / tot < 0.20, f"{senza}/{tot} senza nome"


def test_persone_senatori_recuperati_da_camera(con):
    """Il ponte completa i nomi mancanti dell'anagrafica Senato."""
    n = con.execute("""
        SELECT COUNT(*) FROM per
        WHERE ramo = 'senato' AND ponte AND nome IS NOT NULL
    """).fetchone()[0]
    assert n >= 150, f"solo {n} senatori con nome recuperato dal ponte"


PROFILO_MART = (
    REPO_ROOT / "out" / "data" / "mart" / "persone" / "2026" / "mart_profilo.parquet"
)


@pytest.fixture(scope="module")
def profilo():
    if not PROFILO_MART.exists():
        pytest.skip("mart_profilo non presente — esegui toolkit run")
    db = duckdb.connect()
    db.execute(f"create view prof as select * from read_parquet('{PROFILO_MART}')")
    yield db
    db.close()


def test_profilo_schema_e_pk(profilo):
    """Stesso schema del vecchio `profilo_politico/mart_profilo`."""
    cols = {r[0] for r in profilo.execute("DESCRIBE SELECT * FROM prof").fetchall()}
    assert {
        "ramo", "id_parlamentare", "persona_id", "nome", "cognome",
        "n_voti", "pct_coerente", "pct_col_gruppo", "in_governo",
        "n_commissioni_attuali", "commissioni_attuali",
    } <= cols
    dup = profilo.execute("""
        SELECT COUNT(*) FROM (
          SELECT ramo, id_parlamentare FROM prof GROUP BY 1,2 HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert dup == 0, f"chiavi duplicate: {dup}"


def test_profilo_righe_e_range(profilo):
    n, nulli, fuori = profilo.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE id_parlamentare IS NULL),
               COUNT(*) FILTER (WHERE pct_col_gruppo NOT BETWEEN 0 AND 100)
        FROM prof
    """).fetchone()
    assert n >= 500, f"poche righe: {n}"
    assert nulli == 0
    assert fuori == 0


def test_profilo_legge_mart_persone():
    """L'identità viene da mart_persone, non da anagrafica + ponte."""
    sql = (REPO_ROOT / "compose" / "persone" / "sql" / "mart_profilo.sql").read_text("utf-8")
    code = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    assert "FROM mart_persone" in code
    assert "senato_anagrafica" not in code
    assert "ponte_persona" not in code


def test_profilo_maggioranza_deterministica():
    """La moda del gruppo non usa `arg_max` (tie-break arbitrario)."""
    sql = (REPO_ROOT / "compose" / "persone" / "sql" / "mart_profilo.sql").read_text("utf-8")
    code = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    assert "arg_max" not in code
    assert "ORDER BY count(*) DESC, voto" in code
    assert "n_secondo IS NULL OR n > n_secondo" in code
