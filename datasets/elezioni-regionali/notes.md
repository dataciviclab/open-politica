# Note tecniche — elezioni-regionali

## Struttura

```
datasets/elezioni-regionali/
├── dataset.yml        # script source multi-anno
├── preprocess.py      # download, unzip, normalizza
├── sql/
│   ├── clean.sql      # schema unificato 12 colonne
│   └── mart.sql       # aggregazione lista × comune
├── README.md
└── notes.md
```

## Perimetro

21 anni, 28 tornate (1970-2024). Esclusi:
- **2011-10-16** e **2020-09-20**: la fonte pubblica solo XLSX.
- **2024**: coperta solo la tornata del 09/06 (Piemonte); le altre 4 date
  (10/03, 21/04, 27/10, 17/11) usano il formato per sezione
  (Scrutini + Preferenze) non gestito dal parser attuale.
- **2025**: formato nuovo (SCRUTINI/PREFERENZE/VOTANTI + `dato per sezione/`).

## Mappa fonti

| Periodo | File principale | Note |
|---|---|---|
| 1970-1990 | `regionali-YYYYMMDD.txt` | solo liste, nessun candidato |
| 1995-2015 | `regionali-YYYYMMDD.txt` | liste + candidato |
| 2001-06-24 | `regionali-20010624.csv` (in ZIP) | schema abbreviato REG/CIRC/PROV |
| 2008 | `regionali-20081214.txt` | `VOTICANDIDLEADER`, `ELETTORI_M` |
| 2015 | `regionali-20150531.txt` | aggiunge `CIRCOSCRIZIONE` |
| 2018-2024 | vari | vedi README |

## Variazioni schema raw normalizzate

| Concetto | 1970-1990 | 1995-2015 | 2001-06 | 2008 | 2021-2024 |
|---|---|---|---|---|---|
| Regione | `REGIONE` | `REGIONE` | `REG` | `REGIONE` | `REGIONE`/`REG` |
| Circoscrizione | — | 2015: `CIRCOSCRIZIONE` | `CIRC` | — | `CIRCOSCRIZIONE`/`CIRC` |
| Provincia | `PROVINCIA` | `PROVINCIA` | `PROV` | `PROVINCIA` | `PROVINCIA`/`PROV` |
| Elettori | `ELETTORI` | `ELETTORI` | `ELETTORITOT` | `ELETTORI` | `ELETTORI(TOT)` |
| Voti candidato | — | `VOTI_CANDIDATO` | `VOTICANDIDATO` | `VOTICANDIDLEADER` | `VOTICAND…` |
| Lista | `LISTA` | `LISTA` | `DESCRLISTA` | `LISTA` | `LISTA`/`DESCRLISTA` |
| Voti lista | `VOTI_LISTA` | `VOTI_LISTA` | `VOTILISTA` | `VOTILISTA` | `VOTI_LISTA`/`VOTILISTA` |

`main()` garantisce sempre le 12 colonne di `clean.sql` (anche quando la tornata
non le porta): per 1970-1990 `candidato` e `voti_candidato` restano vuoti.

### Formato numeri
- 2018-2021: comma decimale (`5849,00`) — normalizzato a interi
- 2023-2024: interi diretti

### Encoding
- 2019-05-26 (Piemonte): ISO-8859-1
- Tutti gli altri: ASCII / UTF-8
- Preprocess: UTF-8 → latin-1 → cp1252

## Note implementative

### Perché preprocess invece di http_file diretto
- URL diversi per tornata
- ZIP con 2 file di cui serve solo 1 (scrutini)
- Nomi colonna e formati numerici variano per anno
- Encoding misto

### TOOLKIT_ALLOW_SCRIPT_SOURCE
Il source type `script` è disabilitato di default per sicurezza.
Va attivato con `TOOLKIT_ALLOW_SCRIPT_SOURCE=1` nell'ambiente di run.

### Esclusioni
- **2011-10-16** e **2020-09-20**: file XLSX.
- **2024 (altre date) e 2025**: formato per sezione, parser dedicato da fare.
- **File preferenze**: ogni ZIP ha un secondo file con le preferenze ai
  consiglieri. Non incluso nel perimetro.

## Verifica

```bash
cd open-politica
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/elezioni-regionali/dataset.yml
```

## Output pipeline

| Anno | Righe clean |
|---|---|
| 1970 | 59.077 |
| 1975 | 53.835 |
| 1980 | 64.051 |
| 1985 | 76.266 |
| 1990 | 91.672 |
| 1995 | 77.628 |
| 2000 | 103.120 |
| 2001 | 7.871 |
| 2005 | 100.670 |
| 2006 | 2.124 |
| 2008 | 4.114 |
| 2010 | 94.234 |
| 2013 | 39.605 |
| 2014 | 34.180 |
| 2015 | 35.999 |
| 2018 | 35.060 |
| 2019 | 24.645 |
| 2020 | 10.299 |
| 2021 | 8.484 |
| 2023 | 24.125 |
| 2024 | 15.266 |
| **Totale** | **~962.000** |

## Cross-repo

Issue: https://github.com/DataCivicLab/dataset-incubator/issues/588
Scorporata da: https://github.com/DataCivicLab/dataset-incubator/issues/523
Fonte SO: `eligendo` (radar-only)
