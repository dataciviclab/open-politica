"""DDL & Governo — decreti-legge e macchina legislativa."""

import altair as alt
import streamlit as st

from sources import load_mart

st.title("📜 DDL & Governo")
st.markdown("La macchina legislativa: decreti-legge, conversioni, tempi medi.")

# ── Carica dati ─────────────────────────────────────────────────────────────

try:
    df = load_mart("decreti_legge", "mart_sintesi")
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

# ── KPI ────────────────────────────────────────────────────────────────────

latest = df[df["anno"] == df["anno"].max()].iloc[0] if not df.empty else None

if latest is not None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("DDL presentati", int(latest["n_dl"]))
    k2.metric("Convertiti", int(latest["n_convertiti"]))
    k3.metric("Decaduti", int(latest["n_decaduti"]))
    k4.metric("Giorni media", f"{latest['giorni_conversione_medio']:.0f}")

    st.markdown("---")

# ── Trend DDL per anno ─────────────────────────────────────────────────────

st.subheader("📈 Trend DDL per anno")

df_sorted = df.sort_values("anno")

chart_dl = (
    alt.Chart(df_sorted)
    .mark_bar()
    .encode(
        x=alt.X("anno:O", title="Anno"),
        y=alt.Y("n_dl:Q", title="N. DDL"),
        color=alt.Color(
            "anno:O",
            scale=alt.Scale(range=["#6366f1"] * len(df)),
            legend=None,
        ),
        tooltip=["anno", alt.Tooltip("n_dl:Q", title="DDL"), alt.Tooltip("n_convertiti:Q", title="Convertiti")],
    )
    .properties(height=250)
)
st.altair_chart(chart_dl, width="stretch")

# ── Tasso di conversione ──────────────────────────────────────────────────

st.subheader("📊 Tasso di conversione")

chart_conv = (
    alt.Chart(df_sorted)
    .mark_line(point=True, color="#10b981", strokeWidth=2)
    .encode(
        x=alt.X("anno:O", title="Anno"),
        y=alt.Y("pct_convertiti:Q", title="% Convertiti", axis=alt.Axis(format=".0f")),
        tooltip=["anno", alt.Tooltip("pct_convertiti:Q", format=".1f")],
    )
    .properties(height=250)
)
st.altair_chart(chart_conv, width="stretch")

# ── Dettaglio per anno ────────────────────────────────────────────────────

st.subheader("Dettaglio per anno")

display = df_sorted[["anno", "n_dl", "n_convertiti", "n_decaduti", "pct_convertiti", "giorni_conversione_medio"]].copy()
display.columns = ["Anno", "DDL", "Convertiti", "Decaduti", "% Conv.", "Giorni media"]
st.dataframe(display, width='stretch', hide_index=True)

st.caption("Dati: Senato della Repubblica · Camera dei Deputati · CC BY 4.0")
