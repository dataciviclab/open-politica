# elezioni-comunali

## Issue
DataCivicLab/dataset-incubator#633

## Fonte dati
Eligendo — https://elezionistorico.interno.gov.it/
Open data DAIT: https://dait.interno.gov.it/elezioni/open-data

## Perimetro
35 anni, 154 tornate (1989-2024). Restano fuori:
- 1964, 1970, 1975, 1980, 1985, 1990: XLSX con Scrutini+Liste da joinare
- 2024-11-17, 2025, 2026: formato per sezione (Scrutini/Liste/LivSez)

## Schema raw
Colonne variabili per tornata (normalizzate via COL_MAP regex):
regione, provincia, comune, turno, elettori, votanti, lista, voti_lista,
seggi_lista, cognome, nome, data_nascita, sesso, cod_tipo_elettore,
voti_candidato.

`ensure_canonical` garantisce le 15 colonne di clean.sql: per 1989-1992
`turno`, `candidato` e `voti_candidato` restano vuoti.

## Formato fonti
- 1989-2021: TXT/CSV in ZIP (schema per epoca)
- 2022-06-12: XLSX (Scrutini Primo/Secondo Turno), `turno` iniettato
- 2022-11-27: TXT
- 2023: XLSX single-file
- 2024-06-09: ZIP con Scrutini + Liste separati (merge)
- 2024-07-28: CSV combinato in ZIP
- XLSX non gestiti: 1964-1990, 2024-11-17, 2025, 2026

## Codice condiviso
`datasets/_shared/eligendo.py` (`select_entries`, `read_table`, `merge_on`)
evita di duplicare download/ZIP/CSV/XLSX nei preprocess dei dataset elettorali.

## Encoding
UTF-8 con BOM o ISO-8859-1, delimitatore punto e virgola.

## Note
- Non tutti i comuni votano ogni anno: ogni comune ha elezioni ogni 5 anni.
- Molte annualità hanno più tornate (1989: 31, 1991: 24, 2019: 6).
- Alcuni ZIP (es. 2006, 2008) includono fogli XLSX accanto ai CSV;
  `iter_text_entries` filtra le entry non testuali.
