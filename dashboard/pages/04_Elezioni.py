"""Elezioni — affluenza, trend, confronti."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_mart_flat

st.title("🗳️ Elezioni")
st.markdown("Affluenza alle urne, trend storici e confronti tra territori.")

# ── Carica dati ─────────────────────────────────────────────────────────────

try:
    df = load_mart_flat("elezioni_voto", "mart_sintesi")
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

# ── Filtri ──────────────────────────────────────────────────────────────────

tipi = ["Tutti"] + sorted(df["tipo_elezione"].unique().tolist())
tipo = st.selectbox("Tipo elezione", tipi, key="el_tipo")

if tipo != "Tutti":
    df = df[df["tipo_elezione"] == tipo]

# ── KPI ────────────────────────────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)
k1.metric("Elezioni totali", fmt_num(len(df)))
k2.metric("Affluenza media", fmt_pct(df["affluenza_pct"].mean()))
k3.metric("Anni coperti", f"{int(df['anno'].min())}–{int(df['anno'].max())}")
k4.metric("Regioni", df["regione"].nunique())

st.markdown("---")

# ── Trend affluenza ────────────────────────────────────────────────────────

st.subheader("📈 Trend affluenza")

if tipo != "Tutti":
    trend = df.groupby("anno", as_index=False).agg(affluenza=("affluenza_pct", "mean"))
    chart_trend = (
        alt.Chart(trend)
        .mark_line(point=True, color="#6366f1", strokeWidth=2)
        .encode(
            x=alt.X("anno:O", title="Anno"),
            y=alt.Y("affluenza:Q", title="Affluenza %", axis=alt.Axis(format=".1f")),
            tooltip=["anno", alt.Tooltip("affluenza:Q", format=".1f")],
        )
        .properties(height=250)
    )
    st.altair_chart(chart_trend, width="stretch")
else:
    trend = df.groupby(["anno", "tipo_elezione"], as_index=False).agg(affluenza=("affluenza_pct", "mean"))
    chart_trend = (
        alt.Chart(trend)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("anno:O", title="Anno"),
            y=alt.Y("affluenza:Q", title="Affluenza %", axis=alt.Axis(format=".1f")),
            color=alt.Color("tipo_elezione:N", title="Tipo"),
            tooltip=["tipo_elezione", "anno", alt.Tooltip("affluenza:Q", format=".1f")],
        )
        .properties(height=250)
    )
    st.altair_chart(chart_trend, width="stretch")

st.markdown("---")

# ── Affluenza per regione ──────────────────────────────────────────────────

st.subheader("🗺️ Affluenza per regione")

anno_max = int(df["anno"].max())
anno_sel = st.selectbox("Anno", sorted(df["anno"].unique(), reverse=True), key="el_anno")

df_anno = df[df["anno"] == anno_sel]

if not df_anno.empty:
    by_regione = df_anno.groupby("regione", as_index=False).agg(affluenza=("affluenza_pct", "mean"))
    by_regione = by_regione.sort_values("affluenza", ascending=False)

    chart_reg = (
        alt.Chart(by_regione)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("affluenza:Q", title="Affluenza %"),
            y=alt.Y("regione:N", title="", sort="-x"),
            color=alt.Color("affluenza:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["regione", alt.Tooltip("affluenza:Q", format=".1f")],
        )
        .properties(height=500)
    )
    st.altair_chart(chart_reg, width="stretch")

st.caption("Dati: Ministero dell'Interno (Eligendo/DAIT) · CC BY 4.0")
