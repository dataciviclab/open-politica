# camera_commissioni — organi della Camera (XIX leg.), ruoli

Chi ricopre **ruoli** negli organi della Camera (commissioni, giunte, comitati):
presidente, vicepresidente, capogruppo, segretario, questore.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:ufficioParlamentare`
- **Righe**: 778 · **Organi**: 67 (commissioni permanenti, d'inchiesta, giunte,
  ufficio di presidenza)
- **Campi**: `deputato_id`, `organo_id`, `nome`, `carica`, `data_inizio`,
  `data_fine`, `legislatura`
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
