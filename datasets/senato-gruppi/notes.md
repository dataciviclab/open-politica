# senato_gruppi — gruppi parlamentari del Senato (XIX leg.)

Membership dei senatori ai gruppi parlamentari, con cariche e periodi
(inizio/fine) — i **cambi di gruppo nel tempo** sono tracciati.

## Dati

- **Fonte**: dati.senato.it — SPARQL, graph `composizione/19`
- **Righe**: 288 (una per periodo di adesione senatore→gruppo)
- **Struttura**: senatore → `ocd:aderisce` → adesioneGruppo {gruppo, carica,
  inizio, fine}; etichette via `denominazione` → `osr:titolo/titoloBreve`
  (es. gruppo 56 = "Lega Salvini Premier - Partito Sardo d'Azione", FdI, ...)

## Uso

Alimenta `profilo_politico` per la metrica **pct_col_gruppo** (affidabilità):
% di voti del senatore in linea col voto dominante del proprio gruppo sulla
stessa votazione — l'indice di "vota col suo gruppo" (stile Openpolis).

```bash
make run-senato-gruppi
make run-profilo-politico   # ricompone il profilo con la membership
```

## Insight dal primo run (XIX leg.)

- **Tutti i gruppi molto compatti**: pct_col_gruppo tipicamente 95-100%.
  La divisione governo/opposizione è **strutturale di gruppo**, non
  individuale: l'opposizione vota in blocco contro l'esito vincente.
- **Divergenti individuali** (i meno "affidabili"): Durnwalder (SVP, 89%),
  Versace, Gelmini (94%), Calenda (95,6%) — i noti voti autonomi
- **Salvini**: 100% coerente con l'esito E 100% col proprio gruppo

## Limiti

- Solo XIX legislatura (graph composizione/19)
- Il voto dominante del gruppo si calcola sulla moda F/C della singola
  votazione; votazioni molto ravvicinate con membership a cavallo possono
  avere assegnazione approssimata (join su data)
