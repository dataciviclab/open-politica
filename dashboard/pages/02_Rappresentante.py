"""Il Tuo Rappresentante — ricerca, filtri e scheda profilo."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_mart

st.title("👤 Il Tuo Rappresentante")
st.markdown("Cerca un parlamentare e scopri come vota, cosa comanda, di cosa si occupa.")

try:
    df = load_mart("profilo_politico", "mart_profilo")
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

# -- Filtri ------------------------------------------------------------------

with st.expander("Filtri avanzati", expanded=False):
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        ramo = st.selectbox("Ramo", ["Tutti", "Camera", "Senato"], key="rep_ramo")
    with col_f2:
        solo_governo = st.checkbox("Solo in governo", key="rep_gov")
    with col_f3:
        solo_presidente = st.checkbox("Solo presidenti commissione", key="rep_pres")

    fed_min, fed_max = st.slider(
        "Range fedeltà al gruppo (%)",
        min_value=0, max_value=100, value=(0, 100),
        key="rep_fedelta"
    )

# Applica filtri
df_f = df.copy()
if ramo != "Tutti":
    df_f = df_f[df_f["ramo"] == ramo.lower()]
if solo_governo:
    df_f = df_f[df_f["in_governo"] == True]
if solo_presidente:
    df_f = df_f[df_f["presidente_commissione"] == True]
if fed_min > 0 or fed_max < 100:
    df_f = df_f[(df_f["pct_col_gruppo"] >= fed_min) & (df_f["pct_col_gruppo"] <= fed_max)]

st.caption(f"{len(df_f)} parlamentari dopo i filtri")

# -- Ricerca testo -----------------------------------------------------------

query = st.text_input("Cerca per nome o cognome", placeholder="es. Calenda, Gelmini, Soumahoro...")

if query:
    q = query.strip().upper()
    mask = (df_f["nome"].str.upper().str.contains(q, na=False) |
            df_f["cognome"].str.upper().str.contains(q, na=False))
    results = df_f[mask]
else:
    results = df_f

if results.empty:
    st.info("Nessun risultato trovato.")
    st.stop()

# -- Selezione ---------------------------------------------------------------

if len(results) == 1:
    person = results.iloc[0]
else:
    options = [f"{r['cognome']} {r['nome']} ({r['ramo']})" for _, r in results.iterrows()]
    selected = st.selectbox(f"{len(results)} risultati — seleziona:", options)
    idx = options.index(selected)
    person = results.iloc[idx]

# -- Scheda ------------------------------------------------------------------

st.markdown(f"## {person['cognome']} {person['nome']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ramo", person["ramo"].title())
col2.metric("Voti espressi", fmt_num(person["n_voti"]))
col3.metric("Fedeltà al gruppo", fmt_pct(person["pct_col_gruppo"]))
col4.metric("Coerenza", fmt_pct(person["pct_coerente"]))

st.markdown("---")

# -- Come vota ---------------------------------------------------------------

st.subheader("Come vota")

col_a, col_b, col_c = st.columns(3)
col_a.metric("Favorevoli", fmt_num(person["n_favorevoli"]))
col_b.metric("Contrari", fmt_num(person["n_contrari"]))
col_c.metric("Astenuti", fmt_num(person["n_astenuti"]))

voti_df = pd.DataFrame({
    "tipo": ["Favorevoli", "Contrari", "Astenuti"],
    "n": [person["n_favorevoli"], person["n_contrari"], person["n_astenuti"]],
})
chart_voti = (
    alt.Chart(voti_df)
    .mark_arc(innerRadius=50)
    .encode(
        theta=alt.Theta("n:Q"),
        color=alt.Color("tipo:N", scale=alt.Scale(
            domain=["Favorevoli", "Contrari", "Astenuti"],
            range=["#10b981", "#ef4444", "#6b7280"]
        )),
        tooltip=["tipo", alt.Tooltip("n:Q", format=",.0f")],
    )
    .properties(height=200)
)
st.altair_chart(chart_voti, width="stretch")

st.markdown("---")

# -- Cariche e incarichi ------------------------------------------------------

st.subheader("Cariche e incarichi")

col_x, col_y = st.columns(2)

with col_x:
    if person["in_governo"]:
        st.info("🏛️ **In Governo**")
    st.metric("Commissioni", person["n_commissioni_attuali"])
    if person["presidente_commissione"]:
        st.info("🎯 Presidente di commissione")
    if person["commissioni_attuali"] and pd.notna(person["commissioni_attuali"]):
        with st.expander("Commissioni", expanded=False):
            st.text(person["commissioni_attuali"])

with col_y:
    st.metric("Relatore", fmt_num(person["n_relatori"]))
    st.metric("Anni relatore", fmt_num(person["anni_relatore"]))
    st.metric("Interventi in aula", fmt_num(person["n_interventi"]))

st.caption("Dati: Camera dei Deputati, Senato della Repubblica · XIX legislatura · CC BY 4.0")
