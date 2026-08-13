# camera_relatori — relatori della Camera (XIX leg.)

Il **relatore** è il deputato che segue e "dirige" uno specifico atto in
commissione: scrive la relazione, gestisce gli emendamenti, lo porta in aula.
È il *regista politico* di ogni legge — la fase 3 dell'iter, dal lato che
produce.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:relatore`
- **Righe**: 10.360 incarichi da relatore · **1.000+ deputati** coinvolti
- **Campi**: `relatore_id`, `deputato_id`, `data`, `tipo`, `legislatura`
- La `data` è quella della discussione (`dc:date` in cui il relatore ha
  riferito in commissione)

## Numeri (XIX leg.)

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
