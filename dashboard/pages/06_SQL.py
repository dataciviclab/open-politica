"""Query SQL — Interroga direttamente i dati di Open Politica."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry import load_registry

registry = load_registry(Path(__file__).parent.parent.parent / "registry" / "registry.json")

render_sql_query(
    registry=registry,
    prefix="open-politica/",
    default_slug="profilo_politico",
    title="🧪 Query SQL",
    description="Interroga direttamente i dati di Open Politica. Scrivi SQL su ``clean_input``.",
)
