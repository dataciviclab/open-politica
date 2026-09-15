# camera_leggi — leggi approvate dalla Camera dei Deputati

Leggi pubblicate dalla Camera con ponte diretto verso Normattiva (URN) e
Gazzetta Ufficiale.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:legge`
- **Righe**: ~1.746 leggi (Leg13–19)
- **Legislature**: XIII (1996) – XIX (2026)
- **Campi**: `legge_camera`, `id_legge`, `titolo`, `tipo`, `data_promulgazione`,
  `legislatura`, `anno`, `urn_normattiva`, `gu_pubblicazione`, `ddl_numero`

## Ponte Normattiva

Ogni legge ha `ocd:lex` → URN Normattiva (100% copertura):
```
urn:nir:stato:legge:2026;145
```

Questo collega direttamente il Legal Graph (`normativa` nodes).

## Dati per legislature

| Leg | Leggi |
|---|---|
| 13 | 496 |
| 14 | 368 |
| 15 | 106 |
| 16 | 209 |
| 17 | 206 |
| 18 | 173 |
| 19 | 188 |

## Mart

| Tabella | Contenuto |
|---|---|
| `mart_tipo` | Distribuzione per tipo (Ordinaria, Costituzionale, etc.) |
| `mart_anno` | Leggi per anno di promulgazione |
| `mart_normattiva` | Copertura ponte Normattiva (con/ senza URN) |

## Rebuild

```bash
cd datasets/camera-leggi
toolkit run --year {13..19}
```
