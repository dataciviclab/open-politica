# osservatorio_parlamento — KPI del Parlamento come istituzione

La "pagella del Parlamento": indicatori per legislatura/anno che rispondono
a *"il Parlamento funziona?"*, non al singolo parlamentare.

## Formato

Tabella lunga `(periodo, dimensione, kpi, valore, fonte)`, interrogabile e
pivottabile.

| Dimensione | KPI | Copertura |
|---|---|---|
| **produzione** | ddl_presentati, ddl_approvati, pct_conversione, pct_iniziativa_governativa, **pct_approvati_governativi**, giorni_iter_medio | Senato, XIX |
| **votazioni** | n_votazioni, pct_approvate | Camera (per anno) e Senato (per anno) |
| **fiducia** | n_fiducia | Camera, per anno |
| **partecipazione** | pct_voti_espressi | Camera, per anno |
| **rappresentanza** | n_deputati, pct_donne | Camera, TUTTE le legislature (regno+repubblica) |
| **gruppi** | n_membership, senatori_con_cambi | Senato, XIX |

## Primi numeri (XIX leg.)

- **Produzione**: 5.165 DDL presentati, 733 approvati (14,2% di conversione);
  **36,4% delle leggi approvate di iniziativa governativa**; iter medio 348 giorni
- **Rappresentanza**: donne 11,5% (XIV) → 20,5% (XVI) → 30,7% (XVII) → 36,4% (XVIII)
- **Fiducia Camera**: 26 nel 2023, 17 nel 2024, 15 nel 2025
- **Gruppi**: 59 senatori hanno cambiato gruppo (transfughi)

## Limiti / prossimi passi

- Il "decide o ratifica" è ancora **incompleto**: mancano i **decreti-legge**
  (il governo che legifera da solo + conversioni) e il lato Camera della
  produzione. Con i decreti, `pct_approvati_governativi` salirà di molto
  (Openpolis misura ~75%)
- `pct_iniziativa_governativa` (7,6%) è sul PRESENTATO — basso perché i
  parlamentari presentano tantissimi DDL che non passano; il KPI giusto è
  `pct_approvati_governativi`
- rappresentanza solo Camera (manca senato storico)
- produzione solo Senato (manca Camera DDL)

## Rebuild

```bash
make run-osservatorio-parlamento
```
