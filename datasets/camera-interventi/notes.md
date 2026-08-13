# camera_interventi — chi parla in aula (Camera, XIX leg.)

Il deputato che prende la parola in aula/commissione: la dimensione "attività".

## Dati
- Fonte: dati.camera.it — `ocd:intervento`, 94.294 interventi deputati con data
- Una riga per intervento (URI), con `deputato_id`, `data`, `titolo`
- La data è quella della discussione (`dc:date` del `rif_intervento`)

## Numeri
- Per anno: ~27-30k (2023-2025), 2022 parziale (5k), ~375 parlanti/anno
- Top (2026): Pagano 149, Gusmeroli 144, Rotelli 131

## Note / limiti
- Solo interventi con `rif_deputato` E data discussione → esclusi gli interventi
  di membri del governo (`rif_membroGoverno`) e quelli senza data (~25% del
  totale class). Il conteggio esatto della classe è 126k, noi 94k.
- Partizione per anno sulla data discussione (`{year}`) + dedup su intervento_id
- L'atto/tema esatto (discussione) non è incluso nel clean

## Rebuild
make run-camera-interventi
