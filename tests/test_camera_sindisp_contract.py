"""Contract camera_sindisp — atto, firmatari, destinatari.

Policy:
- il raw passa da uno script (keyset manuale): il plugin sparql del toolkit
  inietta FILTER dopo la WHERE e Virtuoso lo rifiuta;
- un atto per riga nel dataset principale (PK atto_id);
- firmatari e destinatari sono dataset ponte con PK qualificate;
- il mirror Senato (URI `_S`) è escluso alla fonte.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

import toolkit

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS = REPO_ROOT / "datasets"
MACROS = Path(toolkit.__file__).parent / "sql" / "macros.sql"
MART_ODG_DDL = DATASETS / "camera-sindisp" / "sql" / "mart_odg_ddl.sql"
MART_ODG_DDL_SINTESI = DATASETS / "camera-sindisp" / "sql" / "mart_odg_ddl_sintesi.sql"


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACROS.read_text(encoding="utf-8"))
    return con


def _cfg(slug: str) -> dict:
    return yaml.safe_load((DATASETS / slug / "dataset.yml").read_text("utf-8"))


def _clean_sql(slug: str) -> str:
    return (DATASETS / slug / "sql" / "clean.sql").read_text("utf-8").replace("{year}", "19")


def test_main_config_usa_script_e_partiziona_per_legislatura():
    cfg = _cfg("camera-sindisp")
    source = cfg["raw"]["sources"][0]
    assert source["type"] == "script"
    assert "--legislature {year}" in source["args"]["command"]
    assert "--mode ato" in source["args"]["command"]
    assert source["args"]["output"].endswith(".parquet")
    assert cfg["dataset"]["years"] == [13, 14, 15, 16, 17, 18, 19]
    assert cfg["clean"]["validate"]["primary_key"] == ["atto_id"]


def test_main_clean_dedup_e_mapping_tipi():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('http://dati.camera.it/ocd/aic.rdf/aic1_00001_19',
           'INTERROGAZIONE A RISPOSTA SCRITTA', '1/00001', '20221110',
           'Titolo', 'Testo', 'Camera dei Deputati',
           'http://dati.camera.it/ocd/deputato.rdf/d1_19', 'ON. UNO',
           '1', NULL),
          ('http://dati.camera.it/ocd/aic.rdf/aic1_00001_19',
           'INTERROGAZIONE A RISPOSTA SCRITTA', '1/00001', '20221110',
           'Titolo', 'Testo', 'Camera dei Deputati',
           'http://dati.camera.it/ocd/deputato.rdf/d1_19', 'ON. UNO',
           '1', NULL)
        ) AS t(atto, tipo, numero, data, titolo, descrizione, ramo,
               primo, primo_label, concluso, risposta)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp")).fetchdf()
    assert len(out) == 1
    row = out.iloc[0]
    assert row["atto_id"].endswith("aic1_00001_19")
    assert row["tipo_categoria"] == "Interrogazione scritta"
    assert str(row["data_presentazione"])[:10] == "2022-11-10"
    assert row["ha_risposta"] in (False, 0)
    assert row["concluso"] in (True, 1)
    assert row["legislatura"] == 19


def test_main_clean_mappa_tutti_i_tipi_e_risposta():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('a1', 'INTERROGAZIONE A RISPOSTA ORALE', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '1', 'r'),
          ('a2', 'INTERROGAZIONE A RISPOSTA IN COMMISSIONE', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '0', NULL),
          ('a3', 'INTERPELLANZA', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '1', NULL),
          ('a4', 'MOZIONE', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '1', NULL),
          ('a5', 'RISOLUZIONE IN ASSEMBLEA', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '1', NULL),
          ('a6', 'ODG - ORDINE DEL GIORNO IN ASSEMBLEA', 'x', '20230101', 't', 'd', 'Camera dei Deputati', NULL, NULL, '1', NULL)
        ) AS t(atto, tipo, numero, data, titolo, descrizione, ramo,
               primo, primo_label, concluso, risposta)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp")).fetchdf().set_index("atto_id")
    assert out.loc["a1", "tipo_categoria"] == "Interrogazione orale"
    assert out.loc["a2", "tipo_categoria"] == "Interrogazione in commissione"
    assert out.loc["a3", "tipo_categoria"] == "Interpellanza"
    assert out.loc["a4", "tipo_categoria"] == "Mozione"
    assert out.loc["a5", "tipo_categoria"] == "Risoluzione"
    assert out.loc["a6", "tipo_categoria"] == "Ordine del giorno"
    assert bool(out.loc["a1", "ha_risposta"]) is True
    assert bool(out.loc["a2", "ha_risposta"]) is False


def test_main_clean_parse_data_storica_con_suffisso():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('a1', 'MOZIONE', 'x', '19960509-', 't', 'd', 'Camera dei Deputati',
           NULL, NULL, '1', NULL)
        ) AS t(atto, tipo, numero, data, titolo, descrizione, ramo,
               primo, primo_label, concluso, risposta)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp")).fetchdf()
    assert str(out.iloc[0]["data_presentazione"])[:10] == "1996-05-09"
    assert int(out.iloc[0]["anno"]) == 1996


def test_firmatari_clean_dedup_e_persona_id():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('a1', 'http://dati.camera.it/ocd/deputato.rdf/d307219_19', 'primo', 'ON. UNO'),
          ('a1', 'http://dati.camera.it/ocd/deputato.rdf/d307219_19', 'primo', 'ON. UNO'),
          ('a1', 'http://dati.camera.it/ocd/deputato.rdf/d307223_19', 'altro', 'ON. DUE')
        ) AS t(atto, firm, ruolo, label)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp-firmatari")).fetchdf()
    assert len(out) == 2
    assert set(out["ruolo"]) == {"primo", "altro"}
    assert set(out["persona_id"].dropna().astype(int)) == {307219, 307223}


def test_destinatari_clean_organo_e_risposta():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('a1', 'http://dati.camera.it/ocd/organoGoverno.rdf/og182_624', 'MINISTERO ISTRUZIONE', 'r1'),
          ('a1', 'http://dati.camera.it/ocd/organoGoverno.rdf/og182_624', 'MINISTERO ISTRUZIONE', 'r1'),
          ('a1', 'http://dati.camera.it/ocd/organoGoverno.rdf/og182_588', 'MINISTERO PARI OPPORTUNITA', NULL)
        ) AS t(atto, dest, label, risposta)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp-destinatari")).fetchdf()
    assert len(out) == 2
    assert set(out["organo_id"]) == {"og182_624", "og182_588"}
    flags = dict(zip(out["organo_id"], out["ha_risposta"]))
    assert bool(flags["og182_624"]) is True
    assert bool(flags["og182_588"]) is False


def test_bridge_config_pk_qualificate():
    firm = _cfg("camera-sindisp-firmatari")
    dest = _cfg("camera-sindisp-destinatari")
    assert firm["clean"]["validate"]["primary_key"] == ["atto_id", "firmatario_uri", "ruolo"]
    assert dest["clean"]["validate"]["primary_key"] == ["atto_id", "destinatario_uri"]
    assert "--mode firmatari" in firm["raw"]["sources"][0]["args"]["command"]
    assert "--mode destinatari" in dest["raw"]["sources"][0]["args"]["command"]


def test_config_support_camera_ddl_e_mart_ponte():
    cfg = _cfg("camera-sindisp")
    support = {s["name"]: s for s in cfg["support"]}
    assert support["camera_ddl"]["config"] == "../camera-ddl/dataset.yml"
    assert support["camera_ddl"]["years"] == [13, 14, 15, 16, 17, 18, 19]
    mart_names = {t["name"] for t in cfg["mart"]["tables"]}
    assert {"mart_odg_ddl", "mart_odg_ddl_sintesi"} <= mart_names


def test_clean_estrae_numero_ddl_dal_titolo_odg():
    con = _connect()
    con.execute(
        """
        CREATE TABLE raw_input AS SELECT * FROM (VALUES
          ('a1', 'ODG - ORDINE DEL GIORNO IN ASSEMBLEA', '9/00005-A/004',
           '20221110', 'ODG IN ASSEMBLEA SU P.D.L. 9/00005-A/004 presentata da X',
           'testo', 'Camera dei Deputati', NULL, NULL, '1', NULL)
        ) AS t(atto, tipo, numero, data, titolo, descrizione, ramo,
               primo, primo_label, concluso, risposta)
        """
    )
    out = con.execute(_clean_sql("camera-sindisp")).fetchdf()
    assert out.iloc[0]["ddl_numero"] == 5


def test_mart_odg_ddl_join_e_sintesi():
    con = _connect()
    con.execute(
        """
        CREATE TABLE clean_input AS SELECT * FROM (VALUES
          ('a1', 'Ordine del giorno', 19, 5),
          ('a2', 'Ordine del giorno', 19, 5),
          ('a3', 'Ordine del giorno', 19, 7),
          ('a4', 'Ordine del giorno', 19, NULL)
        ) AS t(atto_id, tipo_categoria, legislatura, ddl_numero)
        """
    )
    con.execute(
        """
        CREATE TABLE ddl_fixture AS SELECT * FROM (VALUES
          (5, 19, 'Conversione in legge del decreto-legge X'),
          (7, 19, 'Bilancio di previsione dello Stato')
        ) AS t(id_ddl, legislatura, titolo)
        """
    )
    mart = MART_ODG_DDL.read_text("utf-8").replace(
        "read_parquet('{support.camera_ddl.clean}')", "ddl_fixture"
    )
    out = con.execute(mart).fetchdf().set_index("id_ddl")
    assert int(out.loc[5, "n_odg"]) == 2
    assert bool(out.loc[5, "matched"]) is True
    assert bool(out.loc[5, "is_dl_o_bilancio"]) is True
    assert int(out.loc[7, "n_odg"]) == 1
    assert bool(out.loc[7, "is_dl_o_bilancio"]) is True

    sintesi = MART_ODG_DDL_SINTESI.read_text("utf-8").replace(
        "read_parquet('{support.camera_ddl.clean}')", "ddl_fixture"
    )
    row = con.execute(sintesi).fetchdf().iloc[0]
    assert int(row["n_odg"]) == 4
    assert int(row["n_con_numero"]) == 3
    assert int(row["n_con_match"]) == 3
    assert int(row["n_dl_o_bilancio"]) == 3
    assert float(row["pct_con_match"]) == 75.0
