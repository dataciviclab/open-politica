"""Contract senato_votazioni — percorso incrementale.

Protegge tre cose che, se rotte, non si vedono dal risultato (solo dal tempo
o da un buco nei dati):

1. la lista dei graph per legislatura (niente scansione globale dello store);
2. il filtro ``sedute >= max(data)`` con il confine incluso;
3. la query metadati che in incrementale chiede SOLO le sedute nuove,
   invece di rileggere tutte le votazioni della legislatura.

Non tocca la rete: ``query`` è sostituita da un finto che cattura lo SPARQL.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PREPROCESS = REPO_ROOT / "datasets" / "senato-votazioni" / "preprocess.py"

pytestmark = pytest.mark.contract


def _load_preprocess():
    spec = importlib.util.spec_from_file_location("senato_votazioni_preprocess", PREPROCESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Graph per legislatura
# ---------------------------------------------------------------------------


def test_graph_list_xix_include_fasi_5():
    """XIX: doc + fasi 1-5 + sindisp (7 graph) — fasi-5 esiste solo dalla XIX."""
    m = _load_preprocess()
    graphs = m.graphs_for_legislature(19)
    assert len(graphs) == 7
    assert "http://dati.senato.it/votazioni-fasi-5/19" in graphs
    assert "http://dati.senato.it/votazioni-sindisp/19" in graphs


def test_graph_list_xviii_senza_fasi_5():
    m = _load_preprocess()
    graphs = m.graphs_for_legislature(18)
    assert len(graphs) == 6
    assert not any("fasi-5" in g for g in graphs)


def test_graph_list_legislature_vecchie_graph_unico():
    """XIII-XVI: un solo graph ``votazioni/<leg>``."""
    m = _load_preprocess()
    assert m.graphs_for_legislature(13) == ["http://dati.senato.it/votazioni/13"]
    assert m.graphs_for_legislature(16) == ["http://dati.senato.it/votazioni/16"]


# ---------------------------------------------------------------------------
# Filtro sedute
# ---------------------------------------------------------------------------


def test_sedute_dal_confine_incluso():
    """La seduta del giorno ``max(data)`` resta: può ricevere voti a fine giornata."""
    m = _load_preprocess()
    sedute = [
        {"s": "s-vecchia", "d": "2026-09-30"},
        {"s": "s-confine", "d": "2026-10-01"},
        {"s": "s-nuova", "d": "2026-10-02"},
    ]
    assert m.sedute_dal(sedute, date(2026, 10, 1)) == {"s-confine", "s-nuova"}


def test_sedute_dal_ignora_date_mancanti():
    m = _load_preprocess()
    sedute = [{"s": "s-senza-data", "d": None}, {"s": "s-ok", "d": "2026-10-02"}]
    assert m.sedute_dal(sedute, "2026-10-01") == {"s-ok"}


# ---------------------------------------------------------------------------
# Query metadati
# ---------------------------------------------------------------------------


def test_meta_incrementale_filtra_per_seduta(monkeypatch):
    """Con ``sedute`` la query non rilegge tutte le votazioni del graph."""
    m = _load_preprocess()
    catturato: list[str] = []

    def fake_query(sparql: str, timeout: int = 120):
        catturato.append(sparql)
        return []

    monkeypatch.setattr(m, "query", fake_query)
    m.fetch_votazioni_meta("http://dati.senato.it/votazioni-fasi-1/19",
                           {"http://dati.senato.it/sedutaassemblea/1"})

    assert len(catturato) == 1
    q = catturato[0]
    assert "?v osr:seduta ?s . FILTER(?s IN (<http://dati.senato.it/sedutaassemblea/1>))" in q
    assert "OPTIONAL { ?v osr:seduta ?s . }" not in q


def test_meta_full_senza_filtro(monkeypatch):
    """Senza ``sedute`` resta il comportamento full (OPTIONAL, nessun FILTER)."""
    m = _load_preprocess()
    catturato: list[str] = []
    monkeypatch.setattr(m, "query", lambda sparql, timeout=120: catturato.append(sparql) or [])
    m.fetch_votazioni_meta("http://dati.senato.it/votazioni-fasi-1/19")

    q = catturato[0]
    assert "OPTIONAL { ?v osr:seduta ?s . }" in q
    assert "FILTER(?s IN" not in q


# ---------------------------------------------------------------------------
# End-to-end offline: baseline + delta, con query contate
# ---------------------------------------------------------------------------


def _write_baseline(path: Path, data: str = "2026-11-01") -> None:
    import duckdb

    con = duckdb.connect()
    con.execute(f"""
        COPY (
          SELECT 'v-old' AS votazione, 1::BIGINT AS senatore_id, 'FAVOREVOLE' AS voto,
                 's-old' AS seduta, '19' AS legislatura, 'elettronica' AS tipo_votazione,
                 'approvato' AS esito,
                 1::INTEGER AS n_favorevoli, 0::INTEGER AS n_contrari,
                 0::INTEGER AS n_astenuti, 1::INTEGER AS n_votanti,
                 1::INTEGER AS n_presenti, 1::INTEGER AS n_maggioranza,
                 0::INTEGER AS n_congedo_missione, DATE '{data}' AS data
        ) TO '{path}' (FORMAT PARQUET)
    """)


def test_incremental_end_to_end_solo_nuove_sedute(tmp_path, monkeypatch):
    """Baseline presente → query solo sulle sedute nuove, merge vecchio+nuovo."""
    m = _load_preprocess()
    baseline = tmp_path / "senato_votazioni.parquet"
    _write_baseline(baseline, data="2026-11-01")

    sedute = [
        {"s": "s-old", "d": "2026-10-30"},
        {"s": "s-new", "d": "2026-11-18"},
    ]
    chiamate_meta: list[set[str] | None] = []

    monkeypatch.setattr(m, "fetch_sedute", lambda leg: sedute)

    def fake_meta(graph, sedute_filtrate=None):
        chiamate_meta.append(sedute_filtrate)
        if sedute_filtrate and "votazioni-fasi-1" in graph:
            return [{
                "v": "v-new", "seduta": "s-new", "legislatura": "19",
                "tipoVotazione": "elettronica", "esito": "approvato",
                "favorevoli": "1", "contrari": "0", "astenuti": "0",
                "votanti": "1", "presenti": "1", "maggioranza": "1",
                "congedoMissione": "0",
            }]
        return []

    monkeypatch.setattr(m, "fetch_votazioni_meta", fake_meta)

    def fake_voti(graph, votazioni):
        if "votazioni-fasi-1" in graph:
            return [{"v": "v-new", "sen": "http://dati.senato.it/senatore/123",
                     "p": m.OSR + "favorevole"}]
        return []

    monkeypatch.setattr(m, "fetch_voti_filtered", fake_voti)
    monkeypatch.setattr(sys, "argv", [
        "preprocess.py", "--legislature", "19", "--out", str(tmp_path), "--incremental",
    ])

    assert m.main() == 0

    # La query metadati ha visto SOLO la seduta nuova, non tutta la legislatura.
    assert chiamate_meta and all(s == {"s-new"} for s in chiamate_meta)

    import duckdb
    rows = duckdb.connect().execute(
        f"SELECT votazione, data FROM '{baseline}' ORDER BY votazione"
    ).fetchall()
    assert rows == [("v-new", date(2026, 11, 18)), ("v-old", date(2026, 11, 1))]


def test_incremental_senza_sedute_nuove_non_interroga_i_metadati(tmp_path, monkeypatch):
    """Nessuna seduta nuova → zero query metadati (prima erano una per graph)."""
    m = _load_preprocess()
    _write_baseline(tmp_path / "senato_votazioni.parquet", data="2026-11-19")

    monkeypatch.setattr(m, "fetch_sedute", lambda leg: [{"s": "s-old", "d": "2026-11-18"}])
    monkeypatch.setattr(
        m, "fetch_votazioni_meta",
        lambda *a, **k: pytest.fail("metadati interrogati senza sedute nuove"),
    )
    monkeypatch.setattr(sys, "argv", [
        "preprocess.py", "--legislature", "19", "--out", str(tmp_path), "--incremental",
    ])

    assert m.main() == 0


def test_incremental_graph_fallito_non_scrive_parquet_parziale(tmp_path, monkeypatch):
    """Un graph che fallisce rende il run invalido: niente merge parziale.

    Prima il graph fallito veniva saltato in silenzio: il merge avanzava
    max(data) e le votazioni mancanti non venivano più riprese.
    """
    m = _load_preprocess()
    baseline = tmp_path / "senato_votazioni.parquet"
    _write_baseline(baseline, data="2026-11-01")
    prima = baseline.read_bytes()

    monkeypatch.setattr(m, "fetch_sedute",
                        lambda leg: [{"s": "s-new", "d": "2026-11-18"}])
    monkeypatch.setattr(m, "fetch_votazioni_meta", lambda g, s=None: [{
        "v": "v-new", "seduta": "s-new", "legislatura": "19",
        "tipoVotazione": "elettronica", "esito": "approvato",
        "favorevoli": "1", "contrari": "0", "astenuti": "0", "votanti": "1",
        "presenti": "1", "maggioranza": "1", "congedoMissione": "0",
    }])
    monkeypatch.setattr(
        m, "fetch_voti_filtered",
        lambda g, v: (_ for _ in ()).throw(RuntimeError("WAF 403")),
    )
    monkeypatch.setattr(sys, "argv", [
        "preprocess.py", "--legislature", "19", "--out", str(tmp_path), "--incremental",
    ])

    assert m.main() == 1
    assert baseline.read_bytes() == prima
