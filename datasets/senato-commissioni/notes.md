# senato_commissioni — commissioni del Senato (XIX leg.)

Membership dei senatori alle commissioni parlamentari — la **fase 3** dell'iter
legislativo (dove si esamina e si scrive davvero la legge), prima del voto in
aula. Completa il profilo oltre il voto: "di cosa si occupa davvero ogni
senatore".

## Dati

- **Fonte**: dati.senato.it — SPARQL, graph `composizione/19` (`osr:Afferenza`)
- **Righe**: 1.052 (una per periodo di appartenenza con ruolo)
- **Commissioni**: 46 (permanenti per materia, speciali, d'inchiesta, giunte,
  organismi interni)
- **Campi**: `senatore_id`, `commissione_id`, `nome`, `materia`, `categoria`,
  `carica` (Membro/Presidente/Vicepresidente...), `data_inizio`, `data_fine`

## Come si legge

- Le **permanenti** (11): 1ª Affari Presidenza/Interno, 2ª Giustizia,
  3ª Esteri, 5ª Bilancio, 6ª Finanze, 7ª Cultura/Istruzione, 8ª Ambiente,
  9ª Industria, 10ª Affari sociali/Sanità, 14ª UE... — una per materia
- **Presidenti/vicepresidenti** di commissione = ruoli di potere reale
  (agenda dei lavori), non catturati da nessun altro dataset
- Uno stesso senatore può avere più afferenze sulla stessa commissione con
  ruoli diversi (es. Membro + Segretario) → la chiave include `carica`/date

## Rebuild

```bash
make run-senato-commissioni
```

## Note tecniche

- L'endpoint Senato richiede curl (WAF: POST/requests → 403; il source sparql
  del toolkit usa HttpClient con fallback curl, quindi passa)
- `commissione_id` usa il suffisso completo `"0-7"` (il solo primo numero
  colliderebbe: 0-7 e 0-21 hanno entrambi prefisso 0)
- `nome`/`materia` via MAX (la commissione ha più etichette storiche)
