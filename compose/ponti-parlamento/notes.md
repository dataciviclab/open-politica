# ponti-parlamento — bridge atto ↔ persona ↔ ddl

KPI in formato lungo sui ponti estratti da open-politica.

## Pattern CI-safe (allineato #58)

- **raw**: `http_file` GCS → `senato_votazioni_oggetto`
- **support**: `type: external` URI GCS `{year}` (senato_ddl L19, voti, relatori, firmatari, dibattito, camera_ddl)
- **clean**: `read_parquet('{support.NAME.clean}')` — lista URL multi-year
- Nessun dataset sorgente rilanciato dal compose

## Metriche

| Ponte | Esempi |
|---|---|
| voti_ddl | n_votazioni_con_ddl, ddl_raggiunti, voti_individuali_su_ddl |
| relatori | n_relazioni, ddl_con_relatore |
| firmatari_camera | n_firmature, atti_in_camera_ddl, legislature_coperte |
| dibattito_camera | n_link, atti_distinti |

## Run

```bash
toolkit run -c compose/ponti-parlamento/dataset.yml -y 2026
```
