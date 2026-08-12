PYTHON ?= python3
# toolkit CLI — vedi rna-aiuti-stato (safe_connect applica memory_limit=2GB)
TOOLKIT = $(PYTHON) -m toolkit.cli.app

# --- Dataset ---

.PHONY: run-elezioni-politiche run-elezioni-europee run-elezioni-comunali run-elezioni-regionali run-elezioni-referendum run-camera-deputati-legislature run-camera-gruppi run-camera-incarichi run-camera-votazioni-sparql run-senato-anagrafica run-senato-ddl run-senato-firmatari run-membri-governo run-dait-amministratori-locali run-elezioni-voto run-all

run-elezioni-politiche:
	$(TOOLKIT) run --config datasets/elezioni-politiche/dataset.yml

run-elezioni-europee:
	$(TOOLKIT) run --config datasets/elezioni-europee/dataset.yml

run-elezioni-comunali:
	$(TOOLKIT) run --config datasets/elezioni-comunali/dataset.yml

run-elezioni-regionali:
	$(TOOLKIT) run --config datasets/elezioni-regionali/dataset.yml

run-elezioni-referendum:
	$(TOOLKIT) run --config datasets/elezioni-referendum/dataset.yml

run-camera-deputati-legislature:
	$(TOOLKIT) run --config datasets/camera-deputati-legislature/dataset.yml

run-camera-gruppi:
	$(TOOLKIT) run --config datasets/camera-gruppi/dataset.yml

run-camera-incarichi:
	$(TOOLKIT) run --config datasets/camera-incarichi/dataset.yml

run-camera-votazioni-sparql:
	$(TOOLKIT) run --config datasets/camera-votazioni-sparql/dataset.yml

run-senato-anagrafica:
	$(TOOLKIT) run --config datasets/senato-anagrafica/dataset.yml

run-senato-ddl:
	$(TOOLKIT) run --config datasets/senato-ddl/dataset.yml

run-senato-firmatari:
	$(TOOLKIT) run --config datasets/senato-firmatari/dataset.yml

run-membri-governo:
	$(TOOLKIT) run --config datasets/membri-governo/dataset.yml

run-dait-amministratori-locali:
	$(TOOLKIT) run --config datasets/dait-amministratori-locali/dataset.yml

run-elezioni-voto:
	$(TOOLKIT) run --config compose/elezioni-voto/dataset.yml

run-all: run-elezioni-politiche run-elezioni-europee run-elezioni-comunali run-elezioni-regionali run-elezioni-referendum run-camera-deputati-legislature run-camera-gruppi run-camera-incarichi run-camera-votazioni-sparql run-senato-anagrafica run-senato-ddl run-senato-firmatari run-membri-governo run-dait-amministratori-locali run-elezioni-voto

# --- Validazione config ---

.PHONY: check
check:
	@for f in $$(find datasets compose -name dataset.yml | sort); do \
		echo "→ $$f"; \
		$(TOOLKIT) run preflight --config "$$f" > /dev/null 2>&1 || exit 1; \
	done
	@echo "All configs valid"

# --- Pulizia ---

.PHONY: clean clean-runs
clean:
	rm -rf out/data/_runs out/data/probe out/data/raw out/data/clean out/data/mart out/data/cross .tmp/

clean-runs:
	rm -rf out/data/_runs/

# --- Registry (artifact catalogo — dry-run di default) ---

.PHONY: registry registry-write
registry:
	toolkit registry build

registry-write:
	toolkit registry build --write

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort
