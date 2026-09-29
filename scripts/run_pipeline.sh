#!/usr/bin/env bash
# run_pipeline.sh — orchestrazione open-politica
#
# Con la migrazione a type: script, il toolkit gestisce automaticamente:
#   - estrazioni SPARQL (camera-voti, senato-votazioni) via preprocess.py
#   - dipendenze support (ponte-persona → camera_deputati + senato_anagrafica)
#
# Questo script resta come entry point per make run-all / CI.
set -euo pipefail

TOOLKIT="${TOOLKIT:-toolkit}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# ── Run tutti i dataset (il toolkit gestisce ordine e support) ─────────
echo "═══ Run datasets ═══"
find datasets -name dataset.yml | sort | while read -r cfg; do
  echo "→ $cfg"
  $TOOLKIT run -c "$cfg"
done

# ── Run compose ═════════════════════════════════════════════════════════
echo "═══ Run compose ═══"
find compose -name dataset.yml | sort | while read -r cfg; do
  echo "→ $cfg"
  $TOOLKIT run -c "$cfg"
done

echo "✅ Pipeline completata"
