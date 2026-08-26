"""Come Votano — disciplina di partito, ribelli e chi parla."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_mart, load_mart_flat

st.title("🗳️ Come Votano")
st.markdown("Disciplina di partito, ribelli del Parlamento e chi parla più spesso.")

try:
    df = load_mart("profilo_politico", "mart_profilo")
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

# -- Filtri ------------------------------------------------------------------

ramo = st.selectbox("Ramo", ["Tutti", "Camera", "Senato"], key="cv_ramo")
if ramo != "Tutti":
    df = df[df["ramo"] == ramo.lower()]

# -- KPI ---------------------------------------------------------------------

media = df["pct_col_gruppo"].mean()
ribelli = len(df[df["pct_col_gruppo"] < 90])

k1, k2, k3 = st.columns(3)
k1.metric("Fedeltà media", fmt_pct(media))
k2.metric("Ribelli (<90%)", ribelli)
k3.metric("Parlamentari", len(df))

st.markdown("---")

# -- I ribelli ---------------------------------------------------------------

st.subheader("🔥 I ribelli")

ribelli_df = df[df["pct_col_gruppo"] < 90].sort_values("pct_col_gruppo").head(20)

if not ribelli_df.empty:
    display = ribelli_df[["cognome", "nome", "ramo", "pct_col_gruppo", "n_voti", "n_contrari"]].copy()
    display.columns = ["Cognome", "Nome", "Ramo", "% Gruppo", "Voti", "Contrari"]
    st.dataframe(display, use_container_width=True, height=400)
else:
    st.info("Nessun parlamentare con fedeltà sotto il 90%.")

st.markdown("---")

# -- Coerenza vs Fedeltà -----------------------------------------------------

st.subheader("Coerenza vs Fedeltà al gruppo")

chart_scatter = (
    alt.Chart(df)
    .mark_circle(opacity=0.4, size=40)
    .encode(
        x=alt.X("pct_col_gruppo:Q", title="Fedeltà al gruppo %"),
        y=alt.Y("pct_coerente:Q", title="Coerenza %"),
        color=alt.Color(
            "ramo:N",
            scale=alt.Scale(domain=["camera", "senato"], range=["#3b82f6", "#f59e0b"]),
            title="Ramo",
        ),
        tooltip=["cognome", "nome", "pct_col_gruppo", "pct_coerente", "n_voti"],
    )
    .properties(height=400)
)
st.altair_chart(chart_scatter, width="stretch")

st.markdown("---")

# -- Chi parla più spesso ----------------------------------------------------

st.subheader("🎤 Chi parla più spesso in Camera")

try:
    df_top = load_mart_flat("camera_interventi", "mart_top_parlanti")
    df_profilo = load_mart("profilo_politico", "mart_profilo")

    # Join per avere nomi
    df_parlanti = pd.merge(
        df_top,
        df_profilo[["id_parlamentare", "cognome", "nome"]],
        left_on="deputato_id",
        right_on="id_parlamentare",
        how="left",
    )
    df_parlanti = df_parlanti.sort_values("n_interventi", ascending=False).head(15)

    display_parlanti = df_parlanti[["cognome", "nome", "n_interventi"]].copy()
    display_parlanti.columns = ["Cognome", "Nome", "Interventi"]
    st.dataframe(display_parlanti, use_container_width=True, hide_index=True)

    # Grafico top 10
    chart_parlanti = (
        alt.Chart(df_parlanti.head(10))
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#6366f1")
        .encode(
            x=alt.X("n_interventi:Q", title="N. interventi"),
            y=alt.Y("cognome:N", title="", sort="-x"),
            tooltip=["cognome", "nome", "n_interventi"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_parlanti, width="stretch")
except Exception as e:
    st.info(f"Dati interventi non disponibili: {e}")

st.caption("Dati: Camera dei Deputati, Senato della Repubblica · XIX legislatura · CC BY 4.0")
