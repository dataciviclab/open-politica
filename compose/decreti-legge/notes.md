# decreti_legge — decreti-legge dal lato Parlamento (Leg13–19)

Il decreto-legge: il Governo legifera d'urgenza (in vigore subito), il
Parlamento deve **convertirlo in legge entro 60 giorni** (prorogabili una volta
di altri 60) o decade. Il DL arriva in Senato come "disegno di legge di
conversione" — da lì estraiamo numero, data, esito e tempi.

## Dati

- **Fonte**: `senato_ddl` (natura = "di conversione di decreto-legge")
- **Perimetro**: **Leg13–19** (support Pattern C multi-leg; GCS verificato 2026-10-08)
- **Righe**: **930 DL distinti** (Leg13–19) — dedup da fasi iter; PK
  `(dl_numero, dl_anno)` (numeri DL ripartono ogni anno — multi-leg
  richiede il GROUP BY su entrambe le chiavi)
- **Campi**: `dl_numero`, `dl_anno`, `data_presentazione` (= data del DL),
  `data_conversione`, `esito`, `giorni_conversione`, `titolo`,
  **`ddl_id`** (chiave `senato_ddl.id_ddl`, #63), `ddl_ramo`, `n_id_ddl_iter`
- **Esiti**: convertito / decaduto / restituito al Governo / in esame
- PK: `(dl_numero, dl_anno)` — i numeri DL ripartono ogni anno

## ddl_id (#63) — regola representative

Lo stesso DL può avere **più `id_ddl`** (ramo Camera + Senato della stessa
conversione, o iter distinti). Il clean ne sceglie **uno**:

1. preferenza `ramo = 'S'` (esame Senato)
2. poi `data_legge` / `data_presentazione` più recente

`ddl_id` è quindi **representative, non univoco per costruzione**.
Downstream (legal-graph): l'edge `converte_decreto_legge` punta a questo
iter — accettabile come chiave di join, non come enumeration di tutti gli iter.
`n_id_ddl_iter` conta quanti `id_ddl` distinti c'erano (>=1).

## Numeri

Multi-leg (run 2026-10-08): **930 DL** distinti, 1996–2026.

| Fascia | DL | Anni |
|---|---:|---|
| Leg13 | 224 | 1996–2000 |
| Leg14 | 163 | 2001–2005 |
| Leg15 | 51 | 2006–2007 |
| Leg16 | 107 | 2008–2012 |
| Leg17 | 85 | 2013–2017 |
| Leg18 | 119 | 2018–2021 |
| Leg19 | 181 | 2022–2026 |

XIX leg. (anno calendario, riferimento):

| Anno | DL | Convertiti | Decaduti | Tempo medio |
|---|---|---|---|---|
| 2022 | 12 | 11 | 1 | 152 gg |
| 2023 | **39** | 36 | 3 | 236 gg |
| 2024 | 23 | 19 | 4 | 204 gg |
| 2025 | 21 | 21 | 0 | 70 gg |
| 2026 | 13 | 9 | 0 | 54 gg |

Il 2023 è il picco di decretazione d'urgenza nella XIX.

## Note / limiti

- **`giorni_conversione` = fase Senato, non ciclo completo del DL**: misura
  da `data_presentazione` (data del DL) a `data_legge`. Se il DL è passato
  prima dalla Camera, il dato riflette il solo esame Senato e può superare i
  60/120 giorni reali. È una stima, non il tempo regolamentare.
- `dl_numero` estratto dal titolo (`n. <numero>`); `dl_anno` dall'anno di
  presentazione (i numeri DL ripartono ogni anno).
- Solo lato Senato: DL convertiti direttamente alla Camera senza passare
  dal Senato potrebbero mancare.
- Il raw `http_file` resta un file rappresentativo (Leg19); il clean legge
  **tutti** gli anni dal support multi-leg.

## Rebuild

```bash
toolkit run -c compose/decreti-legge/dataset.yml -y 2026
```
