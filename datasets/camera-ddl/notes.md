# Notes — camera-ddl

## 2026-09-15 — Setup iniziale + espansione multi-legislatura

### Cosa è stato fatto
- Nuovo dataset: Camera DDL da dati.camera.it SPARQL
- Esteso a tutte le legislature (Leg13–19) con query per-legislatura
- Pipeline: SPARQL → CSV → clean (dedup) → 3 mart

### Dati per legislature
| Leg | DDL |
|---|---|
| 13 | 7.091 |
| 14 | 6.365 |
| 15 | 3.444 |
| 16 | 5.714 |
| 17 | 4.822 |
| 18 | 3.705 |
| 19 | 3.099 |

### Root cause fix
- **Query per-legislatura**: la prima versione scaricava tutto in una query
  (25 pagine × 10k) e produceva lo stesso output per ogni anno. Fix: filtro
  `?atto ocd:rif_leg <...repubblica_{year}>` nella query SPARQL.
- **DuckDB NULL vs empty string**: `regexp_extract` restituisce stringa vuota
  (non NULL) quando non matcha → `IS NOT NULL` non filtra. Fix: `NULLIF(..., '')`.
- **Atti Costituenti e storici**: URI con pattern `accostituente_*` e `CD*`
  non matchano il regex `ac\d+_(\d+)` → filtrati con `tipo = 'Progetto di Legge'`.
- **Stato iter mancante**: legislature vecchie non hanno `ocd:rif_statoIter` →
  `mart_stato` con `min_rows: 0`.

### Differenza con conteggio SPARQL (~240k)
Il regex `ac\d+_(\d+)` cattura solo DDL con URI standard. Gatti storici con
formati URI diversi (`CD`, `costituente`, `r_`) vengono esclusi — corretto
perché non hanno numero DDL standardizzabile.

## Source

- Endpoint: `https://dati.camera.it/sparql` — Virtuoso / OpenData Camera
- Predicati: `ocd:atto`, `dc:title`, `dc:identifier`, `dc:date`, `dc:type`,
  `ocd:rif_leg`, `ocd:rif_statoIter`, `ocd:primo_firmatario`
- Limite endpoint: 10k righe per query sorted → usiamo GROUP BY senza ORDER BY
