"""Sindacato Ispettivo — interrogazioni, interpellanze, mozioni del Senato."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, load_mart

st.title("🔍 Sindacato Ispettivo")
st.markdown("Interrogazioni, interpellanze e mozioni — il Senato controlla il governo.")

try:
    df_sintesi = load_mart("senato_sindisp", "mart_sintesi", year=19)
    df_senatori = load_mart("senato_sindisp", "mart_per_senatore", year=19)
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

if df_sintesi.empty:
    st.info("Nessun dato disponibile.")
    st.stop()

# -- KPI principali ----------------------------------------------------------

st.subheader("📊 XIX Legislatura")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Atti totali", fmt_num(df_sintesi["n_atti"].sum()))
k2.metric("Interrogazioni", fmt_num(df_sintesi[df_sintesi["tipo"] == "Interrogazione"]["n_atti"].sum()))
k3.metric("Mozioni", fmt_num(df_sintesi[df_sintesi["tipo"] == "Mozione"]["n_atti"].sum()))
k4.metric("Senatori coinvolti", fmt_num(len(df_senatori)))

st.markdown("---")

# -- Distribuzione per tipo --------------------------------------------------

st.subheader("📋 Distribuzione per tipo")

tipo_chart = (
    alt.Chart(df_sintesi)
    .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    .encode(
        x=alt.X("tipo:N", title="Tipo", sort="-y"),
        y=alt.Y("n_atti:Q", title="N. atti"),
        color=alt.Color("tipo:N", legend=None, scale=alt.Scale(
            domain=["Interrogazione", "Mozione", "Interpellanza",
                    "Risoluzione in Assemblea", "Risoluzione autonoma in commissione"],
            range=["#6366f1", "#f59e0b", "#10b981", "#ec4899", "#8b5cf6"]
        )),
        tooltip=["tipo", alt.Tooltip("n_atti:Q", format=",.0f"), alt.Tooltip("n_senatori:Q", format=",.0f")],
    )
    .properties(height=250)
)
st.altair_chart(tipo_chart, width="stretch")

st.markdown("---")

# -- Top 20 senatori ---------------------------------------------------------

st.subheader("🏆 Top 20 senatori per atti presentati")

top20 = df_senatori.nlargest(20, "n_atti")[["presentatore", "n_atti", "n_tipi", "primo_atto", "ultimo_atto"]]
top20 = top20.reset_index(drop=True)
top20.index = top20.index + 1
top20.columns = ["Senatore", "Atti", "Tipi", "Dal", "Al"]

st.dataframe(top20, use_container_width=True, hide_index=False)

st.markdown("---")

# -- Atti per senatore (distribuzione) --------------------------------------

st.subheader("📈 Distribuzione atti per senatore")

n_bins = st.slider("Numero bin", min_value=10, max_value=50, value=25, key="sindisp_bins")

chart_hist = (
    alt.Chart(df_senatori)
    .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2, color="#6366f1")
    .encode(
        x=alt.X("n_atti:Q", bin=alt.Bin(maxbins=n_bins), title="N. atti presentati"),
        y=alt.Y("count():Q", title="N. senatori"),
        tooltip=[alt.Tooltip("n_atti:Q", bin=True), alt.Tooltip("count():Q")],
    )
    .properties(height=250)
)
st.altair_chart(chart_hist, width="stretch")

st.caption("Dati: Senato della Repubblica · XIX legislatura · Fonte: dati.senato.it · CC BY 3.0")
