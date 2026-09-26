#!/usr/bin/env bash
# run_pipeline.sh — orchestrazione completa open-politica
#
# Usage:
#   ./scripts/run_pipeline.sh              # tutti i dataset
#   ./scripts/run_pipeline.sh datasets/X   # solo dataset specifico
#
# Ordine:
#   1. Estrazioni pesanti (senato_votazioni, camera_voti) — solo se servono
#   2. Run datasets
#   3. Build ponte persona (se i dataset che produce sono stati runnati)
#   4. Run compose
set -euo pipefail

TOOLKIT="${TOOLKIT:-toolkit}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

HEAVY="senato-votazioni camera-voti"

# ── Parse args ────────────────────────────────────────────────────────
TARGETS=()
if [ $# -gt 0 ]; then
  TARGETS=("$@")
fi

# ── Helper: check se un dataset pesante è nei target ──────────────────
needs_extract() {
  for t in "${TARGETS[@]}"; do
    slug=$(basename "$t")
    for h in $HEAVY; do
      [ "$slug" = "$h" ] && return 0
    done
  done
  # Se nessun target specificato, serve sempre
  [ ${#TARGETS[@]} -eq 0 ]
}

# ── 1. Estrazioni pesanti ─────────────────────────────────────────────
if needs_extract; then
  echo "═══ Extract heavy sources ═══"
  python3 "$SCRIPT_DIR/extract_senato_votazioni.py" --legislature 19 --incremental &
  SEN=$!
  python3 "$SCRIPT_DIR/extract_camera_voti.py" --legislature 19 --batch 200 --incremental &
  CAM=$!
  wait $SEN || { echo "❌ extract_senato_votazioni fallito"; exit 1; }
  wait $CAM || { echo "❌ extract_camera_voti fallito"; exit 1; }
fi

# ── 2. Run datasets (escluso ponte-persona, gestito allo step 3) ──────
echo "═══ Run datasets ═══"
if [ ${#TARGETS[@]} -gt 0 ]; then
  for t in "${TARGETS[@]}"; do
    if [ -f "$t/dataset.yml" ] && [ "$(basename "$t")" != "ponte-persona" ]; then
      echo "→ $t"
      $TOOLKIT run -c "$t/dataset.yml"
    fi
  done
else
  find datasets -name dataset.yml | sort | while read -r cfg; do
    dir=$(dirname "$cfg")
    [ "$(basename "$dir")" = "ponte-persona" ] && continue
    echo "→ $dir"
    $TOOLKIT run -c "$cfg"
  done
fi

# ── 3. Build ponte persona ────────────────────────────────────────────
# Il ponte legge i clean di camera_deputati + senato_anagrafica.
# DEVE girare dopo i dataset che producono quei clean.
if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "═══ Build ponte persona ═══"
  python3 "$SCRIPT_DIR/build_ponte_persona.py"
  $TOOLKIT run -c datasets/ponte-persona/dataset.yml
fi

# ── 4. Run compose ────────────────────────────────────────────────────
echo "═══ Run compose ═══"
if [ ${#TARGETS[@]} -gt 0 ]; then
  for t in "${TARGETS[@]}"; do
    if [[ "$t" == compose/* ]] && [ -f "$t/dataset.yml" ]; then
      echo "→ $t"
      $TOOLKIT run -c "$t/dataset.yml"
    fi
  done
else
  find compose -name dataset.yml | sort | while read -r cfg; do
    dir=$(dirname "$cfg")
    echo "→ $dir"
    $TOOLKIT run -c "$cfg"
  done
fi

echo "✅ Pipeline completata"
