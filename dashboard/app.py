#!/usr/bin/env python3
"""
Open Politica · Dashboard Streamlit
La politica italiana in dati aperti: chi vota, come vota, cosa decide.
"""

import streamlit as st

st.set_page_config(
    page_title="Open Politica · Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "": [
        st.Page("pages/01_Panoramica.py", title="Osservatorio", icon="📊", default=True),
    ],
    "Parlamento": [
        st.Page("pages/02_Rappresentante.py", title="Il Tuo Rappresentante", icon="👤"),
        st.Page("pages/03_Come_Votano.py", title="Come Votano", icon="🗳️"),
    ],
    "Elezioni": [
        st.Page("pages/04_Elezioni.py", title="Affluenza & Trend", icon="🗳️"),
    ],
    "Legislazione": [
        st.Page("pages/05_DDL.py", title="DDL & Governo", icon="📜"),
    ],
}

pg = st.navigation(pages, position="sidebar")

st.sidebar.markdown("---")
st.sidebar.caption("Dati: Camera, Senato, MIMIT · [dataciviclab/open-politica](https://github.com/dataciviclab/open-politica)")
st.sidebar.caption("[DataCivicLab](https://dataciviclab.org/) · CC BY 4.0")

pg.run()
