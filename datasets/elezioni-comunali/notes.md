# elezioni-comunali

## Issue
DataCivicLab/dataset-incubator#633

## Fonte dati
Eligendo — https://elezionistorico.interno.gov.it/
Open data DAIT: https://dait.interno.gov.it/elezioni/open-data

## Perimetro
33 anni, 149 tornate (1989-2024). Esclusi perché solo XLSX:
1964, 1970, 1975, 1980, 1985, 1990, 2022, 2023, 2025, 2026.
Esclusa 2024-11-17 (formato per sezione).

## Schema raw
Colonne variabili per tornata (normalizzate via COL_MAP regex):
regione, provincia, comune, turno, elettori, votanti, lista, voti_lista,
seggi_lista, cognome, nome, data_nascita, sesso, cod_tipo_elettore,
voti_candidato.

`ensure_canonical` garantisce le 15 colonne di clean.sql: per 1989-1992
`turno`, `candidato` e `voti_candidato` restano vuoti.

## Formato fonti
- 1989-2021: TXT/CSV in ZIP (schema per epoca)
- 2024-06-09: ZIP con Scrutini + Liste separati (merge)
- 2024-07-28: CSV combinato in ZIP
- XLSX (esclusi): 1964-1985, 1990, 2022-2023, 2025-2026

## Encoding
UTF-8 con BOM o ISO-8859-1, delimitatore punto e virgola.

## Note
- Non tutti i comuni votano ogni anno: ogni comune ha elezioni ogni 5 anni.
- Molte annualità hanno più tornate (1989: 31, 1991: 24, 2019: 6).
- Alcuni ZIP (es. 2006, 2008) includono fogli XLSX accanto ai CSV;
  `iter_text_entries` filtra le entry non testuali.
