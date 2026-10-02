# camera_commissioni — organi della Camera (Leg13–19), ruoli

Chi ricopre **ruoli** negli organi della Camera (commissioni, giunte, comitati):
presidente, vicepresidente, capogruppo, segretario, questore.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:ufficioParlamentare` + `rif_leg repubblica_{year}`
- **Righe**: Leg19 ~778 · **Organi**: ~67
- **Campi**: `deputato_id`, `organo_id`, `nome`, `carica`, `data_inizio`,
  `data_fine`, `legislatura`

## 2026-10-02 — Pattern C multi-legislature

- `years: [13..19]`, query `rif_leg <.../repubblica_{year}>`
- Clean: `{year} AS legislatura`; min_rows 150 (per-leg)
- **Cariche**: CAPOGRUPPO (365), SEGRETARIO (168), VICEPRESIDENTE (132),
  PRESIDENTE (93), QUESTORE (18)

## Nota di grano

`ocd:ufficioParlamentare` NON è la membership completa (non ci sono "Membro"):
cattura i **vertici di organo** (ufficio di presidenza + capigruppo + segretari).
Al Senato invece `osr:Afferenza` include tutti i membri. I due dataset sono
quindi complementari ma di grano diverso:
- **Camera**: chi comanda l'organo (presidente, capogruppo...)
- **Senato**: chi ne fa parte (tutti i membri)

La membership completa Camera è nei `haMembro` dell'organo (bnode) — lavoro
futuro se serve.

## Note tecniche

- Il predicato fine è **`dc:date`** (purl), non `ocd:date` — errore subdolo
- Il constraint `?dep a ocd:deputato` è necessario: l'organo ha anch'esso
  `rif_ufficioParlamentare` verso le stesse membership → senza, doppio match
- `startDate` è tutto cifre → DuckDB lo inferisce BIGINT → serve
  `CAST(... AS VARCHAR)` prima di `substr`
- Volume reale ~778 (sotto i 800 stimati)

## Rebuild

```bash
make run-camera-commissioni
```
