# senato-ddl

**Domanda guida:** Come nasce e muore una legge in Senato? Iter completo di un disegno di legge: presentazione, stato, tempi, fasi.

**Fonte:** Senato della Repubblica — OpenData SPARQL (`https://dati.senato.it/sparql`)
**Dataset:** graph `ddl/13`..`ddl/19` (legislature XIII-XIX, 1996-2026)
**Licenza:** CC BY 3.0

## Perché vale la pena

Complementare a `italia-corpus` (Normattiva = leggi vigenti): questo dà l'**iter parlamentare** dal deposito all'approvazione. Ddl mai approvati, tempi per stato, produttività legislativa — il cuore del processo legislativo.

Il campo `urn_normattiva` collega ogni DDL diventato legge alla sua URN:NIR su Normattiva, abilitando il bridge con `italia-corpus` (F5).

## Output

- `mart_stato`: ddl per stato dell'iter (approvati vs fermi)
- `mart_anno`: ddl per anno di presentazione
- `mart_iter_tempi`: tempi dell'iter per i ddl diventati legge

## Legislature coperte

| Legislature | Anni | DDL |
|---|---|---|
| XIII | 1996-2001 | 5.244 |
| XIV | 2001-2006 | 5.166 |
| XV | 2006-2008 | 5.023 |
| XVI | 2008-2013 | 5.160 |
| XVII | 2013-2018 | 5.203 |
| XVIII | 2018-2022 | 5.176 |
| XIX | 2022-2026 | 5.170 |
| **TOTALE** | | **36.142** |

## Stato

- **Stato**: legislature 13-19 complete, dati disponibili
- **Prossimo passo**: PR su open-politica
