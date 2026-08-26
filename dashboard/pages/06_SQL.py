"""Query SQL — interrogazione diretta dei dati."""

from lab_connectors.duckdb.sql_page import render_sql_query

from sources import PREFIX

render_sql_query(
    years=list(range(2022, 2027)),
    prefix=PREFIX,
    title="🧪 Query SQL",
    description="Interroga i dati di Open Politica. Usa ``clean_input`` come tabella.",
    example_queries=[
        {"label": "Chi parla meno?", "sql": "SELECT * FROM clean_input ORDER BY n_interventi LIMIT 10"},
        {"label": "Ribelli Camera", "sql": "SELECT * FROM clean_input WHERE ramo='camera' ORDER BY pct_col_gruppo LIMIT 10"},
        {"label": "Top 10 fedeli", "sql": "SELECT * FROM clean_input ORDER BY pct_col_gruppo DESC LIMIT 10"},
    ],
)
