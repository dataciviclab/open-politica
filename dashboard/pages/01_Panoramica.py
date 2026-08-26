"""Osservatorio — KPI del Parlamento italiano."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_kpi

st.title("🏛️ Osservatorio Parlamento")
st.markdown("La \"pagella\" del Parlamento italiano — dati della XIX legislatura.")

# ── Carica KPI ──────────────────────────────────────────────────────────────

try:
    df_kpi = load_kpi()
except Exception as e:
    st.error(f"Errore caricamento KPI: {e}")
    st.stop()

if df_kpi.empty:
    st.info("Nessun KPI disponibile.")
    st.stop()

# ── KPI principali ──────────────────────────────────────────────────────────

# Trova i KPI chiave
kpi_map = {}
for _, row in df_kpi.iterrows():
    kpi_map[row["kpi"]] = row["valore"]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("DDL presentati", fmt_num(kpi_map.get("ddl_presentati", 0)))
k2.metric("DDL approvati", fmt_num(kpi_map.get("ddl_approvati", 0)))
k3.metric("% Approvati", fmt_pct(kpi_map.get("pct_approvati_governativi", 0)))
k4.metric("Giorni iter medio", f"{kpi_map.get('giorni_iter_medio', 0):.0f}")
k5.metric("% Leggi governo", fmt_pct(kpi_map.get("pct_iniziativa_governativa", 0)))

st.markdown("---")

# ── Trend votazioni Camera ──────────────────────────────────────────────────

st.subheader("📈 Trend votazioni Camera")

votazioni = df_kpi[
    (df_kpi["dimensione"] == "votazioni") &
    (df_kpi["fonte"] == "camera_votazioni") &
    (df_kpi["kpi"] == "n_votazioni")
].copy()

if not votazioni.empty:
    votazioni["periodo"] = votazioni["periodo"].astype(str)
    chart_vot = (
        alt.Chart(votazioni)
        .mark_line(point=True, color="#6366f1", strokeWidth=2)
        .encode(
            x=alt.X("periodo:O", title="Anno"),
            y=alt.Y("valore:Q", title="N. votazioni"),
            tooltip=["periodo", alt.Tooltip("valore:Q", format=",.0f")],
        )
        .properties(height=250)
    )
    st.altair_chart(chart_vot, width="stretch")

# ── Fiducie per anno ───────────────────────────────────────────────────────

st.subheader("🗳️ Voti di fiducia per anno")

fiducia = df_kpi[
    (df_kpi["dimensione"] == "fiducia") &
    (df_kpi["kpi"] == "n_fiducia")
].copy()

if not fiducia.empty:
    fiducia["periodo"] = fiducia["periodo"].astype(str)
    chart_fid = (
        alt.Chart(fiducia)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#f59e0b")
        .encode(
            x=alt.X("periodo:O", title="Anno"),
            y=alt.Y("valore:Q", title="N. fiducie"),
            tooltip=["periodo", alt.Tooltip("valore:Q", format=",.0f")],
        )
        .properties(height=250)
    )
    st.altair_chart(chart_fid, width="stretch")

# ── Partecipazione ai voti ─────────────────────────────────────────────────

st.subheader("👥 Partecipazione ai voti Camera")

partec = df_kpi[
    (df_kpi["dimensione"] == "partecipazione") &
    (df_kpi["kpi"] == "pct_voti_espressi")
].copy()

if not partec.empty:
    partec["periodo"] = partec["periodo"].astype(str)
    chart_part = (
        alt.Chart(partec)
        .mark_line(point=True, color="#10b981", strokeWidth=2)
        .encode(
            x=alt.X("periodo:O", title="Anno"),
            y=alt.Y("valore:Q", title="% Voti espressi", axis=alt.Axis(format=".0f")),
            tooltip=["periodo", alt.Tooltip("valore:Q", format=".1f")],
        )
        .properties(height=250)
    )
    st.altair_chart(chart_part, width="stretch")

# ── Rappresentanza storica ─────────────────────────────────────────────────

st.subheader("📉 Donne in Parlamento — storia")

donne = df_kpi[
    (df_kpi["dimensione"] == "rappresentanza") &
    (df_kpi["kpi"] == "pct_donne") &
    (df_kpi["fonte"] == "camera_deputati")
].copy()

if not donne.empty:
    donne = donne.sort_values("periodo")
    chart_donne = (
        alt.Chart(donne)
        .mark_line(point=True, color="#ec4899", strokeWidth=2)
        .encode(
            x=alt.X("periodo:N", title="Legislatura"),
            y=alt.Y("valore:Q", title="% Donne", axis=alt.Axis(format=".1f")),
            tooltip=["periodo", alt.Tooltip("valore:Q", format=".1f")],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_donne, width="stretch")

st.caption("Dati: Camera dei Deputati, Senato della Repubblica · XIX legislatura · CC BY 4.0")
