# dait-amministratori-storico

Serie storica annuale dell'Anagrafe degli Amministratori Comunali (DAIT) — snapshot al 31/12 di ogni anno, 1986–2025.

**Fonte**: Ministero dell'Interno — Dipartimento per gli Affari Interni e Territoriali
- **URL pagine**: https://dait.interno.gov.it/elezioni/open-data (archivio open-data)
- **File**: `storico_amministratori_comuni3112YYYY.csv` per ogni anno (naming variabile)

## Domanda

*Come è cambiata la classe politica comunale italiana in 40 anni? Quante donne, che età, quali profili tra sindaci, assessori e consiglieri? Come si è ridotta o trasformata la mappa degli enti?*

Sotto-domande esplorative:
- Come è cresciuta la presenza femminile negli enti locali dal 1986 a oggi?
- Sono invecchiati o rimpianzionati sindaci e assessori?
- Quanti comuni avevano organi straordinari (commissioni, commissari) e quando?
- Come è cambiata la composizione per titolo di studio e professione?

## Dataset

- **Fonte**: 40 CSV annuali dal portale DAIT, uniti da `preprocess.py`
- **Granularità**: 1 riga = 1 amministratore in 1 carica in 1 comune, allo snapshot del 31/12 dell'anno
- **Periodo**: 1986–2025 (40 anni, zero gap)
- **Righe**: 6.075.430 totali (~125k–198k per anno)
- **Colonne (36)**: anno_snapshot, territorio (codici DAIT + ISTAT), popolazione, contesto elezione, persona (anagrafica), carica (date inizio/cessazione, incarico, funzione), lista, titolo di studio, professione

### Le due ere schema

Il DAIT ha cambiato schema nel 2023. `preprocess.py` le unifica:

| | Era A (1986–2022) | Era B (2023–2025) |
|---|---|---|
| Colonne raw | 28 | 34 |
| Inizio carica | `DATA_NOMINA` | `DATA_INIZIO_CARICA` |
| Lista | `PARTITO_LISTA_COALIZIONE` | `LISTA_APPARTENENZA/COLLEGAMENTO` |
| Popolazione | `POPOLAZIONE_CENSITA` | `POPOLAZIONE_CENSITA_ALLA_DATA_ELEZIONE` |
| Extra Era B | — | `CONSIGLIERI_ELETTI`, `INCARICO`+date, `FUNZIONE`+date |

Encoding misti: utf-8 parziali + latin-1 nel blocco ~2010–2022 — gestito da `smart_decode`.

## Mart

| Mart | Descrizione |
|---|---|
| `mart_genere_anno` | Quota femminile per anno — il trend storico |
| `mart_profilo_anno` | Profilo per anno × carica (n, età media, % femmine) |

### Trend chiave (da mart)

| Anno | % donne (totale) | Sindaci F | Sindaci età media |
|---|---|---|---|
| 1986 | 6,7% | 2,7% | 45,7 |
| 1995 | 17,5% | 6,3% | 46,2 |
| 2005 | 16,9% | 9,7% | 49,9 |
| 2015 | 28,4% | 13,7% | 51,7 |
| 2025 | 35,3% | 15,3% | 55,1 |

## Esecuzione

```bash
cd open-politica
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/dait-amministratori-storico/dataset.yml
```

Il run scarica ~1,4 GB (40 CSV) e richiede ~8 minuti. `TOOLKIT_ALLOW_SCRIPT_SOURCE=1` è necessario per lo script source (già esportato dal Makefile del repo).

## Relazione con dait_amministratori_locali

- `dait_amministratori_locali`: snapshot corrente "in carica", 3 livelli (comune/provincia/regione)
- `dait_amministratori_storico`: serie annuale solo comuni, 40 anni — la profondità temporale che al corrente manca
