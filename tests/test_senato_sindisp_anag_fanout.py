"""Regression senato_sindisp — join anagrafica multi-leg senza fan-out.

policy: support senato_anagrafica con years [13..19] → {support.*.clean}
è un glob multi-anno. Il clean deve produrre UNA riga per (atto_id,
senatore_id); un join grezzo su senatore_id duplica le iniziative
(PK validation fallisce in CI).

Prova del fuoco: se cancello il dedup in anag o il GROUP BY finale,
questo test fallisce (righe > raw, PK dup).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEAN_SQL = REPO_ROOT / "datasets" / "senato-sindisp" / "sql" / "clean.sql"
DATASET_YML = REPO_ROOT / "datasets" / "senato-sindisp" / "dataset.yml"


def _load_clean_sql() -> str:
    return CLEAN_SQL.read_text("utf-8")


def test_sindisp_support_anagrafica_multi_leg():
    """contract: support anagrafica su sindisp = years Pattern C (non [2026])."""
    cfg = yaml.safe_load(DATASET_YML.read_text("utf-8"))
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    assert "senato_anagrafica" in support
    assert support["senato_anagrafica"]["years"] == [13, 14, 15, 16, 17, 18, 19]


def test_sindisp_clean_dedup_anagrafica_e_pk():
    """contract: clean dedup anagrafica + GROUP BY PK (atto_id, senatore_id)."""
    sql = _load_clean_sql()
    assert "{support.senato_anagrafica.clean}" in sql
    assert "GROUP BY senatore_id" in sql
    assert "arg_max(" in sql
    assert "GROUP BY s.atto_id, s.senatore_id" in sql


def test_sindisp_join_multi_year_no_fanout():
    """regression: anagrafica multi-anno non moltiplica le iniziative."""
    con = duckdb.connect()
    # Fixture raw: stesso senatore su 2 iniziative dello stesso atto + 1 altro atto
    con.execute(
        """
        CREATE TABLE raw_input AS
        SELECT * FROM (VALUES
          (100, 'Interrogazione', '100', DATE '2001-05-01', 'presentata', 'u1', 'label1',
           'http://dati.senato.it/iniziativa/i1', 10, 'Sen. Rossi', 'Parlamentare'),
          (100, 'Interpellanza', '100', DATE '2001-05-02', 'presentata', 'u1', 'label1',
           'http://dati.senato.it/iniziativa/i2', 10, 'Sen. Rossi', 'Parlamentare'),
          (200, 'Mozione', '200', DATE '2001-06-01', 'approvata', 'u2', 'label2',
           'http://dati.senato.it/iniziativa/i3', 20, 'Sen. Bianchi', 'Parlamentare')
        ) AS t(atto, tipo, numero, data, esito, url, label,
               iniziativa, senatore, presentatore, tipoIniziativa)
        """
    )
    # anagrafica multi-leg: senatore 10 compare in due legislature
    con.execute(
        """
        CREATE TABLE anag_multi AS
        SELECT * FROM (VALUES
          (10, 'Mario', 'Rossi', DATE '1950-01-01', 'Roma', 13),
          (10, 'Mario', 'Rossi', DATE '1950-01-01', 'Roma', 19),
          (20, 'Anna', 'Bianchi', DATE '1960-02-02', 'Torino', 19)
        ) AS t(senatore_id, nome, cognome, data_nascita, luogo_nascita, legislatura)
        """
    )
    # Riscrittura del clean per duckdb puro: niente macro toolkit.
    sql = """
    WITH sindisp AS (
        SELECT
            CAST(atto AS BIGINT) AS atto_id,
            tipo, numero, data AS data_presentazione, esito, url AS url_testo,
            label AS label_atto,
            CAST(senatore AS BIGINT) AS senatore_id,
            presentatore, tipoIniziativa AS tipo_iniziativa,
            CASE
                WHEN tipo ILIKE '%interrogazione%' THEN 'Interrogazione'
                WHEN tipo ILIKE '%interpellanza%'  THEN 'Interpellanza'
                WHEN tipo ILIKE '%mozione%'        THEN 'Mozione'
                ELSE tipo
            END AS tipo_categoria,
            14 AS legislatura
        FROM raw_input
        WHERE atto IS NOT NULL AND senatore IS NOT NULL
    ),
    anag AS (
        SELECT
            senatore_id,
            arg_max(nome,          legislatura) AS nome,
            arg_max(cognome,       legislatura) AS cognome,
            arg_max(data_nascita,  legislatura) AS data_nascita,
            arg_max(luogo_nascita, legislatura) AS luogo_nascita
        FROM anag_multi
        WHERE senatore_id IS NOT NULL
        GROUP BY senatore_id
    )
    SELECT
        s.atto_id,
        MAX(s.tipo) AS tipo,
        s.senatore_id,
        MAX(s.legislatura) AS legislatura,
        MAX(a.nome) AS nome_senatore
    FROM sindisp s
    LEFT JOIN anag a ON s.senatore_id = a.senatore_id
    GROUP BY s.atto_id, s.senatore_id
    """
    out = con.execute(sql).df()
    # 2 righe (atto 100 + atto 200), NON 3 — senatore 10 non fan-out
    assert len(out) == 2, f"attese 2 righe, ottenute {len(out)}:\n{out}"
    assert out.duplicated(subset=["atto_id", "senatore_id"]).sum() == 0
    sen10 = out[out["senatore_id"] == 10]
    assert len(sen10) == 1
    assert sen10.iloc[0]["nome_senatore"] == "Mario"
    # controllo anti-regression: join grezzo multi-year = fan-out
    # (2 iniziative atto100 × 2 righe anag sen10 + 1 atto200 × 1 = 5)
    bad = con.execute(
        """
        WITH sindisp AS (
            SELECT CAST(atto AS BIGINT) AS atto_id, CAST(senatore AS BIGINT) AS senatore_id
            FROM raw_input
        )
        SELECT s.atto_id, s.senatore_id, a.nome
        FROM sindisp s
        LEFT JOIN anag_multi a ON s.senatore_id = a.senatore_id
        """
    ).df()
    assert len(bad) == 5, f"il fixture multi-year deve dimostrare il fan-out grezzo: {len(bad)}"
