"""Elezioni — politiche, affluenza, trend, confronti."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_mart_flat

st.title("🗳️ Elezioni")
st.markdown("Risultati elettorali, affluenza e trend storici.")

tab_pol, tab_aff, tab_trend = st.tabs(["Politiche", "Affluenza", "Trend"])

# -- Tab Politiche -----------------------------------------------------------

with tab_pol:
    st.subheader("Risultati elezioni politiche")
    st.caption("Dati dal 1948 — voto per lista/comune")

    try:
        df_pol = load_mart_flat("elezioni_politiche", "mart_voti_elezioni_politiche", year=2022)
    except Exception as e:
        st.error(f"Errore: {e}")
        st.stop()

    # Filtri
    col_a, col_b = st.columns(2)
    with col_a:
        camera_senato = st.selectbox("Camera/Senato", ["Tutti", "Camera", "Senato"], key="pol_cs")
    with col_b:
        anni_disponibili = sorted(df_pol["anno"].unique(), reverse=True)
        anno_pol = st.selectbox("Anno", anni_disponibili, key="pol_anno")

    df_f = df_pol[df_pol["anno"] == anno_pol]
    if camera_senato == "Camera":
        df_f = df_f[df_f["camera_senato"] == "C"]
    elif camera_senato == "Senato":
        df_f = df_f[df_f["camera_senato"] == "S"]

    # Top liste per voti
    top_liste = (
        df_f.groupby("lista", as_index=False)
        .agg(voti=("tot_voti_lista", "sum"))
        .sort_values("voti", ascending=False)
        .head(15)
    )

    if not top_liste.empty:
        chart_liste = (
            alt.Chart(top_liste)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("voti:Q", title="Voti totali", axis=alt.Axis(format="~s")),
                y=alt.Y("lista:N", title="", sort="-x"),
                tooltip=["lista", alt.Tooltip("voti:Q", format=",.0f")],
            )
            .properties(height=400)
        )
        st.altair_chart(chart_liste, width="stretch")
    else:
        st.info("Nessun dato per questo anno.")

# -- Tab Affluenza -----------------------------------------------------------

with tab_aff:
    st.subheader("Affluenza alle urne")

    try:
        df_aff = load_mart_flat("elezioni_voto", "mart_sintesi")
    except Exception as e:
        st.error(f"Errore: {e}")
        st.stop()

    tipo = st.selectbox("Tipo elezione", ["Tutti"] + sorted(df_aff["tipo_elezione"].unique().tolist()), key="aff_tipo")
    if tipo != "Tutti":
        df_aff = df_aff[df_aff["tipo_elezione"] == tipo]

    k1, k2, k3 = st.columns(3)
    k1.metric("Affluenza media", fmt_pct(df_aff["affluenza_pct"].mean()))
    k2.metric("Anni coperti", f"{int(df_aff['anno'].min())}–{int(df_aff['anno'].max())}")
    k3.metric("Regioni", df_aff["regione"].nunique())

    # Trend affluenza
    if tipo != "Tutti":
        trend = df_aff.groupby("anno", as_index=False).agg(affluenza=("affluenza_pct", "mean"))
    else:
        trend = df_aff.groupby(["anno", "tipo_elezione"], as_index=False).agg(affluenza=("affluenza_pct", "mean"))

    chart_trend = (
        alt.Chart(trend)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("anno:O", title="Anno"),
            y=alt.Y("affluenza:Q", title="Affluenza %", axis=alt.Axis(format=".1f")),
            color=alt.Color("tipo_elezione:N" if "tipo_elezione" in trend.columns else alt.value("#6366f1"), legend=None if tipo != "Tutti" else alt.Legend(title="Tipo")),
            tooltip=["anno", alt.Tooltip("affluenza:Q", format=".1f")],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_trend, width="stretch")

    # Affluenza per regione
    st.subheader("Affluenza per regione")
    anno_sel = st.selectbox("Anno", sorted(df_aff["anno"].unique(), reverse=True), key="aff_anno")
    df_anno = df_aff[df_aff["anno"] == anno_sel]
    if not df_anno.empty:
        by_reg = df_anno.groupby("regione", as_index=False).agg(affluenza=("affluenza_pct", "mean")).sort_values("affluenza", ascending=False)
        chart_reg = (
            alt.Chart(by_reg)
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

# -- Tab Trend ---------------------------------------------------------------

with tab_trend:
    st.subheader("Trend affluenza per comune")
    st.caption("I comuni che votano di più o di meno nel tempo")

    try:
        df_trend = load_mart_flat("elezioni_voto", "mart_trend")
    except Exception as e:
        st.error(f"Errore: {e}")
        st.stop()

    # Top comuni per variazione
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Comuni con più calo affluenza**")
        bottom = df_trend.nsmallest(10, "var_assoluta_punti")[["comune", "provincia", "n_tornate", "prima_affluenza_pct", "ultima_affluenza_pct", "var_assoluta_punti"]]
        st.dataframe(bottom, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Comuni con più crescita affluenza**")
        top = df_trend.nlargest(10, "var_assoluta_punti")[["comune", "provincia", "n_tornate", "prima_affluenza_pct", "ultima_affluenza_pct", "var_assoluta_punti"]]
        st.dataframe(top, use_container_width=True, hide_index=True)

st.caption("Dati: Camera, Senato, Ministero dell'Interno · CC BY 4.0")
