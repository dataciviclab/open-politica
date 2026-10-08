# camera_relatori — relatori della Camera (Leg13–19)

Il **relatore** è il deputato che segue e "dirige" uno specifico atto in
commissione: scrive la relazione, gestisce gli emendamenti, lo porta in aula.
È il *regista politico* di ogni legge — la fase 3 dell'iter, dal lato che
produce.

## Dati

- **Fonte**: dati.camera.it — SPARQL, `ocd:relatore`, filtro URI `rel{year}_`
- **Righe**: Leg19 ~10.360 incarichi · **1.000+ deputati** coinvolti
- **Campi**: `relatore_id`, `deputato_id`, `data`, `tipo`, `legislatura`,
  **`atto_camera`**, **`atto_id`**, **`atto_legislatura`**, **`atto_id_leg`** (#62)
- La `data` è quella della discussione (`dc:date` in cui il relatore ha
  riferito in commissione)

## 2026-10-08 — Chiave atto (#62)

- Seconda source SPARQL: `?atto a ocd:atto ; ocd:rif_relatore ?rel` →
  URI `attocamera.rdf/ac{leg}_{id}`
- **Correzione query issue**: `ocd:rif_deputato` non è su `?atto`
  (COUNT=0) — resta sulla source discussione; join su `relatore_id`.
- `read.mode: all` (union_by_name discussione + atto), stesso pattern di
  `camera_leggi`; clean aggrega per `relatore_id` (max campi).
- Colonne: `atto_camera` (URI), `atto_id`, `atto_legislatura`,
  `atto_id_leg` (`{leg}_{id}`) — allineate a `camera_firmatari`
- **Limite misurato (Leg19 run locale)**: **1.936 / 10.413** relatori
  con `atto_camera` non null = **18,6%**. La stima issue (~45%) contava
  righe atti, non relatori distinti dopo dedup. Il resto resta
  senza atto LOD pulito — non bloccante, da dichiarare nei consumer.
- **Grain atto**: per relatore_id con più atti LOD (media ~2.4) resta
  **un solo atto representative** (`max(atto_camera)` = URI
  lessicograficamente maggiore). Non è semantico: per legal-graph l'edge
  relatore Camera punta a un atto representative, non all'insieme.
  Espandere le righe (1 relatore × N atti) romperebbe la PK
  `relatore_id` — fuori scope #62, se mai serve va ripensato il grain.

## 2026-10-02 — Pattern C multi-legislature

- `years: [16,17,18,19]` — **LOD Camera ha solo rel16_..rel19_** (rel13/14/15 = 0 live)
- Query `FILTER(CONTAINS(STR(?rel), "rel{year}_"))`
- Clean: `{year} AS legislatura`; min_rows 1000 (per-leg)
- pages: 2 (Leg19 ~10k > cap 10k; storiche sotto il cap)

## Numeri (riferimento Leg19)

- **Top relatori**: Sbardella 226, Russo 201, Tremaglia 183, Maschio 181,
  Mascaretti 170 — i "registi" che seguono decine di leggi
- **Per anno**: picco 2023 (3.196 incarichi, 245 deputati), poi 2.900/anno
- Nel profilo: `n_relatori` e `anni_relatore` per ogni deputato

## Note / limiti

- La source **atto diretto** (#62) copre **~18,6%** dei relatori Leg19
  (1.936/10.413 con atto non null — run 2026-10-08); il resto resta
  senza atto LOD — non bloccante, da dichiarare nei consumer.
- `relatore_id` = URI (chiave unica); una riga per relatore nel clean
  (max di data/tipo/atto — la data è quella della discussione se presente)

## Rebuild

```bash
make run-camera-relatori
```

## 2026-10-03 — Pipeline

- Perimetro multi-leg (Pattern C); I–XII non nel LOD dove applicabile.
- La pipeline su **push a main** (`datasets/**`) rilancia run + sync GCS
  di questi dataset (workflow `Pipeline`, `detect-paths: datasets compose`).
- Rebuild manuale: `toolkit run -c datasets/<slug>/dataset.yml` dalla root repo.
