# camera_sindisp — Sindacato ispettivo della Camera (Leg13–19)

Atti di indirizzo e controllo della Camera: interrogazioni (scritta, orale,
in commissione), interpellanze, mozioni, risoluzioni e ordini del giorno.
Una riga per atto. I firmatari e i destinatari stanno nei dataset ponte
`camera_sindisp_firmatari` e `camera_sindisp_destinatari`.

## Dati

- **Fonte**: dati.camera.it — SPARQL, classe `ocd:aic` (default graph)
- **Licenza**: CC BY
- **Perimetro**: legislature XIII–XIX (1996–2026), multi-leg
- **Grano**: atto (URI `.../aic.rdf/...`), PK `atto_id`
- **Mirror Senato escluso**: gli URI con suffisso `_S` sono atti di origine
  Senato presenti nel LOD Camera e duplicano `senato_sindisp`

### Volumi (atti distinti, Camera-origin)

| Leg | Atti |
|---:|---:|
| 13 | 60.130 |
| 14 | 42.218 |
| 15 | 14.796 |
| 16 | 44.304 |
| 17 | 58.161 |
| 18 | 40.491 |
| 19 | 31.063 |
| **Totale** | **291.163** |

XIX legislatura per tipo (31.063 atti):
| Tipo | Atti |
|---|---:|
| Ordine del giorno | 10.495 |
| Interrogazione scritta | 9.344 |
| Interrogazione in commissione | 5.872 |
| Interrogazione orale | 2.953 |
| Interpellanza | 949 |
| Risoluzione | 843 |
| Mozione | 607 |

Risposte per legislatura (atti con `ocd:risposta`):
| Leg | Atti | Con risposta | % |
|---:|---:|---:|---:|
| 13 | 60.130 | 19.174 | 31,9% |
| 14 | 42.218 | 13.793 | 32,7% |
| 15 | 14.796 | 4.415 | 29,8% |
| 16 | 44.304 | 12.275 | 27,7% |
| 17 | 58.161 | 12.736 | 21,9% |
| 18 | 40.491 | 8.256 | 20,4% |
| 19 | 31.063 | 6.691 | 21,5% |

`risposta` è single-valued; `rif_delegato` può avere più valori (risposte
successive) ed è fuori da questo dataset. I dataset ponte contengono
**1.188.225** link firmatario (287.557 atti, 2.690 persone) e **308.058**
link destinatario (215.697 atti, 344 organi).

## Perché uno script (e non il source `sparql`)

Il plugin `sparql` del toolkit, in modalità keyset, inietta
`FILTER(?key > ...)` **dopo** la WHERE (prima di `ORDER BY`): Virtuoso lo
rifiuta con `SP030 syntax error at 'FILTER'`. Lo script
`scripts/extract_camera_sindisp.py` fa keyset manuale con il FILTER dentro
la WHERE.

Sul endpoint Camera sono emersi due comportamenti da tenere presenti:
- `FILTER` + `OPTIONAL` nella stessa WHERE può essere ignorato
  dall'ottimizzatore (verificato: il filtro `!STRENDS(..., "_S")` spariva
  con `BIND`/`OPTIONAL`). Il filtro sta in una **sottoquery senza OPTIONAL**;
  la sottoquery seleziona la pagina di URI, la query esterna aggiunge i metadati.
- `ORDER BY ?atto` e keyset su IRI non sono coerenti (l'ordine degli IRI in
  Virtuoso non è lessicografico). Si usa `ORDER BY STR(?atto)` e keyset su
  stringa.

I conteggi `COUNT(*)` su `ocd:aic` sono gonfiati da triple `rdf:type`
duplicate: il volume reale è il numero di **atti distinti** (tabella sopra).

## Query / colonne

`dc:type`, `dc:identifier`, `dc:date` (YYYYMMDD), `dc:title`,
`dc:description` (testo integrale), `ocd:ramo`, `ocd:primo_firmatario`
(+ label), `ocd:concluso`, `ocd:risposta`.

Mapping `tipo_categoria`: interrogazione scritta/orale/in commissione,
interpellanza, mozione, risoluzione, ordine del giorno.

## Limiti noti

- `dc:description` è il testo integrale (media ~3,6k caratteri; max ~105k):
  il clean pesa ~58 MB parquet per la sola Leg19.
- `ocd:ramo` è assente per Leg13/16; per quelle legislature tutti gli atti
  sono Camera-origin (nessun suffisso `_S`).
- Nessun link strutturato AIC→DDL trovato (`ocd:subject` non popolato sul
  perimetro): il collegamento ODG→disegno di legge richiede parsing del testo.
- `ha_risposta` dice solo che esiste un URI `ocd:risposta`; non misura la
  qualità né la tempestività della risposta.
- Il mirror Senato (`_S`) non è incluso: il confronto Camera/Senato va fatto
  in un compose con `senato_sindisp`.

## Rebuild

```bash
# pilota Leg19
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/camera-sindisp/dataset.yml --year 19
# multi-leg 13–19
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/camera-sindisp/dataset.yml
```
