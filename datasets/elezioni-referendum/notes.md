# elezioni-referendum

## Issue
DataCivicLab/dataset-incubator#633

## Fonte dati
Eligendo — https://elezionistorico.interno.gov.it/
Open data DAIT: https://dait.interno.gov.it/elezioni/open-data

## Schema raw
Colonne variabili per anno (normalizzate via COL_MAP regex):
- regione, provincia, comune, num_quesito, quesito, elettori, votanti, voti_si, voti_no, schede_bianche, ...

## Gap noti
- 1974, 1978, 1981, 1985: livello comunale
- 1987-2006: livello provinciale (colonna comune NULL)
- 2009 in poi: livello comunale
- 1985: ZIP senza riga di intestazione → schema posizionale `HEADERLESS_COLS`
- 1989 e 1991: un solo quesito su 95 province (per questo `min_rows` = 90)
- 2001: solo referendum costituzionale (Titolo V) — diverso dagli abrogativi
- 1946 (referendum istituzionale monarchia/repubblica): escluso, la fonte usa
  31 CIRCOSCRIZIONI senza REGIONE → candidato separato
- 2025 e 2026: ZIP con soli XLSX, non gestiti dal preprocess (serve supporto XLSX)

## Note
- I quesiti multipli per anno hanno lo stesso num_quesito per tutti i comuni
- I totali voti SI+NO nei dati sono la somma per tutti i quesiti dell'anno
