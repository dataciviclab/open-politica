"""Contract senato_emendamenti_lod — multi-leg + keyset + grano emendamento.

policy:
- multi-legislatura 13–19 con `{year}` nel FILTER sul nome-grafo (i grafi
  `emendamenti/{leg}_{part}` sono spezzati in parti);
- paginazione **keyset** su `?e` con il placeholder `{keyset}` isolato in
  sottoquery (l'OFFSET su Virtuoso duplica con il FILTER sul nome-grafo);
- grano = emendamento (PK `emend_uri_id`), perché un oggetto può relativoA
  più ddl (atti abbinati).

Un revert silenzioso a OFFSET, a `19` hardcoded o a un grano diverso rompe qui.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DS = REPO_ROOT / "datasets/senato-emendamenti-lod"


def _cfg() -> dict:
    return yaml.safe_load((DS / "dataset.yml").read_text("utf-8"))


def test_years_e_placeholder_year():
    """contract: years allineati al LOD + {year} nel filtro sul nome-grafo."""
    cfg = _cfg()
    assert cfg["dataset"]["years"] == [13, 14, 15, 16, 17, 18, 19]
    q = cfg["raw"]["sources"][0]["args"]["query"]
    assert "emendamenti/{year}" in q
    # niente revert al grafo unico Leg19
    assert "emendamenti/19" not in q


def test_paginazione_keyset_con_placeholder():
    """policy: keyset su ?e con {keyset} isolato (l'OFFSET duplica)."""
    args = _cfg()["raw"]["sources"][0]["args"]
    assert args["pagination"] == {"mode": "keyset", "key": "?e"}
    assert "{keyset}" in args["query"]
    # ORDER BY ?e obbligatorio per il keyset
    assert "ORDER BY ?e" in args["query"]


def test_clean_grano_emendamento_e_legislatura():
    """contract: {year} AS legislatura + grano per emendamento (dedup)."""
    sql = (DS / "sql/clean.sql").read_text("utf-8")
    assert "{year}" in sql
    assert "AS legislatura" in sql
    assert "GROUP BY emend_uri_id" in sql
