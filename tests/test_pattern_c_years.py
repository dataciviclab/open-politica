"""Contract Pattern C — dataset SPARQL hardcoded Leg19 → years legislatura.

policy: i dataset Pattern C devono usare {year} nella query e years
allineati al LOD (Senato I–XII assenti; Camera relatori solo da Leg16).
Un revert silenzioso a `19` hardcoded o years:[2026] deve fallire qui.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# dataset Pattern C → (years attesi, frammenti obbligatori in dataset.yml)
PATTERN_C = {
    "senato-firmatari": (
        [13, 14, 15, 16, 17, 18, 19],
        ["GRAPH <http://dati.senato.it/ddl/{year}>"],
    ),
    "senato-gruppi": (
        [13, 14, 15, 16, 17, 18, 19],
        ["GRAPH <http://dati.senato.it/composizione/{year}>"],
    ),
    "senato-anagrafica": (
        [13, 14, 15, 16, 17, 18, 19],
        ["GRAPH <http://dati.senato.it/composizione/{year}>"],
    ),
    "senato-commissioni": (
        [13, 14, 15, 16, 17, 18, 19],
        ["GRAPH <http://dati.senato.it/composizione/{year}>"],
    ),
    "senato-interventi": (
        [13, 14, 15, 16, 17, 18, 19],
        ["GRAPH <http://dati.senato.it/composizione/{year}>"],
    ),
    "camera-commissioni": (
        [13, 14, 15, 16, 17, 18, 19],
        ["repubblica_{year}"],
    ),
    # LOD Camera: rel13/14/15_ = 0 live (2026-10-02)
    "camera-relatori": (
        [16, 17, 18, 19],
        ["rel{year}_"],
    ),
}

# clean che devono iniettare la legislatura da {year}
CLEAN_WITH_YEAR = [
    "senato-gruppi",
    "senato-anagrafica",
    "senato-commissioni",
    "senato-interventi",
    "camera-commissioni",
    "camera-relatori",
]

# Support multi-anno Pattern C nei dataset (non compose — fuori scope PR #52).
# I compose restano su years:[2026] fino a un follow-up dedicato.
DATASET_SUPPORT = {
    "datasets/ponte-persona/dataset.yml": {
        "senato_anagrafica": [13, 14, 15, 16, 17, 18, 19],
    },
    "datasets/senato-sindisp/dataset.yml": {
        "senato_anagrafica": [13, 14, 15, 16, 17, 18, 19],
    },
}


def _load(rel: str) -> dict:
    return yaml.safe_load((REPO_ROOT / rel).read_text("utf-8"))


def test_pattern_c_years_e_query():
    """contract: years allineati al LOD + {year} nella SPARQL (no hardcoded 19)."""
    for ds, (years, fragments) in PATTERN_C.items():
        cfg = _load(f"datasets/{ds}/dataset.yml")
        assert cfg["dataset"]["years"] == years, ds
        q = cfg["raw"]["sources"][0]["args"]["query"]
        for frag in fragments:
            assert frag in q, f"{ds}: manca {frag!r}"
        # niente revert silenzioso al grafo unico Leg19
        assert "/ddl/19>" not in q, ds
        assert "composizione/19>" not in q, ds
        assert "repubblica_19>" not in q, ds
        assert 'rel19_' not in q, ds


def test_pattern_c_clean_inietta_legislatura():
    """contract: clean multi-leg usano {year} AS legislatura dove serve."""
    for ds in CLEAN_WITH_YEAR:
        sql = (REPO_ROOT / f"datasets/{ds}/sql/clean.sql").read_text("utf-8")
        assert "{year}" in sql, ds
        assert "AS legislatura" in sql, ds


def test_dataset_support_years_allineati():
    """contract: support multi-anno Pattern C nei dataset (non compose)."""
    for rel, expected in DATASET_SUPPORT.items():
        cfg = _load(rel)
        support = {s["name"]: s for s in cfg.get("support", []) if isinstance(s, dict)}
        for name, years in expected.items():
            assert name in support, f"{rel}: manca support {name}"
            assert support[name].get("years") == years, (
                f"{rel}: support {name} years={support[name].get('years')} != {years}"
            )


def test_compose_fuori_scope_pattern_c():
    """policy: i compose non devono essere toccati da Pattern C (follow-up dedicato).

    Se un compose dovesse già dichiarare support multi-anno sui dataset
    Pattern C, questo test fallisce: allora il pin è entrato per sbaglio
    e va spostato nella PR dei compose.
    """
    for rel in (
        "compose/profilo-politico/dataset.yml",
        "compose/osservatorio-parlamento/dataset.yml",
    ):
        cfg = _load(rel)
        support = {s["name"]: s for s in cfg.get("support", []) if isinstance(s, dict)}
        for name in (
            "senato_anagrafica",
            "senato_gruppi",
            "senato_commissioni",
            "senato_interventi",
            "camera_commissioni",
            "camera_relatori",
        ):
            if name not in support:
                continue
            years = support[name].get("years") or []
            # ammesso solo [2026] o assente: multi-anno = fuori scope
            assert years in ([], [2026]), (
                f"{rel}: support {name} years={years} — Pattern C non tocca i compose"
            )


def test_firmatari_notes_idddl_globale():
    """policy: le notes documentano l'univocità idDdl Leg13–19 (review #52)."""
    notes = (
        REPO_ROOT / "datasets/senato-firmatari/notes.md"
    ).read_text("utf-8")
    assert "globale" in notes.lower()
    assert "idDdl" in notes
