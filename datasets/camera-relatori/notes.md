# camera_relatori — relatori della Camera (Leg13–19)

Il **relatore** è il deputato che segue e "dirige" uno specifico atto in
commissione: scrive la relazione, gestisce gli emendamenti, lo porta in aula.
È il *regista politico* di ogni legge — la fase 3 dell'iter, dal lato che
produce.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:relatore`, filtro URI `rel{year}_`
- **Righe**: Leg19 ~10.360 incarichi · **1.000+ deputati** coinvolti
- **Campi**: `relatore_id`, `deputato_id`, `data`, `tipo`, `legislatura`
- La `data` è quella della discussione (`dc:date` in cui il relatore ha
  riferito in commissione)

## 2026-10-02 — Pattern C multi-legislature

- `years: [16,17,18,19]` — **LOD Camera ha solo rel16_..rel19_** (rel13/14/15 = 0 live)
- Query `FILTER(CONTAINS(STR(?rel), "rel{year}_"))`
- Clean: `{year} AS legislatura`; min_rows 1000 (per-leg)
- pages: 2 (Leg19 ~10k > cap 10k; storiche sotto il cap)

## Numeri (riferimento Leg19)

- **Top relatori**: Sbardella 226, Russo 201, Tremaglia 183, Maschio 181,
  Mascaretti 170 — i "registi" che seguono decine di leggi
- **Per anno**: picco 2023 (3.196 incarichi, 245 deputati), poi 2.900/anno
- Nel profilo: `n_relatori` e `anni_relatore` per ogni deputato

## Note / limiti

- Il legame **atto esplicito** non è diretto: il relatore è referenziato da
  una `discussione` (che ha seduta/data ma non sempre il codice atto). Il
  dataset cattura chi-quando, non ancora il singolo atto; il join atto è
  lavoro futuro via `allegatoDiscussione`/seduta
- `relatore_id` = URI (chiave unica); dedup in clean
- 10.621 stimati, 10.360 dopo dedup/date mancanti

## Rebuild

```bash
make run-camera-relatori
```
