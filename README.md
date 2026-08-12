# open-politica

Dati aperti e interrogabili sulla politica italiana — elezioni, parlamento,
governo, legislazione e amministratori locali — con la **Persona** come entità
centrale del grafo.

Repo dedicata del dominio politico (progetto interno). I config migrano da
`dataset-incubator` seguendo il modello di `rna-aiuti-stato`.

## Perimetro

| Dominio | Dataset |
|---|---|
| Elezioni | `elezioni_politiche`, `elezioni_europee`, `elezioni_comunali`, `elezioni_regionali`, `elezioni_referendum`, `elezioni_voto` (compose) |
| Camera | `camera_deputati_legislature`, `camera_gruppi`, `camera_incarichi`, `camera_votazioni_sparql` |
| Senato | `senato_anagrafica`, `senato_ddl`, `senato_firmatari` |
| Governo | `membri_governo` |
| Amministratori locali | `dait_amministratori_locali` |

## Roadmap

- [ ] Step 0 — migrazione config da dataset-incubator (fatto: config copiati in `datasets/` + `compose/`)
- [ ] Step 1 — `senato_votazioni` (voti individuali via SPARQL) + ponte `person_id` ↔ `senator_id` + fix dedup `camera_incarichi`
- [ ] Step 2 — `camera_voti_individuali` (scraping HTML) + compose `profilo_politico` (hub Persona)
- [ ] Step 3 — gap inventario (commissioni, referendum 1946, regionali 1970, costituente 1946) + prima analisi "chi vota col proprio gruppo?"

## Struttura

```
open-politica/
  datasets/                  # un filone = dataset.yml + sql/
  compose/                   # dataset compositi (es. elezioni-voto)
  registry/                  # registry.json (artifact catalogo, fusion ADR)
  notes/                     # note per dataset
  scripts/                   # estrazione SPARQL, scraping
  tests/
  out/                       # output runtime — mai versionato
```

## Comandi

```bash
make run-<slug>          # esegue il dataset via toolkit
make check               # valida tutti i config
make registry-write      # build registry/registry.json
```

> **Elezioni**: i dataset `elezioni_*` usano il source type `script`
> (preprocess.py), disabilitato di default nel toolkit per policy. Il Makefile
> abilita già `TOOLKIT_ALLOW_SCRIPT_SOURCE=1`; a mano serve
> `TOOLKIT_ALLOW_SCRIPT_SOURCE=1 python3 -m toolkit.cli.app run --config ...`.
> Senza questa env var i run elezioni falliscono al layer raw (fonte del
> FAILED storico di `elezioni_comunali`).

## Fonti

- Eligendo — Archivio storico elettorale DAIT (Ministero dell'Interno)
- dati.camera.it — OpenData SPARQL endpoint
- dati.senato.it — OpenData SPARQL endpoint
- DAIT — Anagrafe Amministratori Locali
