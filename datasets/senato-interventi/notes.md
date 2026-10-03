# senato_interventi — chi parla in aula (Senato, Leg13–19)

Il senatore che prende la parola in aula/commissione: la dimensione "attività".

## Dati
- Fonte: dati.senato.it — `osr:Intervento` (graph composizione/{year}), Leg19 ~36k
- Una riga per intervento (URI), con `senatore_id`, `data`, `oggetto`, `legislatura`
- La data è della seduta (`osr:dataSeduta`)

## 2026-10-02 — Pattern C multi-legislature

- `years: [13..19]`, query `GRAPH <.../composizione/{year}>`
- Clean: `{year} AS legislatura`; min_rows 5000 (per-leg)
- pages: 10 (Leg13/14/17 hanno superato 50k con pages=5)

## Numeri (riferimento Leg19)
- Per anno: ~9-10k (2023-2026), 2022 parziale (971), ~195 parlanti/anno
- Top: Calandrini 1.598, Balboni 1.077, Tosato 895

## Note tecniche
- `dataSeduta` è in un graph diverso da `composizione/{year}` → il pattern va
  messo FUORI dal GRAPH (altrimenti la data resta NULL)
- `FILTER(isIRI(?int))` esclude gli interventi bnode (commissione)
- Dedup su intervento_id

## Rebuild
make run-senato-interventi

## 2026-10-03 — Pipeline

- Perimetro multi-leg (Pattern C); I–XII non nel LOD dove applicabile.
- La pipeline su **push a main** (`datasets/**`) rilancia run + sync GCS
  di questi dataset (workflow `Pipeline`, `detect-paths: datasets compose`).
- Rebuild manuale: `toolkit run -c datasets/<slug>/dataset.yml` dalla root repo.
