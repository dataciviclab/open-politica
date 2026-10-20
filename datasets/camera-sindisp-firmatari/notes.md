# camera_sindisp_firmatari — firmatari degli atti di indirizzo e controllo

Una riga = (atto, firmatario, ruolo). Ruolo `primo` o `altro`.
Ponte tra `camera_sindisp.atto_id` e `camera_deputati_legislature.persona_id`.

## Dati

- **Fonte**: dati.camera.it — `ocd:aic` con `ocd:primo_firmatario` e
  `ocd:altro_firmatario`
- **Perimetro**: Leg13–19, multi-leg
- **PK**: `(atto_id, firmatario_uri, ruolo)`
- **Estratto con**: `scripts/extract_camera_sindisp.py --mode firmatari`
  (keyset sintetico `atto|firmatario|ruolo`)

## Volumi (multi-leg 13–19)

- **1.188.225** righe (atto × firmatario × ruolo)
- **287.557** atti distinti con almeno un firmatario
- **2.690** persone distinte

## Join

- `atto_id` → `camera_sindisp.atto_id`
- `persona_id` (da `deputato.rdf/d{id}_{leg}`) →
  `camera_deputati_legislature.persona_id`

Sul LOD Camera un atto Camera può avere anche un firmatario Senato
(`senatore.rdf/s{id}_{leg}`): il clean estrae l'id in entrambi i casi,
ma il dato resta nel perimetro Camera.

## Mart

- `mart_firmatari_per_atto`: n firmatari, n primo/altro, n persone
- `mart_per_deputato`: atti firmati per persona e legislatura

## Limiti

- Il dataset non include i destinatari (vedi `camera_sindisp_destinatari`).
- I nomi (`label`) sono quelli del LOD, non normalizzati.
- Un firmatario può comparire con URI diversi in legislature diverse: il
  join cross-leg va fatto su `persona_id`, non sull'URI.
