# camera_sindisp_destinatari — destinatari degli atti di indirizzo e controllo

Una riga = (atto, organo di governo destinatario). Un atto può indirizzarsi a
più ministri. Include `ha_risposta` per il tasso di risposta per ministro.

## Dati

- **Fonte**: dati.camera.it — `ocd:aic` con `ocd:destinatario` e
  `ocd:risposta`
- **Perimetro**: Leg13–19, multi-leg
- **PK**: `(atto_id, destinatario_uri)`
- **Estratto con**: source `sparql` (keyset sintetico `atto|destinatario`,
  placeholder `{keyset}` nella sottoquery)

## Volumi (multi-leg 13–19)

- **308.058** righe (atto × destinatario)
- **215.697** atti distinti con destinatario
- **344** organi distinti

Top destinatari (tutte le legislature):
| Organo | Atti | % con risposta |
|---|---:|---:|
| Presidenza del Consiglio dei Ministri | 36.104 | 23,6% |
| Ministero dell'Interno | 35.603 | 28,1% |
| Ministero dell'Economia e delle Finanze | 23.235 | 28,1% |
| Ministero delle Infrastrutture e dei Trasporti | 17.994 | 40,7% |
| Ministero della Salute | 17.294 | 26,6% |
| Ministero del Lavoro e delle Politiche Sociali | 16.153 | 29,2% |
| Ministero della Giustizia | 14.300 | 32,0% |

## Join

- `atto_id` → `camera_sindisp.atto_id`
- `organo_id` = ultimo segmento di `organoGoverno.rdf/...` (es. `og182_624`);
  l'organo generico `og` è normalizzato a label `GOVERNO`
- `destinatario_label` = `rdfs:label` dell'organo (es. MINISTERO DELL'ISTRUZIONE)

## Mart

- `mart_per_ministro`: atti ricevuti, atti con risposta e percentuale per
  ministro e legislatura

## Limiti

- Il label può variare nel tempo (ministeri ridenominati): il join stabile è
  `organo_id`, non il label.
- `ha_risposta` replica il flag dell'atto: se un atto ha più destinatari,
  il flag è lo stesso per tutti.
- Non tutti gli atti hanno destinatario (Leg19: ~82%).
- La fonte può restituire `ocd:destinatario` troncato a
  `.../organoGoverno.rdf/og` (organo generico `GOVERNO`). Al 2026-11-02 erano
  **2.538** righe contro le **1.968** del pubblicato del 20/10: **1.402 atti**
  sono passati da un ministero specifico a `/og`. Per questo il totale può
  **calare** anche con atti nuovi. Non è perdita di righe: il
  `COUNT(DISTINCT atto|destinatario)` sul LOD coincide con l'estratto
  (28.014 per la XIX legislatura).
