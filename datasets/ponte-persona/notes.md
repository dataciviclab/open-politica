# ponte_persona — identità unica Camera ↔ Senato

Unifica l'identità di una persona tra i due rami del Parlamento: il sistema
parlamentare non espone una chiave condivisa, la stessa persona ha un
`persona_id` (dati.camera.it) e un `senatore_id` (dati.senato.it) diversi.

## Dati (XIX legislatura)

- **Senatori**: 212 (anagrafica Senato, graph composizione/19)
- **Deputati**: 11.843 persone distinte (anagrafica Camera, tutte le legislature)
- **Ponte**: 62 senatori (29,2%) mappati 1:1 su un deputato · 1 caso ambiguo ·
  149 senza match

## Metodo

Match su **cognome + nome normalizzati** (UPPER, senza accenti), con fallback
per i nomi composti: la Camera tiene tutti i prenomi (`nome="IGNAZIO BENITO
MARIA"`), il Senato solo il primo (`"Ignazio"`) → si fa match su cognome
esatto + parole del nome contenute nel nome Camera.

```bash
# richiede i clean locali di camera_deputati_legislature e senato_anagrafica
make run-camera-deputati-legislature run-senato-anagrafica
make build-ponte-persona   # → out/data/derived/ponte_persona/ponte_persona.parquet
make run-ponte-persona     # pipeline → clean + mart_match
```

## Limiti noti

- **Match solo per nome**: rischia omonimie; per i casi sensibili serve
  validazione umana o dati aggiuntivi (luogo/data nascita)
- **~70% dei senatori senza match** perché: (a) mai stati deputati (senatori
  di diritto, tecnici, regionali, senatori a vita), (b) **gap di copertura
  del dataset Camera** — es. **Matteo Renzi** (deputato XVII, senatore XVIII/
  XIX) è assente da `camera_deputati_legislature` → da segnalare a monte
- Il ponte copre la XIX; per estenderlo servono anagrafiche Senato delle
  legislature precedenti (XIII-XVIII)
