"""Regression senato_sindisp — anagrafica multi-leg senza fan-out.

policy: {support.senato_anagrafica.clean} multi-anno → dedup SOLO su anag.
Il raw sindisp non va filtrato su senatore (le leg. storiche hanno
iniziativa senza URI) né raggruppato a valle (perde iniziative).

Prova del fuoco: join grezzo multi-year = fan-out; con anag dedup = no.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEAN_SQL = REPO_ROOT / "datasets" / "senato-sindisp" / "sql" / "clean.sql"
DATASET_YML = REPO_ROOT / "datasets" / "senato-sindisp" / "dataset.yml"


def test_sindisp_support_anagrafica_multi_leg():
    cfg = yaml.safe_load(DATASET_YML.read_text("utf-8"))
    support = {s["name"]: s for s in cfg["support"] if isinstance(s, dict)}
    assert support["senato_anagrafica"]["years"] == [13, 14, 15, 16, 17, 18, 19]


def test_sindisp_clean_shape():
    sql = CLEAN_SQL.read_text("utf-8")
    assert "{support.senato_anagrafica.clean}" in sql
    assert "GROUP BY senatore_id" in sql
    assert "arg_max(" in sql
    # non deve azzerare le righe raw
    assert "senatore IS NOT NULL" not in sql
    # non deve raggruppare il raw (perde iniziative)
    assert "GROUP BY s.atto_id" not in sql


def test_sindisp_anag_dedup_no_fanout():
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE raw_input AS
        SELECT * FROM (VALUES
          (100, 'Interrogazione', '100', DATE '2001-05-01', 'presentata', 'u1', 'l1',
           'http://x/iniziativa/i1', 10, 'Sen. Rossi', 'Parlamentare'),
          (100, 'Interpellanza', '100', DATE '2001-05-02', 'presentata', 'u1', 'l1',
           'http://x/iniziativa/i2', 10, 'Sen. Rossi', 'Parlamentare'),
          (200, 'Mozione', '200', DATE '2001-06-01', 'approvata', 'u2', 'l2',
           'http://x/iniziativa/i3', 20, 'Sen. Bianchi', 'Parlamentare'),
          (300, 'Interrogazione', '300', DATE '2001-07-01', 'presentata', NULL, 'l3',
           NULL, NULL, NULL, NULL)
        ) AS t(atto, tipo, numero, data, esito, url, label,
               iniziativa, senatore, presentatore, tipoIniziativa)
        """
    )
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
    # stessa logica del clean (macro toolkit assenti)
    sql = """
    WITH sindisp AS (
        SELECT
            CAST(atto AS BIGINT) AS atto_id,
            tipo, numero, data AS data_presentazione, esito, url AS url_testo,
            label AS label_atto,
            CASE WHEN senatore IS NULL THEN NULL
                 ELSE CAST(senatore AS BIGINT) END AS senatore_id,
            presentatore, tipoIniziativa AS tipo_iniziativa,
            tipo AS tipo_categoria,
            14 AS legislatura
        FROM raw_input
        WHERE atto IS NOT NULL
    ),
    anag AS (
        SELECT senatore_id,
               arg_max(nome, legislatura) AS nome,
               arg_max(cognome, legislatura) AS cognome,
               arg_max(data_nascita, legislatura) AS data_nascita,
               arg_max(luogo_nascita, legislatura) AS luogo_nascita
        FROM anag_multi
        WHERE senatore_id IS NOT NULL
        GROUP BY senatore_id
    )
    SELECT s.atto_id, s.tipo, s.senatore_id, a.nome AS nome_senatore
    FROM sindisp s
    LEFT JOIN anag a ON s.senatore_id = a.senatore_id
    """
    out = con.execute(sql).df()
    # 4 righe raw: non filtrare le iniziative senza senatore
    assert len(out) == 4, f"attese 4 righe raw, ottenute {len(out)}:\n{out}"
    # sen10: 2 iniziative restano 2 (non 4 = fan-out anag)
    sen10 = out[out["senatore_id"] == 10]
    assert len(sen10) == 2
    assert (sen10["nome_senatore"] == "Mario").all()
    # riga senza senatore: non droppata, nome null
    null_sen = out[out["senatore_id"].isna()]
    assert len(null_sen) == 1
    # join grezzo multi-year avrebbe prodotto 2+2+1+1=6
    bad = con.execute(
        """
        SELECT s.atto_id, s.senatore_id
        FROM (SELECT CAST(atto AS BIGINT) AS atto_id,
                     CAST(senatore AS BIGINT) AS senatore_id
              FROM raw_input WHERE atto IS NOT NULL) s
        LEFT JOIN anag_multi a ON s.senatore_id = a.senatore_id
        """
    ).df()
    assert len(bad) == 6, f"fixture deve mostrare fan-out grezzo: {len(bad)}"
