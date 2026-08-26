"""Come Votano — disciplina di partito e ribelli."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_pct, load_mart

st.title("🗳️ Come Votano")
st.markdown("Disciplina di partito, fedeltà al gruppo e i \"ribelli\" del Parlamento.")

try:
    df = load_mart("profilo_politico", "mart_profilo")
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

# ── Filtri ──────────────────────────────────────────────────────────────────

ramo = st.selectbox("Ramo", ["Tutti", "Camera", "Senato"], key="cv_ramo")
if ramo != "Tutti":
    df = df[df["ramo"] == ramo.lower()]

# ── Distribuzione fedeltà ──────────────────────────────────────────────────

st.subheader("Distribuzione fedeltà al gruppo")

chart_dist = (
    alt.Chart(df)
    .mark_bar(color="#6366f1")
    .encode(
        x=alt.X("pct_col_gruppo:Q", bin=alt.Bin(maxbins=30), title="% Fedeltà al gruppo"),
        y=alt.Y("count():Q", title="N. parlamentari"),
        tooltip=[alt.Tooltip("count():Q", title="N.")],
    )
    .properties(height=250)
)
st.altair_chart(chart_dist, width="stretch")

media = df["pct_col_gruppo"].mean()
st.info(f"📊 Fedeltà media: **{fmt_pct(media)}** — {len(df)} parlamentari")

st.markdown("---")

# ── I ribelli ──────────────────────────────────────────────────────────────

st.subheader("🔥 I ribelli (fedeltà < 90%)")

ribelli = df[df["pct_col_gruppo"] < 90].sort_values("pct_col_gruppo").head(20)

if not ribelli.empty:
    display = ribelli[["cognome", "nome", "ramo", "pct_col_gruppo", "n_voti", "n_contrari"]].copy()
    display.columns = ["Cognome", "Nome", "Ramo", "% Gruppo", "Voti", "Contrari"]
    st.dataframe(display, use_container_width=True, height=400)
else:
    st.info("Nessun parlamentare con fedeltà sotto il 90%.")

st.markdown("---")

# ── Coerenza vs Fedeltà ───────────────────────────────────────────────────

st.subheader("Coerenza vs Fedeltà al gruppo")

chart_scatter = (
    alt.Chart(df)
    .mark_circle(size=30, opacity=0.5)
    .encode(
        x=alt.X("pct_col_gruppo:Q", title="Fedeltà al gruppo %"),
        y=alt.Y("pct_coerente:Q", title="Coerenza %"),
        color=alt.Color("ramo:N", scale=alt.Scale(domain=["camera", "senato"], range=["#3b82f6", "#f59e0b"])),
        tooltip=["cognome", "nome", "pct_col_gruppo", "pct_coerente", "n_voti"],
    )
    .properties(height=350)
)
st.altair_chart(chart_scatter, width="stretch")

st.caption("Dati: Camera dei Deputati, Senato della Repubblica · XIX legislatura · CC BY 4.0")
