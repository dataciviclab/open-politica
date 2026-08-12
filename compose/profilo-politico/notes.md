# profilo_politico — scheda viva del senatore

Primo mart composito del dominio: per ogni senatore della XIX legislatura
unisce **partecipazione**, **direzione di voto**, **coerenza con l'esito**
e **ruolo di governo**. È il primo pezzo del "sistema" di civic intelligence:
non più un insieme di dataset, ma una scheda interrogabile.

## Metriche

- **Partecipazione** — `n_voti` espressi (su ~7.998 votazioni)
- **Direzione** — `n_favorevoli` / `n_contrari` / `n_astenuti`
- **Coerenza** — % di voti in linea con l'esito della votazione (FAVOREVOLE su
  approvata, CONTRARIO su respinta)
- **Governo** — `n_cariche_governo` in carica, `in_governo` (via persona_id +
  ponte)

## Insight dal primo run (XIX leg.)

- Il Senato vota soprattutto su **emendamenti dell'opposizione respinti**
  (6.173 respinte vs 1.825 approvate) → `CONTRARIO` su votazione respinta =
  votare col governo. La **coerenza con l'esito** è la metrica giusta, non il
  conteggio grezzo dei contrari.
- **Membri del governo ~100% coerenti** (Salvini, Urso 100%; Garavaglia,
  Calderoli, Zangrillo ~99,5%)
- **Opposizione ~8% coerenti** (Magni, Cucchi, Floridia, De Cristofaro) —
  votano contro l'esito vincente, come atteso
- **Partecipazione molto variabile**: Salvini solo 282 voti (ministro in
  missione), Garavaglia 5.498 (anche vicepresidente dell'aula); senatori a
  vita (Rubbia, Monti) quasi mai presenti

## Rebuild

```bash
# richiede i clean locali di senato_votazioni, senato_anagrafica,
# ponte_persona, membri_governo (make run-...-votazioni/anagrafica/ponte/governo)
make run-profilo-politico
```

## Limiti

- La "coerenza con l'esito" è un **proxy dell'allineamento al governo**; non
  distingue l'orientamento del singolo gruppo. L'indice "vota col proprio
  gruppo" (compattezza) richiede la membership senato per gruppo, non ancora
  estratta
- Copre solo i senatori della XIX con almeno un voto espresso
- `persona_id` presente solo per i senatori mappati dal ponte (~1/3)
