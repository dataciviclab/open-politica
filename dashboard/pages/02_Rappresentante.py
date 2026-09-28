"""Il Tuo Rappresentante — ricerca, filtri e scheda profilo."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import fmt_num, fmt_pct, load_profilo

st.title("👤 Il Tuo Rappresentante")
st.markdown("Cerca un parlamentare e scopri come vota, cosa comanda, di cosa si occupa.")


try:
    df = load_profilo()
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
    df_f = df_f[df_f["in_governo"]]
if solo_presidente:
    df_f = df_f[df_f["presidente_commissione"]]
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

# -- URL scheda (funzionante) ------------------------------------------------

def _scheda_url(person):
    """Costruisce URL scheda funzionante da id_parlamentare e ramo."""
    pid = person.get("id_parlamentare")
    if pid is None or pd.isna(pid):
        return None
    pid = int(pid)
    ramo = person.get("ramo", "")
    if ramo == "camera":
        return f"https://dati.camera.it/ocd/deputato.rdf/d{pid}_19"
    elif ramo == "senato":
        return f"http://dati.senato.it/senatore/{pid}"
    return None

# -- Testata: foto + info ----------------------------------------------------

foto_url = person.get("foto_url")
has_foto = foto_url and pd.notna(foto_url)

if has_foto:
    col_img, col_info = st.columns([1, 3])
    with col_img:
        st.image(str(foto_url), width=100)
    with col_info:
        st.markdown(f"### {person['cognome']} {person['nome']}")
        _meta = []
        _meta.append(person["ramo"].title())
        if person.get("gender") and pd.notna(person["gender"]):
            _meta.append(person["gender"].title())
        if person.get("luogo_nascita") and pd.notna(person["luogo_nascita"]):
            _meta.append(f"Nato/a a {person['luogo_nascita']}")
        url = _scheda_url(person)
        if url:
            _meta.append(f"[Scheda ufficiale]({url})")
        st.caption(" · ".join(_meta))
else:
    st.markdown(f"### {person['cognome']} {person['nome']}")
    _meta = [person["ramo"].title()]
    if person.get("gender") and pd.notna(person["gender"]):
        _meta.append(person["gender"].title())
    url = _scheda_url(person)
    if url:
        _meta.append(f"[Scheda ufficiale]({url})")
    st.caption(" · ".join(_meta))

# -- Metriche principali -----------------------------------------------------

k1, k2, k3, k4 = st.columns(4)
k1.metric("Voti espressi", fmt_num(person["n_voti"]))
k2.metric("Fedeltà al gruppo", fmt_pct(person["pct_col_gruppo"], signed=False))
k3.metric("Coerenza", fmt_pct(person["pct_coerente"], signed=False))
k4.metric("Interventi in aula", fmt_num(person.get("n_interventi", 0) or 0))

st.markdown("---")

# -- Biografia ---------------------------------------------------------------

bio = person.get("biografia")
if bio and pd.notna(bio):
    st.markdown(f"> {bio}")
    st.markdown("")

# -- Come vota ---------------------------------------------------------------

st.subheader("Come vota")

col_vote, col_donut = st.columns([1, 1])

with col_vote:
    c1, c2, c3 = st.columns(3)
    c1.metric("Favorevoli", fmt_num(person["n_favorevoli"]))
    c2.metric("Contrari", fmt_num(person["n_contrari"]))
    c3.metric("Astenuti", fmt_num(person["n_astenuti"]))

with col_donut:
    voti_df = pd.DataFrame({
        "tipo": ["Favorevoli", "Contrari", "Astenuti"],
        "n": [person["n_favorevoli"], person["n_contrari"], person["n_astenuti"]],
    })
    chart_voti = (
        alt.Chart(voti_df)
        .mark_arc(innerRadius=40, outerRadius=70)
        .encode(
            theta=alt.Theta("n:Q"),
            color=alt.Color("tipo:N", scale=alt.Scale(
                domain=["Favorevoli", "Contrari", "Astenuti"],
                range=["#10b981", "#ef4444", "#6b7280"]
            )),
            tooltip=["tipo", alt.Tooltip("n:Q", format=",.0f")],
        )
        .properties(height=180, width=180)
    )
    st.altair_chart(chart_voti, use_container_width=False)

st.markdown("---")

# -- Cariche e incarichi ------------------------------------------------------

st.subheader("Cariche e incarichi")

col_left, col_right = st.columns(2)

with col_left:
    if person["in_governo"]:
        st.info("🏛️ In Governo")
    n_comm = person["n_commissioni_attuali"] if pd.notna(person["n_commissioni_attuali"]) else 0
    st.metric("Commissioni", int(n_comm))
    if person["presidente_commissione"]:
        st.success("🎯 Presidente di commissione")
    comm_text = person.get("commissioni_attuali")
    if comm_text and pd.notna(comm_text) and str(comm_text).strip():
        with st.expander("Vedi commissioni", expanded=False):
            st.text(comm_text)

with col_right:
    st.metric("Relatore", fmt_num(person["n_relatori"]))
    st.metric("Anni relatore", fmt_num(person["anni_relatore"]))

st.caption("Dati: Camera dei Deputati, Senato della Repubblica · XIX legislatura · CC BY 4.0")
