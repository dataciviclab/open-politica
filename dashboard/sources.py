"""Fonti dati per la dashboard Open Politica.

Wrappa lab_connectors.duckdb.queries con @st.cache_data.
Prefix: "open-politica/" (tutti i dataset pubblicati sotto questa subdirectory).
"""

from __future__ import annotations

import streamlit as st

from lab_connectors.duckdb.queries import (
    load_mart_table as _load_mart_table,
)

PREFIX = "open-politica/"


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(slug: str, table: str, year: int = 2026):
    """Carica un singolo mart table da GCS (cached 1h)."""
    return _load_mart_table(slug, table, year, prefix=PREFIX)


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_flat(slug: str, table: str, year: int = 2026):
    """Carica un mart flat da GCS.

    URL: {PREFIX}{slug}/{year}/{table}.parquet
    """
    import duckdb

    url = f"https://storage.googleapis.com/dataciviclab-mart/{PREFIX}{slug}/{year}/{table}.parquet"
    with duckdb.connect() as con:
        return con.sql(f"SELECT * FROM read_parquet('{url}')").df()


@st.cache_data(ttl=3600, show_spinner=False)
def load_kpi(dimensione: str = None):
    """Carica KPI dall'osservatorio, filtrato per dimensione."""
    df = load_mart_flat("osservatorio_parlamento", "mart_kpi")
    if dimensione:
        df = df[df["dimensione"] == dimensione]
    return df


# ── Formattazione ───────────────────────────────────────────────────────────


def fmt_eur(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"€{value / 1_000_000_000:,.1f} mld"
    if abs(value) >= 1_000_000:
        return f"€{value / 1_000_000:,.1f} M"
    return f"€{value:,.0f}"


def fmt_num(value: float) -> str:
    return f"{value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"
