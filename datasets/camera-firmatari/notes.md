# camera_firmatari — atto Camera → deputato firmatario

Collega gli **atti della Camera** ai **deputati firmatari** (URI joinabili).

## Proprietà usate

| Proprietà | Formato | Join |
|---|---|---|
| `ocd:altro_firmatario` | URI `deputato.rdf/d{id}_{leg}` | ✅ persona_id |
| `ocd:primo_firmatario` | URI | ✅ persona_id |
| `dc:contributor` | solo testo nome | ❌ non usato (no id) |

## Join utili

- `atto_id` → `camera_ddl.id_ddl` (da URI `ac{leg}_{id}`)
- `persona_id` → `camera_deputati.persona_id`
- `camera_voti.deputato_id` (stesso intero)

## Volume atteso

- Atti L19: ~6.3k · firmatari con URI su migliaia di atti
- UNION di due proprietà → dedup obbligatorio nel clean

## Limiti

- `dc:contributor` senza URI: fuori scope (serve NER o match nominativo)
- OFFSET Virtuoso non-deterministico → DISTINCT + ROW_NUMBER
- Multi-legislatura: `years: [13..19]`
