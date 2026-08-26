"""Query SQL — Interroga direttamente i dati di Open Politica."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sources import PREFIX, YEARS
from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry import load_registry

render_sql_query(
    years=YEARS,
    prefix=PREFIX,
    registry=load_registry(Path("../open-politica/registry/registry.json")),
    title="🧪 Query SQL",
    description="Interroga direttamente i dati di Open Politica.",
    example_queries=[
        {
            "label": "Chi parla meno?",
            "sql": (
                "SELECT deputato_id, COUNT(*) AS interventi "
                "FROM clean_input "
                "WHERE legislature = 19 "
                "GROUP BY deputato_id ORDER BY interventi ASC LIMIT 20"
            ),
        },
        {
            "label": "Ribelli Camera",
            "sql": (
                "SELECT * FROM clean_input "
                "WHERE ramo = 'C' AND fedelta_al_gruppo < 1.0 "
                "ORDER BY fedelta_al_gruppo ASC LIMIT 20"
            ),
        },
        {
            "label": "Top 10 fedeli",
            "sql": (
                "SELECT * FROM clean_input "
                "WHERE ramo = 'S' AND fedelta_al_gruppo IS NOT NULL "
                "ORDER BY fedelta_al_gruppo DESC LIMIT 10"
            ),
        },
    ],
)
