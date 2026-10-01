# camera_atti_dibattito — atto Camera ↔ dibattito/abbinamenti

Collega gli **atti** ai **dibattiti** e **abbinamenti** Camera.

## Proprietà usate

| Proprietà | Significato |
|---|---|
| `ocd:rif_dibattito` | atto → dibattito (discussione) |
| `ocd:rif_abbinamento` | atto → abbinamento |
| `ocd:rif_attoCameraAbbinato` | atto → altro atto abbinato |

## Join utili

- `atto_id` → `camera_ddl.id_ddl` / `camera_firmatari.atto_id`
- `target_uri` dibattito → eventuale dataset interventi/discorsi (non in questa PR)

## Volume atteso

- L19: ~35k link atto→dibattito (probe live)
- UNION di 3 proprietà → dedup nel clean

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
