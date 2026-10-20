# camera-iter — Iter legislativo Camera (Leg16–19)

## Fonte e classi

- Endpoint: `https://dati.camera.it/sparql` (Virtuoso, grafo `http://dati.camera.it/ocd/`)
- Licenza: CC BY
- Source Observatory: `dati_camera` (radar GREEN; endpoint intermittente, 502/503/500)

Quattro classi OCD, partizionate per prefisso URI (la legislatura **non** è sempre nel grafo):

| Classe | Prefisso URI | Leg16 | Leg17 | Leg18 | Leg19 | Totale |
|---|---|---:|---:|---:|---:|---:|
| `ocd:assegnazione` | `a{leg}_{n}` | 6.220 | 9.493 | 11.240 | 9.921 | 36.874 |
| `ocd:statoIter` | `si{leg}_{n}` | 16.943 | 19.816 | 13.823 | 11.644 | 62.226 |
| `ocd:trasmissione` | `tr{leg}_{n}` | 716 | 930 | 677 | 548 | 2.871 |
| `ocd:richiestaParere` | `rp{leg}_{n}` | 3.599 | 3.445 | 2.536 | 2.671 | 12.251 |

Volumi verificati il 2026-10-19. Corrispondono alle specifiche dell'issue #75.

## Predicate reali (verificate)

| Classe | Predicate presenti | Note |
|---|---|---|
| `assegnazione` | `ocd:rif_organo`, `ocd:rif_dibattito`, `ocd:sede`, `ocd:dataAssegnazione`, `dc:date`, `dc:identifier`, `dc:title`, `rdfs:label` | `dataAssegnazione` (7.057/9.921 su Leg19) meglio di `dc:date` (2.857). Multipli `rif_organo` → commissioni riunite |
| `statoIter` | `dc:date`, `dc:type`, `dc:title`, `rdfs:label` | **Nessun** `rif_leg`, `rif_atto` né `dc:identifier`: legislatura solo dall'URI |
| `trasmissione` | `dc:date`, `dc:type`, `dcterms:provenance`, `dc:title`, `rdfs:label` | **Non** `ocd:provenienza`. `ocd:rif_attoSenato` solo Leg16 (466) e Leg17 (78); **zero** su Leg18/19 |
| `richiestaParere` | `ocd:rif_dibattito`, `ocd:esito` (2.482/2.671), `dc:title`, `rdfs:label` | **Nessun** `rif_organo`, **nessuna** `dc:date` |
| `organo` | `rdfs:label` | elenco `organo.rdf/o{leg}_` (74/77/68/84 per Leg16–19) |

## Collegamento all'atto

Il nodo centrale è `ocd:atto` (`attocamera.rdf/ac{leg}_{num}`), che punta agli eventi con
`rif_assegnazione`, `rif_statoIter`, `rif_trasmissione`, `rif_richiestaParere`.
Il collegamento è **solo inverso**: gli eventi non hanno `rif_atto`.

Due strade di recupero:

1. **link inverso `attocamera`** (fonte primaria).
2. **fallback `dibattito → ocd:rif_attoCamera`**, usato per assegnazioni e pareri quando il link
   diretto manca (fondamentale su Leg16 e utile su tutte le legislature).

`atto_source` distingue la provenienza: `attocamera` (50.223), `dibattito` (12.379),
`ambiguo` (503), NULL (62.720).

**Regola ambiguità**: se un evento è collegato a più di un atto, `atto_id` resta NULL e
`atto_source='ambiguo'`. Ambigui per leg/tipo: Leg16 asn 112, trs 1; Leg17 asn 302, trs 15;
Leg18 asn 46, stato 11, trs 5; Leg19 asn 5, stato 4, trs 2.

Copertura `atto_id` finale (leg / con atto / totale):

| Classe | Leg16 | Leg17 | Leg18 | Leg19 |
|---|---|---|---|---|
| assegnazione | 145 / 6.721 | 5.598 / 10.455 | 3.815 / 16.715 | 3.075 / 14.586 |
| statoIter | 78 / 16.943 | 15.733 / 19.816 | 10.993 / 13.823 | 9.978 / 11.644 |
| trasmissione | 4 / 716 | 762 / 930 | 482 / 677 | 473 / 548 |
| richiestaParere | 3.528 / 3.599 | 3.090 / 3.445 | 2.535 / 2.536 | 2.313 / 2.671 |

**Leg16**: `attocamera→assegnazione`/`statoIter` quasi assenti (17 e 78). Per le assegnazioni il
fallback `dibattito→atto` recupera 128 eventi non ambigui (145 totali con `atto_id`); gli
`statoIter` restano senza atto (limite del LOD).

## Estrazione (`preprocess.py`)

- Partizione per legislatura (16–19), prefisso URI esplicito.
- **Due fasi**: prima gli URI (`fetch_ids`, keyset `?s > ultimo`), poi i dettagli in batch
  `FILTER(?s IN (...))`. OFFSET profondo su righe larghe manda Virtuoso in 500.
- **Robustezza**: preflight `endpoint_alive` (esce con codice 2 se irraggiungibile), retry con
  backoff esponenziale e jitter, cache incrementale per pagina/batch con marker di completamento,
  verifica `COUNT DISTINCT` e ripresa automatica dopo interruzioni.
- Cache per `(legislatura, classe)` in `_cache/` (`.gitignore`); `--refresh` per ignorare.
- Flag: `--build-only` (ricostruisce dai file in cache), `--no-verify` (salta i controlli di completezza).
- Link atto estratti a parte con keyset `(?a, ?e)`; elenco organi per legislatura.
- Output: `camera_iter.parquet` con
  `evento_id, evento_uri, tipo_evento, legislatura, atto_id, atto_source, data, data_anomala,
  organo_id, organo_label, sede, esito, target_uri, provenienza, senato_atto_num, identifier`.

## Clean

- Dedup su `evento_id` (ordinamento deterministico per `data DESC, atto_id DESC, evento_uri`).
- Date `YYYYMMDD` → DATE (fix regex: il quantificatore `{8}` era corrotto da una f-string).
- `richiestaParere`: `organo_id` ricavato per label normalizzata (accenti, apostrofi, spazi,
  parentesi) dalla mappa delle assegnazioni della stessa legislatura.
  Il fix `'(' → ' ('` allinea varianti tipo `I Commissione(Affari...)` (Leg18) a
  `I COMMISSIONE (AFFARI...)`, portando Leg18 dal 6% al 100% di copertura.
- `senato_atto_num`: numero Senato da URI (`rif_attoSenato`) o dal titolo (`S. 393`) → 2.871/2.871.
- `data_anomala`: `data < inizio legislatura` (Leg16 2008-04-29, Leg17 2013-03-15,
  Leg18 2018-03-23, Leg19 2022-10-13) → 53 eventi (tutti `statoIter`: 9/18/20/6).

## Mart

1. `mart_iter_per_atto` — PK `(legislatura, atto_id)`: stato iniziale/finale, n_eventi, durata, conteggi per tipo. Usa `COUNT(DISTINCT evento_uri)` e ignora `data_anomala` per date/stato.
2. `mart_tempi` — PK `(tipo_evento, esito, anno)`: durate tra eventi consecutivi dello stesso atto; filtra `esito IS NOT NULL` e `NOT data_anomala`.
3. `mart_commissioni` — PK `(legislatura, organo_id)`: assegnazioni, pareri, atti toccati.

## Run finale (2026-10-19)

- 125.825 righe clean, 0 duplicati: Leg16 27.979, Leg17 34.646, Leg18 33.751, Leg19 29.449.
- 62.602 con `atto_id` (49,8%), 125.053 con `data` (99,4%).
- `mart_iter_per_atto`: 12.341 righe, 0 duplicati PK; date 2008-05-07 → 2026-10-16.
- `mart_tempi`: 509 righe; durata max 1.730 giorni.
- `mart_commissioni`: 71 righe.
- Pipeline toolkit `raw`/`clean`/`mart` validate `ok=True`; `ruff` e test offline puliti.

## Cautele

- **Leg16**: iter quasi non collegato agli atti (limite del LOD); `statoIter` senza `atto_id`.
- **Leg19**: 358 `richiestaParere` con `dibattito` vuoto → nessuna data/organo/atto.
- **Trasmissioni → Senato**: `rif_attoSenato` assente su Leg18/19; numero recuperato dal titolo.
- **Date anomale**: 53 `statoIter` pre-legislatura, flaggate e escluse dai tempi.
- **Multi-organo**: assegnazioni in commissioni riunite → più righe per evento (documentato).
- **Endpoint instabile**: retry con backoff; cache obbligatoria per run lunghi.
