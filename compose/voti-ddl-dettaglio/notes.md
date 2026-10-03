# voti_ddl_dettaglio — join disaggregato voti × DDL (Senato XIX)

Una riga = **voto individuale** su una votazione che ha `ddl_id` (osr:idDdl).

## Pattern CI-safe (allineato #58)

- **raw**: `http_file` GCS → `senato_votazioni_oggetto`
- **support**: `type: external` URI GCS (senato_votazioni 2026, senato_ddl L19, anagrafica 2026)
- **clean**: `read_parquet('{support.NAME.clean}')` + dedup ROW_NUMBER
- **Solo 2026/XIX** — niente multi-year su voti individuali (RAM)

## Join

```text
senato_votazioni_oggetto (ddl_id not null)
  ⋈ senato_votazioni ON votazione_id
  LEFT JOIN senato_ddl (id_ddl = ddl_id, dedup fasi)
  LEFT JOIN anagrafica
```

## Output

| Mart | Contenuto |
|---|---|
| `mart_voti_ddl` | dettaglio voto×atto (~349k) |
| `mart_voti_ddl_sintesi` | per ddl: n_voti, n_senatori, F/C/A |

## Run

```bash
toolkit run -c compose/voti-ddl-dettaglio/dataset.yml -y 2026
```
