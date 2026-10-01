# camera_atti_dibattito — atto Camera ↔ dibattito/abbinamenti

Collega gli **atti** ai **dibattiti** e **abbinamenti** Camera.

## Proprietà usate

| Proprietà | Significato |
|---|---|
| `ocd:rif_dibattito` | atto → dibattito (discussione) |
| `ocd:rif_abbinamento` | atto → abbinamento |
| `ocd:rif_attoCameraAbbinato` | atto → altro atto abbinato |

## Join utili

- **`atto_id_leg`** = `{legislatura}_{atto_id}`
- Join a `camera_ddl`: **`atto_id` + `legislatura`**, non `atto_id` solo
- `target_uri` dibattito → eventuale dataset interventi/discorsi (non in questa PR)

## Copertura legislature

| Leg | rif_dibattito | rif_abbinamento | rif_attoCameraAbbinato |
|---:|---:|---:|---:|
| 13–14 | 0 | 0 | 0 |
| 15 | 0 | 0 | ~5k |
| 16–19 | sì | sì | 0 |

→ `years: [15..19]` (L13–14 non hanno queste proprietà sul graph).

## Limiti

- Non estrae interventi/discorsi dentro il dibattito (solo il link)
- OFFSET non-deterministico → DISTINCT + ROW_NUMBER
- **Rischio cross-leg**: join solo su `atto_id` senza `legislatura` è ambiguo
- L15 (solo `rif_attoCameraAbbinato`): link atto↔atto abbinato, non dibattito in senso stretto
- Drop ~50% clean = dedup UNION/OFFSET
