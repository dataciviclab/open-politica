# profilo_politico — scheda viva del parlamentare (Camera + Senato)

Primo mart composito che unifica il profilo di **entrambe le camere** (XIX
legislatura) con una dimensione `ramo`. Non più un insieme di dataset, ma una
scheda interrogabile per ogni parlamentare.

## Metriche

- **Partecipazione** — `n_voti` espressi
- **Direzione** — `n_favorevoli` / `n_contrari` / `n_astenuti`
- **Coerenza** (`pct_coerente`) — % di voti in linea con l'esito della
  votazione. **Ora su entrambe le camere**: per la Camera l'esito è
  `approvato` da `camera_votazioni_sparql` (serie multi-anno, join per
  votazione al 100%)
- **Affidabilità al gruppo** (`pct_col_gruppo`) — % di voti (F/C) in linea col
  voto dominante del proprio gruppo sulla stessa votazione
- **Governo** — `n_cariche_governo` in carica, `in_governo`
- **Commissioni** — `n_commissioni_attuali`, `presidente_commissione`,
  `commissioni_attuali` (lista "nome (ruolo)"): la fase 3 dell'iter,
  "di cosa si occupa davvero". **Entrambe le camere** (grano diverso:
  Senato = membership completa; Camera = ruoli/vertici di organo)

## Come si calcola il gruppo

- **Senato**: join della membership `senato_gruppi` per periodo (data del voto)
- **Camera**: `camera_voti.sigla_gruppo` — il gruppo è registrato **al momento
  del voto** nella riga stessa (più preciso, nessun join)

## Risultato (XIX leg.)

- **Affidabilità media ~99,5% in entrambe le camere** — la disciplina di
  partito è uniformemente alta
- **Divergenti Camera**: Soumahoro (80%), Minardo, Cesa (91%), Gallo (91%)
- **Leali 100% Camera**: Meloni, Giorgetti, Lollobrigida, Fitto (con pochi voti
  espressi: premier/ministri raramente in aula)
- **Divergenti Senato**: Durnwalder (SVP), Versace, Gelmini, Calenda

## Rebuild

```bash
# richiede i clean locali di: camera_voti, senato_votazioni, camera_deputati,
# senato_anagrafica, senato_gruppi, ponte_persona, membri_governo
make run-profilo-politico
```

## Limiti

- `persona_id` NULL per i senatori mai stati deputati (identity solo `senatore_id`)
- L'identità unica persona (Camera↔Senato) è limitata al ponte (29% dei senatori)
- `pct_coerente` della Camera deriva dall'esito `approvato` di
  `camera_votazioni_sparql` (che copre il 100% delle votazioni XIX) — per
  votazioni a cavallo di anno il join è per URI, non per data
- **Commissioni di grano diverso**: per la Camera la membership completa
  (tutti i "Membro") non è ancora estratta — solo i ruoli (presidente,
  capogruppo, segretari)
