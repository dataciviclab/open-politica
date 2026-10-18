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

## Ponte ODG → DDL

Il numero del disegno di legge è nel titolo degli ODG
(`P.D.L. 9/00005-A/004`). Il clean estrae `ddl_numero`; i mart
`mart_odg_ddl` e `mart_odg_ddl_sintesi` fanno il join con `camera_ddl`
su `id_ddl` + `legislatura`.

| Leg | ODG | Con numero | Match DDL | % match | ODG su DL/bilancio | % DL/bilancio |
|---:|---:|---:|---:|---:|---:|---:|
| 13 | 4.856 | 4.168 | 3.132 | 64,5% | 911 | 18,8% |
| 14 | 8.273 | 7.377 | 7.377 | 89,2% | 4.610 | 55,7% |
| 15 | 3.202 | 2.084 | 2.084 | 65,1% | 1.463 | 45,7% |
| 16 | 9.152 | 8.132 | 8.132 | 88,9% | 6.314 | 69,0% |
| 17 | 16.759 | 13.667 | 13.667 | 81,6% | 7.518 | 44,9% |
| 18 | 12.638 | 11.159 | 11.159 | 88,3% | 9.544 | 75,5% |
| 19 | 10.495 | 10.004 | 9.981 | 95,1% | 7.107 | 67,7% |

Il link è **testuale**: copre gli ODG (95,1% in Leg19), non gli altri tipi.
Il DDL 2500 della Leg18 (DL 34/2020, "Rilancio") è il più contestato con 407
ODG; nella Leg18 il 75,5% degli ODG riguarda un DL o un bilancio.

## Limiti noti

- `dc:description` è il testo integrale (media ~3,6k caratteri; max ~105k):
  il clean pesa ~58 MB parquet per la sola Leg19.
- `ocd:ramo` è assente per Leg13/16; per quelle legislature tutti gli atti
  sono Camera-origin (nessun suffisso `_S`).
- Il link AIC→DDL è testuale (titolo `P.D.L.`): copre gli ODG, non gli altri
  tipi. I numeri DDL orfani (non presenti in `camera_ddl`) restano nel mart con
  `matched = false`.
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
