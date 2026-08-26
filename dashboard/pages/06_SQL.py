"""Query SQL — interrogazione diretta dei dati."""

from lab_connectors.duckdb.sql_page import render_sql_query

from sources import PREFIX

render_sql_query(
    years=list(range(2022, 2027)),
    prefix=PREFIX,
    title="🧪 Query SQL",
    description="Interroga direttamente i dati di Open Politica. Usa ``clean_input`` come tabella virtuale.",
)
