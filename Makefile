TOOLKIT ?= toolkit
export TOOLKIT_ALLOW_SCRIPT_SOURCE := 1

# --- Dataset -----------------------------------------------------------

DATASETS := $(shell find datasets -name dataset.yml 2>/dev/null | sort)
COMPOSES := $(shell find compose -name dataset.yml 2>/dev/null | sort)

# --- Pipeline completa (datasets → compose) ---------------------------

.PHONY: run-all
run-all: run-datasets run-compose

.PHONY: run-datasets
run-datasets:
	@for f in $(DATASETS); do \
		echo "→ $$f"; \
		$(TOOLKIT) run -c "$$f" || exit 1; \
	done

.PHONY: run-compose
run-compose:
	@for f in $(COMPOSES); do \
		echo "→ $$f"; \
		$(TOOLKIT) run -c "$$f" || exit 1; \
	done

# --- Batch selettivo (PR post-merge: solo dataset cambiati) -----------

.PHONY: run-batch
run-batch:
	@if [ -s batch.txt ]; then \
		$(TOOLKIT) run --batch batch.txt; \
	else \
		echo "Nessun dataset da processare"; \
	fi

# --- Estrazioni manuali (convenience) ---------------------------------

.PHONY: extract-senato-votazioni extract-camera-voti
extract-senato-votazioni:
	python3 datasets/senato-votazioni/preprocess.py --legislature 19 --incremental

extract-camera-voti:
	python3 datasets/camera-voti/preprocess.py --legislature 19 --batch 200 --incremental

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
