"""Contract camera_iter — build offline, clean e mart deterministici.

Non tocca la rete: costruisce una cache sintetica nel layout di preprocess.py
e verifica link atto, fallback dibattito, date range, numero Senato e PK.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "datasets" / "camera-iter"

OCD = "http://dati.camera.it/ocd/"


def _load_preprocess():
    spec = importlib.util.spec_from_file_location("camera_iter_preprocess",
                                                  DATASET / "preprocess.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_rows() -> dict[str, list[dict]]:
    return {
        "assegnazione": [
            {"s": f"{OCD}assegnazione.rdf/a19_1", "org": f"{OCD}organo.rdf/o19_10",
             "orgLabel": "I Commissione(Affari costituzionali)", "date": None, "dataAsn": "20230301",
             "sede": "Referente", "ident": "1", "dib": None, "ac": None, "label": None},
            {"s": f"{OCD}assegnazione.rdf/a19_2", "org": f"{OCD}organo.rdf/o19_10",
             "orgLabel": "I Commissione(Affari costituzionali)", "date": None, "dataAsn": "20230302",
             "sede": "Referente", "ident": "2", "dib": f"{OCD}dibattito.rdf/d19_5",
             "ac": f"{OCD}attocamera.rdf/ac19_101", "label": None},
            {"s": f"{OCD}assegnazione.rdf/a19_2", "org": f"{OCD}organo.rdf/o19_11",
             "orgLabel": "Bilancio", "date": None, "dataAsn": "20230302",
             "sede": "Referente", "ident": "2", "dib": f"{OCD}dibattito.rdf/d19_5",
             "ac": f"{OCD}attocamera.rdf/ac19_101", "label": None},
            # URI non standard: il numero non è l'ultimo segmento numerico.
            # Prima del fix entrambi collassavano su asn__19_10.
            {"s": f"{OCD}assegnazione.rdf/a19_19VII0743",
             "org": f"{OCD}organo.rdf/o19_10",
             "orgLabel": "I Commissione(Affari costituzionali)",
             "date": None, "dataAsn": "20230303", "sede": "Referente",
             "ident": "19VII0743", "dib": None, "ac": None, "label": None},
            {"s": f"{OCD}assegnazione.rdf/a19_19VII0744",
             "org": f"{OCD}organo.rdf/o19_10",
             "orgLabel": "I Commissione(Affari costituzionali)",
             "date": None, "dataAsn": "20230304", "sede": "Referente",
             "ident": "19VII0744", "dib": None, "ac": None, "label": None},
        ],
        "statoIter": [
            {"s": f"{OCD}statoIter.rdf/si19_1", "label": "In corso",
             "date": "20230303", "type": "Iter"},
        ],
        "trasmissione": [
            {"s": f"{OCD}trasmissione.rdf/tr19_1",
             "label": "Disegno di legge (S. 393) Trasmesso dalla Camera dei Deputati",
             "date": "20230304", "type": "Trasmissione", "prov": "Senato", "senato": None},
        ],
        "richiestaParere": [
            {"s": f"{OCD}richiestaParere.rdf/rp19_1", "dib": f"{OCD}dibattito.rdf/d19_5",
             "dibLabel": "I Commissione(Affari costituzionali)", "dibTitle": None,
             "dibDate": "20230305", "dibDateRange": None,
             "ac": f"{OCD}attocamera.rdf/ac19_101", "esito": "Espresso", "label": None},
            {"s": f"{OCD}richiestaParere.rdf/rp19_2", "dib": f"{OCD}dibattito.rdf/d19_6",
             "dibLabel": None,
             "dibTitle": "Commissione parlamentare per le questioni regionali",
             "dibDate": None, "dibDateRange": "20230306-20230307",
             "ac": f"{OCD}attocamera.rdf/ac19_102", "esito": "Espresso", "label": None},
        ],
    }


def _write_cache(pp, cache: Path) -> None:
    cache.mkdir()
    for cls, rows in _fixture_rows().items():
        folder = cache / f"details_19_{cls}"
        folder.mkdir()
        for row in rows:
            row["_class"] = cls
            row["_leg"] = 19
        pp.write_rows(rows, folder / "batch_00000.parquet", pp.CANONICAL_EVENT_COLUMNS)
        (cache / f"count_19_{cls}.json").write_text(
            json.dumps({"n": len({r["s"] for r in rows})}), encoding="utf-8"
        )

    links = {
        "assegnazione": [
            {"a": f"{OCD}attocamera.rdf/ac19_100", "e": f"{OCD}assegnazione.rdf/a19_1"},
        ],
        "statoIter": [
            {"a": f"{OCD}attocamera.rdf/ac19_100", "e": f"{OCD}statoIter.rdf/si19_1"},
        ],
        "trasmissione": [
            {"a": f"{OCD}attocamera.rdf/ac19_100", "e": f"{OCD}trasmissione.rdf/tr19_1"},
        ],
    }
    for cls, rows in links.items():
        pp.write_rows(rows, cache / f"links_19_{cls}.parquet", pp.CANONICAL_LINK_COLUMNS)

    organi = [
        {"o": f"{OCD}organo.rdf/o19_10", "label": "I COMMISSIONE (AFFARI COSTITUZIONALI)"},
        {"o": f"{OCD}organo.rdf/o19_11", "label": "Bilancio"},
        {"o": f"{OCD}organo.rdf/o19_4023",
         "label": "Commissione parlamentare per le questioni regionali"},
    ]
    pp.write_rows(organi, cache / "organi_19.parquet", ["o", "label"])


def test_build_clean_mart_offline(tmp_path: Path):
    pp = _load_preprocess()
    cache = tmp_path / "_cache"
    _write_cache(pp, cache)
    final = pp.build_final(tmp_path, cache, [19])

    con = duckdb.connect()
    con.execute("CREATE MACRO normalize_string(x) AS NULLIF(TRIM(x), '')")
    con.execute(f"CREATE VIEW raw_input AS SELECT * FROM read_parquet('{final.as_posix()}')")

    events = con.execute("SELECT * FROM raw_input ORDER BY evento_id").fetchdf()
    assert len(events) == 9
    assert set(events["tipo_evento"]) == {
        "assegnazione", "statoIter", "trasmissione", "richiestaParere"}

    asn = events[events["tipo_evento"] == "assegnazione"]
    assert set(asn["atto_id"].dropna().astype(int)) == {100, 101}
    assert (asn[asn["atto_id"] == 101]["atto_source"] == "dibattito").all()
    ns = asn[asn["evento_uri"].str.contains("19VII074")]
    assert len(ns) == 2
    assert ns["evento_id"].nunique() == 2, "URI non standard collassati su evento_id"

    trs = events[events["tipo_evento"] == "trasmissione"].iloc[0]
    assert trs["senato_atto_num"] == "393"
    rqp2 = events[events["evento_id"].str.startswith("rqp_2_19")].iloc[0]
    assert str(rqp2["data"])[:10] == "2023-03-06"

    clean_sql = (DATASET / "sql" / "clean.sql").read_text(encoding="utf-8")
    con.execute("CREATE TABLE clean_tbl AS " + clean_sql)
    assert con.execute("SELECT count(*) - count(DISTINCT evento_id) FROM clean_tbl").fetchone()[0] == 0

    parere = con.execute(
        "SELECT organo_id, organo_label FROM clean_tbl WHERE evento_id LIKE 'rqp_1_19'"
    ).fetchone()
    assert parere[0].endswith("o19_10")
    parere2 = con.execute(
        "SELECT organo_id FROM clean_tbl WHERE evento_id LIKE 'rqp_2_19'"
    ).fetchone()
    assert parere2[0].endswith("o19_4023")

    con.execute("CREATE VIEW clean_input AS SELECT * FROM clean_tbl")

    def run_mart(name: str):
        sql = (DATASET / "sql" / f"{name}.sql").read_text(encoding="utf-8")
        return con.execute(sql).fetchdf()

    mi = run_mart("mart_iter_per_atto")
    run_mart("mart_tempi")
    mc = run_mart("mart_commissioni")

    row101 = mi[mi["atto_id"] == 101].iloc[0]
    assert (row101["n_eventi"], row101["n_assegnazioni"], row101["n_pareri"]) == (2, 1, 1)
    organo10 = mc[mc["organo_id"].str.endswith("o19_10")].iloc[0]
    assert (organo10["n_assegnazioni"], organo10["n_pareri"]) == (4, 1)
