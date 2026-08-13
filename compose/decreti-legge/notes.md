# decreti_legge — decreti-legge dal lato Parlamento (XIX leg.)

Il decreto-legge: il Governo legifera d'urgenza (in vigore subito), il
Parlamento deve **convertirlo in legge entro 60 giorni** (prorogabili una volta
di altri 60) o decade. Il DL arriva in Senato come "disegno di legge di
conversione" — da lì estraiamo numero, data, esito e tempi.

## Dati

- **Fonte**: `senato_ddl` (natura = "di conversione di decreto-legge")
- **Righe**: 108 DL distinti (XIX leg.) — dedup da 270 righe di iter
- **Campi**: `dl_numero`, `dl_anno`, `data_presentazione` (= data del DL),
  `data_conversione`, `esito`, `giorni_conversione`, `titolo`
- **Esiti**: convertito / decaduto / restituito al Governo / in esame

## Numeri (XIX leg.)

| Anno | DL | Convertiti | Decaduti | Tempo medio |
|---|---|---|---|---|
| 2022 | 12 | 11 | 1 | 152 gg |
| 2023 | **39** | 36 | 3 | 236 gg |
| 2024 | 23 | 19 | 4 | 204 gg |
| 2025 | 21 | 21 | 0 | 70 gg |
| 2026 | 13 | 9 | 0 | 54 gg |

Il 2023 è il picco di decretazione d'urgenza.

## Note / limiti

- **`giorni_conversione` = fase Senato, non ciclo completo del DL**: misura
  da `data_presentazione` (data del DL) a `data_legge`. Se il DL è passato
  prima dalla Camera, il dato riflette il solo esame Senato e può superare i
  60/120 giorni reali. È una stima, non il tempo regolamentare.
- `dl_numero` estratto dal titolo (`n. <numero>`); `dl_anno` dall'anno di
  presentazione (i numeri DL ripartono ogni anno).
- Copre solo la XIX legislatura e solo il lato Senato (i DL convertiti
  direttamente alla Camera senza passare dal Senato potrebbero mancare).

## Rebuild

```bash
make run-decreti-legge
```
