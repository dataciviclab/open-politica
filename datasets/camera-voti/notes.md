# camera_voti — voti individuali dei Deputati (XIX leg.)

Voto di ogni deputato su ogni votazione elettronica della XIX legislatura,
dalla classe `ocd:voto` di dati.camera.it (59,4M istanze, tutte le legislature).
Completa il quadro: ora il profilo politico copre **entrambe le camere** con
i voti individuali.

## Dati

- **Fonte**: dati.camera.it — SPARQL, classe `ocd:voto`
- **Periodo**: XIX legislatura (2022-2026)
- **Volume**: 7.747.588 voti · 414 deputati · 19.425/19.428 votazioni
- **Stati**: FAVOREVOLE, CONTRARIO, ASTENUTO, NON_HA_VOTATO, IN_MISSIONE,
  HA_VOTATO
- **Chiavi**: `deputato_id` (persona_id Camera), `votazione` (URI, join con
  `camera_votazioni_sparql`), `data`, `sigla_gruppo`

## Estrazione (lezione appresa)

`ocd:voto` NON è paginabile con OFFSET su Virtuoso (instabile senza ORDER BY:
overlap e buchi). Approccio corretto e deterministico:

1. **Lista votazioni** XIX (19.428) paginata + **dedup** (le votazioni hanno
   triple `rdf:type` duplicate → compaiono 2 volte)
2. **Batch per votazione** via `FILTER(?vr IN (...))` — result-set fisso per
   batch → niente overlap. ~98 batch da 200 votazioni
3. **POST form-encoded** (non GET): la GET con IN-list lunghe fallisce con
   **414 Request-URI Too Long**; la POST mette la query nel body
4. **Date**: `dc:date` è presente su tutte le 19.428 votazioni (il dataset
   `camera_votazioni_sparql` ne cattura solo 3.321 per il suo filtro per
   anno → NON usarlo per le date)
5. **Dedup finale** su `voto_uri` (le tripl `rdf:type` duplicate generano
   righe duplicate nel SELECT)

```bash
make extract-camera-voti   # estrazione completa (batch 200, ~30 min)
make run-camera-voti       # pipeline → clean + mart
```

## Limiti

- Solo XIX legislatura (2022-2026); per le altre basta `--legislature N`
- Gli stati IN_MISSIONE/HA_VOTATO sono pochi (il "Non ha votato" copre il
  grosso delle assenze); la partecipazione netta va derivata dai conteggi
  delle votazioni o dagli stati F/C/A
