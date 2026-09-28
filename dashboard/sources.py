"""Fonti dati per la dashboard Open Politica.

Wrappa lab_connectors.duckdb.queries con @st.cache_data.
Prefix: "open-politica/" (tutti i dataset pubblicati sotto questa subdirectory).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from lab_connectors.duckdb.queries import (
    load_mart_table as _load_mart_table,
)
from lab_connectors.registry import load_registry
from lab_connectors.formatters import fmt_eur, fmt_num, fmt_pct

PREFIX = "open-politica/"
YEARS = list(range(2022, 2027))  # 2022–2026

_registry = load_registry(Path(__file__).parent.parent / "registry" / "registry.json")


def get_registry():
    return _registry


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int = 2026):
    """Carica un singolo mart table da GCS (cached 1h)."""
    return _load_mart_table(slug, table, year, prefix=PREFIX)


@st.cache_data(ttl=3600, show_spinner=False)
def load_kpi(dimensione: str = None, year: int = 2026):
    """Carica KPI dall'osservatorio, filtrato per dimensione."""
    df = load_mart("osservatorio_parlamento", "mart_kpi", year)
    if dimensione:
        df = df[df["dimensione"] == dimensione]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_profilo(year: int = 2026):
    """Carica profilo parlamentare con anagrafiche Camera/Senato merge."""
    import pandas as pd
    from lab_connectors.duckdb.queries import load_clean

    df = load_mart("profilo_politico", "mart_profilo", year)

    # Camera: foto, biografia, scheda_url, gender
    try:
        cam = load_clean("camera_deputati_legislature", [year], prefix=PREFIX)
        cam = cam.drop_duplicates(subset=["persona_id"], keep="first")
        cam_cols = cam[["persona_id", "gender", "biografia", "foto_url", "scheda_url"]].copy()
        cam_cols["persona_id"] = cam_cols["persona_id"].astype("Int64")
        df = df.merge(cam_cols, on="persona_id", how="left")
    except Exception:
        pass

    # Senato: data_nascita, luogo_nascita
    try:
        sen = load_clean("senato_anagrafica", [year], prefix=PREFIX)
        sen = sen.drop_duplicates(subset=["senatore_id"], keep="first")
        sen_cols = sen[["senatore_id", "data_nascita", "luogo_nascita"]].copy()
        sen_cols = sen_cols.rename(columns={"senatore_id": "id_parlamentare"})
        df = df.merge(sen_cols, on="id_parlamentare", how="left")
    except Exception:
        pass

    return df
