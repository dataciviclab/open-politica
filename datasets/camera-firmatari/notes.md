# camera_firmatari — atto Camera → deputato firmatario

Collega gli **atti della Camera** ai **deputati firmatari** (URI joinabili).

## Proprietà usate

| Proprietà | Formato | Join |
|---|---|---|
| `ocd:altro_firmatario` | URI `deputato.rdf/d{id}_{leg}` | ✅ persona_id |
| `ocd:primo_firmatario` | URI | ✅ persona_id |
| `dc:contributor` | solo testo nome | ❌ non usato (no id) |

## Join utili

- **`atto_id_leg`** = `{legislatura}_{atto_id}` (es. `19_2886`) — chiave stabile
- Join a `camera_ddl`: **`atto_id` + `legislatura`** (o `atto_id_leg`), **non** `atto_id` solo
  - I numeri restartano per legislatura (stesso pattern di `camera-ddl`)
- `persona_id` → `camera_deputati.persona_id`
- `camera_voti.deputato_id` (stesso intero)

## Volume atteso

- Atti L19: ~6.3k · firmatari con URI su migliaia di atti
- UNION di due proprietà → dedup obbligatorio nel clean

## Limiti

- `dc:contributor` senza URI: fuori scope (serve NER o match nominativo)
- OFFSET Virtuoso non-deterministico → DISTINCT + ROW_NUMBER
- Multi-legislatura: `years: [13..19]`
- **Rischio cross-leg**: join solo su `atto_id` senza `legislatura` è ambiguo
- Drop ~50% clean = dedup UNION/OFFSET (non perdita dati reali)
