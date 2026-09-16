# Notes — camera-leggi

## 2026-09-15 — Setup iniziale + espansione multi-legislatura

### Cosa è stato fatto
- Nuovo dataset: leggi Camera da dati.camera.it SPARQL (`ocd:legge`)
- Esteso a tutte le legislature (Leg13–19) con query per-legislatura
- Pipeline: SPARQL → CSV → clean → 3 mart

### Ponte Normattiva
Ogni legge ha `ocd:lex` che punta a Normattiva → 100% copertura URN.
Questo è il ponte chiave tra Camera e Legal Graph.

### DDL bridge
76 leggi su 188 (Leg19) hanno `ddl_numero` estratto dal titolo
(parentesi finale: "...(3053)"). Ponte verso `camera_ddl.id_ddl`.

### Root cause fix
- **Legge Costituzionale**: URI `LC2026_2` non matchava il regex `L\d+_(\d+)`.
  Fix: `L[C]?\d+_(\d+)`.
- **ORDER BY su >10k rows**: Virtuoso rifiuta `ORDER BY` con >10k risultati.
  Fix: rimosso `ORDER BY` dalla query SPARQL.
- **min_rows troppo alto**: 188 righe < 1000. Fix: abbassato a 100.

## Source

- Endpoint: `https://dati.camera.it/sparql` — Virtuoso / OpenData Camera
- Predicati: `ocd:legge`, `rdfs:label`, `dc:identifier`, `dc:date`,
  `dc:type`, `ocd:lex`, `dc:publisher`, `ocd:rif_leg`
