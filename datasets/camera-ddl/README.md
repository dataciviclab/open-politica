# camera_ddl — iter legislativo della Camera dei Deputati

DDL (disegni di legge) presentati alla Camera dal 1948 alla XIX legislatura,
con stato dell'iter, firmatari e dates.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:atto`
- **Righe**: ~34k DDL unici (Leg13–19)
- **Legislature**: XIII (1996) – XIX (2026)
- **Campi**: `atto_camera`, `id_ddl`, `titolo`, `tipo`, `data_presentazione`,
  `legislatura`, `stato`, `primo_firmatario`, `anno`

## Pipeline

```
SPARQL (per-legislatura) → CSV → clean (dedup per id_ddl) → 3 mart
```

### Mart

| Tabella | Contenuto |
|---|---|
| `mart_stato` | Distribuzione DDL per stato iter (solo Leg16+, lo storico non ha lo stato) |
| `mart_anno` | DDL per anno di presentazione |
| `mart_firmatari` | Top firmatari per numero di DDL |

## Note tecniche

- **URI pattern**: `ac{LEG}_{NUM}` (es. `ac19_3095`) — il NUM è l'id_ddl
- **Stato iter**: disponibile solo per legislature recenti (Leg16+); le
  legislature vecchie hanno `stato = NULL`
- **Filtro**: solo `tipo = 'Progetto di Legge'` (esclusi Relazione e altri)
- **Dedup**: un DDL può avere versioni multiple (`-B` dopo navata) →
  teniamo la più recente per ogni `id_ddl`
- **Vincoli endpoint**: Virtuoso limita a 10k righe per query sorted;
  usiamo `GROUP BY` + `MAX()` senza `ORDER BY`

## Rebuild

```bash
cd datasets/camera-ddl
toolkit run --year {13..19}
```
