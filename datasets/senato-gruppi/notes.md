# senato_gruppi — gruppi parlamentari del Senato (Leg13–19)

Membership dei senatori ai gruppi parlamentari, con cariche e periodi
(inizio/fine) — i **cambi di gruppo nel tempo** sono tracciati.

## Dati

- **Fonte**: dati.senato.it — SPARQL, graph `composizione/{year}` (Leg13–19)
- **Righe**: Leg19 ~288 (una per periodo di adesione senatore→gruppo)
- **Struttura**: senatore → `ocd:aderisce` → adesioneGruppo {gruppo, carica,
  inizio, fine}; etichette via `denominazione` → `osr:titolo/titoloBreve`

## Uso

Alimenta `profilo_politico` per la metrica **pct_col_gruppo** (affidabilità):
% di voti del senatore in linea col voto dominante del proprio gruppo sulla
stessa votazione — l'indice di "vota col suo gruppo" (stile Openpolis).

```bash
make run-senato-gruppi
make run-profilo-politico   # ricompone il profilo con la membership
```

## 2026-10-02 — Pattern C multi-legislature

- `years: [13..19]`, query `GRAPH <.../composizione/{year}>`
- Clean: `{year} AS legislatura`
- min_rows clean abbassato a 100 (per-leg)

## Insight dal primo run (XIX leg.)

- **Tutti i gruppi molto compatti**: pct_col_gruppo tipicamente 95-100%.
  La divisione governo/opposizione è **strutturale di gruppo**, non
  individuale: l'opposizione vota in blocco contro l'esito vincente.
- **Divergenti individuali** (i meno "affidabili"): Durnwalder (SVP, 89%),
  Versace, Gelmini (94%), Calenda (95,6%) — i noti voti autonomi
- **Salvini**: 100% coerente con l'esito E 100% col proprio gruppo

## Limiti

- Perimetro Leg13–19 (graph `composizione/{year}`); I–XII non nel LOD
- Il voto dominante del gruppo si calcola sulla moda F/C della singola
  votazione; votazioni molto ravvicinate con membership a cavallo possono
  avere assegnazione approssimata (join su data)

## 2026-10-03 — Pipeline

- Perimetro multi-leg (Pattern C); I–XII non nel LOD dove applicabile.
- La pipeline su **push a main** (`datasets/**`) rilancia run + sync GCS
  di questi dataset (workflow `Pipeline`, `detect-paths: datasets compose`).
- Rebuild manuale: `toolkit run -c datasets/<slug>/dataset.yml` dalla root repo.
