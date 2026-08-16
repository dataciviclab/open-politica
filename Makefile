PYTHON ?= python3
# toolkit CLI — vedi rna-aiuti-stato (safe_connect applica memory_limit=2GB)
# TOOLKIT_ALLOW_SCRIPT_SOURCE: i dataset elezioni usano preprocess.py come
# source type `script`, disabilitato di default nel toolkit (policy).
TOOLKIT = TOOLKIT_ALLOW_SCRIPT_SOURCE=1 $(PYTHON) -m toolkit.cli.app

# --- Dataset ---

.PHONY: run-elezioni-politiche run-elezioni-europee run-elezioni-comunali run-elezioni-regionali run-elezioni-referendum run-camera-deputati-legislature run-camera-gruppi run-camera-incarichi run-camera-votazioni-sparql run-camera-voti run-senato-anagrafica run-senato-ddl run-senato-firmatari run-senato-gruppi run-senato-commissioni run-camera-commissioni run-camera-relatori run-camera-interventi run-senato-interventi run-membri-governo run-dait-amministratori-locali run-elezioni-voto run-senato-votazioni run-ponte-persona run-camera-voti run-profilo-politico run-osservatorio-parlamento run-decreti-legge extract-senato-votazioni extract-camera-voti build-ponte-persona run-all

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

run-senato-votazioni:
	$(TOOLKIT) run --config datasets/senato-votazioni/dataset.yml

run-senato-gruppi:
	$(TOOLKIT) run --config datasets/senato-gruppi/dataset.yml

run-senato-commissioni:
	$(TOOLKIT) run --config datasets/senato-commissioni/dataset.yml

run-camera-commissioni:
	$(TOOLKIT) run --config datasets/camera-commissioni/dataset.yml

run-camera-relatori:
	$(TOOLKIT) run --config datasets/camera-relatori/dataset.yml

run-camera-interventi:
	$(TOOLKIT) run --config datasets/camera-interventi/dataset.yml

run-senato-interventi:
	$(TOOLKIT) run --config datasets/senato-interventi/dataset.yml

extract-senato-votazioni:
	python3 scripts/extract_senato_votazioni.py --legislature 19

run-ponte-persona:
	$(TOOLKIT) run --config datasets/ponte-persona/dataset.yml

build-ponte-persona:
	python3 scripts/build_ponte_persona.py

run-camera-voti:
	$(TOOLKIT) run --config datasets/camera-voti/dataset.yml

extract-camera-voti:
	python3 scripts/extract_camera_voti.py --legislature 19 --batch 200

run-profilo-politico:
	$(TOOLKIT) run --config compose/profilo-politico/dataset.yml

run-osservatorio-parlamento:
	$(TOOLKIT) run --config compose/osservatorio-parlamento/dataset.yml

run-decreti-legge:
	$(TOOLKIT) run --config compose/decreti-legge/dataset.yml

run-senato-corpus-parlamento:
	$(TOOLKIT) run --config compose/senato-corpus-parlamento/dataset.yml

run-all: run-elezioni-politiche run-elezioni-europee run-elezioni-comunali run-elezioni-regionali run-elezioni-referendum run-camera-deputati-legislature run-camera-gruppi run-camera-incarichi run-camera-votazioni-sparql run-senato-anagrafica run-senato-ddl run-senato-firmatari run-membri-governo run-dait-amministratori-locali run-elezioni-voto run-senato-votazioni

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
