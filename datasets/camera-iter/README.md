# camera-iter

**Iter legislativo della Camera dei Deputati** (Leg16–19): assegnazioni alle commissioni,
passaggi di stato, trasmissioni e richieste di parere.

Fonte: SPARQL `dati.camera.it` — Issue [#75](https://github.com/dataciviclab/open-politica/issues/75)

## Domanda

Come si muove un disegno di legge alla Camera? A quale commissione è assegnato, in quale sede,
con quali passaggi di stato e in quanto tempo? Quando viene trasmesso al Senato? Quanto lavoro
ricevono le commissioni?

## Dati

- **Copertura**: Legislature 16–19 (2008–2026). Il LOD Camera non espone l'iter per Leg13–15.
- **Granularità**: una riga = un evento (assegnazione, stato, trasmissione, parere).
  Le assegnazioni a commissioni riunite generano più righe per lo stesso evento.
- **Volumi LOD**: 114.222 eventi distinti (36.874 assegnazioni, 62.226 stati, 2.871 trasmissioni, 12.251 pareri).
- **Righe clean**: 126.667 (multi-organo espanso), 0 duplicati su `evento_id`; 114.222 eventi distinti dopo il fix `evento_id`.
- **`atto_id`**: 62.602 eventi (49,4%) — 50.223 via link inverso `attocamera`, 12.379 via `dibattito→atto`, 503 ambigui lasciati NULL.
- **Data**: 125.889 eventi (99,4%).
- **Unità di analisi**: evento; per l'analisi per atto usare `mart_iter_per_atto`.

## Output

| Layer | File | Chiave | Righe | Note |
|---|---|---|---:|---|
| Clean | `camera_iter_2026_clean.parquet` | `evento_id` | 126.667 | eventi normalizzati |
| Mart | `mart_iter_per_atto.parquet` | `(legislatura, atto_id)` | 12.341 | stato iniziale/finale, durata, conteggi |
| Mart | `mart_tempi.parquet` | `(tipo_evento, esito, anno)` | 509 | durate tra eventi consecutivi |
| Mart | `mart_commissioni.parquet` | `(legislatura, organo_id)` | 71 | assegnazioni e pareri per organo |

Colonne principali del clean: `evento_id, evento_uri, tipo_evento, legislatura, atto_id,
atto_source, data, data_anomala, organo_id, organo_label, sede, esito, target_uri, provenienza,
senato_atto_num, identifier`.

## Join

| Da | A | Chiave |
|---|---|---|
| `camera_iter` | `camera_ddl` | `atto_id` + `legislatura` |
| `camera_iter` | `camera_commissioni` | `organo_id` |
| `camera_iter` (parere) | `camera_commissioni` | `organo_id` (mappato per label) |
| `camera_iter` (trasmissione) | `senato_ddl` | `senato_atto_num` (2.871/2.871) |

## Copertura per legislatura

| Leg | Eventi | con `atto_id` | con `data` | con `organo_id` |
|---|---:|---:|---:|---:|
| 16 | 27.979 | 3.755 (13,4%) | 27.979 | 9.699 |
| 17 | 34.646 | 25.183 (72,7%) | 34.304 | 12.491 |
| 18 | 33.751 | 17.825 (52,8%) | 33.751 | 19.251 |
| 19 | 29.449 | 15.839 (53,8%) | 29.090 | 16.898 |

Pareri con `organo_id`: Leg16 3.528/3.599, Leg17 3.099/3.445, Leg18 2.536/2.536, Leg19 2.313/2.671.

## Limiti

- **Leg16**: i link `attocamera→assegnazione`/`statoIter` sono quasi assenti (17 e 78).
  Le assegnazioni sono recuperate in parte via `dibattito→rif_attoCamera` (145 eventi collegati),
  gli `statoIter` restano senza `atto_id`. `dc:identifier` non esiste su Leg16.
- **Leg19**: 358 `richiestaParere` puntano a `dibattito` vuoti (nessuna predicate): `data`/`organo_id`/`atto_id` NULL.
- **Link ambigui**: se un evento è collegato a più atti, `atto_id` è NULL e `atto_source='ambiguo'` (503 eventi).
- **Trasmissioni → Senato**: `rif_attoSenato` esiste solo Leg16/17; `senato_atto_num` è estratto dal titolo dove assente.
- **Pareri**: il LOD non espone l'organo; `organo_id` è ricavato per label normalizzata (Leg18 100%, Leg16 98%, Leg17 90%, Leg19 87%).
- **Date anomale**: 53 `statoIter` con `data` precedente all'inizio legislatura (9/18/20/6 per Leg16–19).
  Sono flaggate con `data_anomala=true` ed escluse da durate e stato iniziale/finale nei mart.
- **Commissioni riunite**: un'assegnazione a più organi produce più righe.

Vedi [notes.md](notes.md) per predicate, copertura link e verifiche puntuali.

## Comandi

```bash
# Estrazione (da datasets/camera-iter/)
python preprocess.py --legislature 16 17 18 19        # usa cache, riprende se interrotta
python preprocess.py --legislature 19 --refresh       # ignora cache
python preprocess.py --legislature 19 --build-only    # ricostruisce solo dai file in cache

# Run toolkit (dalla root del repo)
toolkit run raw   -c datasets/camera-iter/dataset.yml --years 2026
toolkit run clean -c datasets/camera-iter/dataset.yml --years 2026
toolkit run mart  -c datasets/camera-iter/dataset.yml --years 2026
```

In PowerShell servono `$env:PYTHONIOENCODING="utf-8"` e `$env:TOOLKIT_ALLOW_SCRIPT_SOURCE="1"`.

Test offline (senza endpoint): `python -m pytest tests/test_camera_iter_offline.py -q`.

## Stato

- [x] Predicate LOD verificate, scaffold allineato
- [x] Fix `evento_id` per URI non standard (`a19_19VII...`): 779 assegnazioni Leg19 recuperate
- [x] Run completo Leg16–19 (126.667 righe clean, 114.222 eventi distinti, 0 duplicati)
- [x] Mapping organi pareri robusto a varianti label (fix Leg18)
- [x] Flag `data_anomala` ed esclusione dai tempi
- [x] Mart e PK validati con toolkit
- [x] Test offline
- [ ] Review e PR
