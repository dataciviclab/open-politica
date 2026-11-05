# senato_emendamenti_lod — registro ufficiale emendamenti Senato

Registro degli emendamenti presentati al Senato (Leg13–19) dalla fonte ufficiale
Open Data: **dati.senato.it**, classe `osr:Emendamento`, grafi `emendamenti/{leg}_{part}`.

Una riga = un emendamento (URI unico). Contiene **numero**, **tipo**,
**ramo** (aula/commissione via `flagCommissione`), il **link ufficiale** al testo
(HTML + XML) e il bridge all'atto (`atto_num` = id in `http://dati.senato.it/ddl/N`).

## Relazione con `senato-akn/senato_emendamenti`

Sono **due strati dello stesso oggetto**, non due dataset concorrenti:

| | questo dataset (LOD) | `senato-akn/senato_emendamenti` |
|---|---|---|
| Cos'è | **indice/registro** ufficiale | **contenuto** (testo dal corpus AKN) |
| Copertura | Leg13–19 | Leg14–19 |
| Testo | ❌ (solo link) | ✅ `text_integrale` |
| Bridge atto | `atto_num` (ddl/N) | `atto_num` + `fase` |

**Join verificato** su un caso reale (atto 56260 / S.391):
`atto_num` = `ddl/N` = 56260, `emend_id` = `numero`, `ramo` ↔ `tipologia`
(`emend`/`emendc`). Conteggi identici: 119 = 119 (aula 47, commissione 72).

Chiave: `(legislatura, atto_num, emend_id, ramo)`.

## Limiti noti

- `atto_num` è **NULL** dove la fonte non collega l'oggetto a un ddl: Leg19 ~97%,
  Leg13 ~20%. Il `mart_per_atto` copre solo i collegati.
- Il WAF di `dati.senato.it` tronca a ~10k righe/risposta e rate-limita a burst.

## Estrazione

```bash
make run-senato-emendamenti-lod   # raw → clean → mart (una run per legislatura)
```

## Fonte

- `https://dati.senato.it/sparql` — `osr:Emendamento`, licenza CC BY 3.0
- Issue di intake: #109
