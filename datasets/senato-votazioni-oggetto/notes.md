# senato_votazioni_oggetto — ponte votazioni → DDL

Collega le **votazioni del Senato** ai **DDL** tramite l'oggetto di
trattazione (default graph `dati.senato.it`).

## Catena

```text
votazione  →  osr:oggetto  →  OggettoTrattazione.osr:relativoA  →  ddl
```

## Perché default graph

I named graph (`GRAPH ?g`) **spezzano** il join (probe live 2026-10-01):
`votazione.oggetto` e `oggetto.relativoA` vivono in grafi diversi.
Sul **default graph** Virtuoso li unisce correttamente.

## Volume atteso

- Votazioni totali Senato ~64k · con `oggetto` ~48k · con `ddl` ~39k
- Il clean tiene **una riga per votazione** (non i voti individuali)

## Join utili

- `senato_votazioni.votazione_id` → `senato_votazioni_oggetto.votazione_id`
- `senato_votazioni_oggetto.ddl_id` → `senato_ddl.id_ddl` / `atto_num`

## Limiti

- Esito emendamento: assente (non è un dataset emendamenti)
- Copertura non uniforme: alcune votazioni senza oggetto
- WAF: GET + paginazione; query con nomi variabile lunghi → risultati vuoti
