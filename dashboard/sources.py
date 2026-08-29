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
