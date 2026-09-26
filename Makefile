TOOLKIT ?= toolkit

# --- Dataset -----------------------------------------------------------

DATASETS := $(shell find datasets -name dataset.yml 2>/dev/null | sort)
COMPOSES := $(shell find compose -name dataset.yml 2>/dev/null | sort)

# --- Pipeline completa (extract → datasets → ponte → compose) ----------

.PHONY: run-all
run-all:
	TOOLKIT_ALLOW_SCRIPT_SOURCE=1 ./scripts/run_pipeline.sh

# --- Estrazioni pesanti (servono solo per senato/camera voti) ----------

.PHONY: extract-senato-votazioni extract-camera-voti
extract-senato-votazioni:
	python3 scripts/extract_senato_votazioni.py --legislature 19 --incremental

extract-camera-voti:
	python3 scripts/extract_camera_voti.py --legislature 19 --batch 200 --incremental

# --- Validazione config ------------------------------------------------

.PHONY: check
check:
	@for f in $(DATASETS) $(COMPOSES); do \
		echo "→ $$f"; \
		$(TOOLKIT) run preflight --config "$$f" > /dev/null 2>&1 || exit 1; \
	done
	@echo "✅ All configs valid"

# --- Pulizia -----------------------------------------------------------

.PHONY: clean clean-runs
clean:
	rm -rf out/data/_runs out/data/probe out/data/raw out/data/clean out/data/mart out/data/cross .tmp/

clean-runs:
	rm -rf out/data/_runs/

# --- Registry ----------------------------------------------------------

.PHONY: registry registry-write
registry:
	$(TOOLKIT) registry build --prefix open-politica

registry-write:
	$(TOOLKIT) registry build --prefix open-politica --write

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort
