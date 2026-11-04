# Elezioni Regionali 1970-2024 — risultati per comune

Risultati delle elezioni regionali italiane a livello comunale, da Eligendo (DAIT).

## Dati

**Periodo**: 1970-2024 (21 anni, 28 tornate)
**Righe totali**: ~962.000
**Qualità clean**: 100/100

| Anno | Tornate | Righe clean |
|---|---|---|
| 1970 | 07/06 | 59.077 |
| 1975 | 15/06 | 53.835 |
| 1980 | 08/06 | 64.051 |
| 1985 | 12/05 | 76.266 |
| 1990 | 06/05 | 91.672 |
| 1995 | 23/04 | 77.628 |
| 2000 | 16/04 | 103.120 |
| 2001 | 24/06, 11/11 | 7.871 |
| 2005 | 03/04, 17/04 | 100.670 |
| 2006 | 05/11 | 2.124 |
| 2008 | 14/12 | 4.114 |
| 2010 | 28/03 | 94.234 |
| 2013 | 24/02, 17/11 | 39.605 |
| 2014 | 25/05, 23/11 | 34.180 |
| 2015 | 31/05 | 35.999 |
| 2018 | 04/03 | 35.060 |
| 2019 | 10/02, 24/03, 26/05, 27/10 | 24.645 |
| 2020 | 26/01 | 10.299 |
| 2021 | 03/10 | 8.484 |
| 2023 | 12/02 | 24.125 |
| 2024 | 09/06 | 15.266 |

### Escluse
- **2011-10-16** e **2020-09-20**: file XLSX non gestiti dal toolkit
- **2024** (10/03, 21/04, 27/10, 17/11) e **2025**: formato per sezione
  (Scrutini + Preferenze), parser dedicato da fare

### Schema clean (12 colonne)

| Colonna | Tipo | Note |
|---|---|---|
| `data_elezione` | DATE | Data del voto |
| `regione` | VARCHAR | |
| `circoscrizione` | VARCHAR | |
| `provincia` | VARCHAR | |
| `comune` | VARCHAR | |
| `elettori` | BIGINT | |
| `votanti` | BIGINT | |
| `schede_bianche` | BIGINT | |
| `candidato` | VARCHAR | Cognome e nome candidato presidente (vuoto 1970-1990) |
| `voti_candidato` | BIGINT | Voti al candidato presidente (vuoto 1970-1990) |
| `lista` | VARCHAR | Lista di appoggio |
| `voti_lista` | BIGINT | Voti alla lista |

Dato normalizzato dal preprocess: nomi colonna unificati, encoding utf-8, numeri interi.

### Mart

- `mart_voti_lista_comune` — voti aggregati per lista × comune × elezione

## Cross con altri dataset del Lab

| Dataset | Chiave | Domanda |
|---|---|---|
| `bdap_lea` | regione | Spesa sanitaria e voto regionale |
| `irpef_comunale` | comune | Reddito e voto |
| `elezioni_politiche` (issue #523) | comune × anno | Correlazione voto politiche vs regionali |
| `popolazione_istat_comunale` | comune | Affluenza e demografia |

## Fonte

**Eligendo** — Archivio storico elettorale del DAIT (Ministero dell'Interno)
URL: https://elezionistorico.interno.gov.it/eligendo/opendata.php
Licenza: CC BY 4.0

## Issue

#588 — Intake eligendo: elezioni regionali 2018-2024
