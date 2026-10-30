# decreti_legge — decreti-legge dal lato Parlamento (Leg13–19)

Il decreto-legge: il Governo legifera d'urgenza (in vigore subito), il
Parlamento deve **convertirlo in legge entro 60 giorni** (prorogabili una volta
di altri 60) o decade. Il DL arriva in Senato come "disegno di legge di
conversione" — da lì estraiamo numero, data, esito e tempi.

## Dati

- **Fonte**: `senato_ddl` (natura = "di conversione di decreto-legge")
- **Perimetro**: **Leg13–19** (support Pattern C multi-leg; GCS verificato 2026-10-08)
- **Righe**: **883 DL distinti** (Leg13–19) — dedup da fasi iter; PK
  `(dl_numero, dl_anno)` (numeri DL ripartono ogni anno — multi-leg
  richiede il GROUP BY su entrambe le chiavi)
- **Campi**: `dl_numero`, `dl_anno` (= anno del **decreto**), `data_dl` (dal
  titolo), `data_presentazione` (prima presentazione del DDL di conversione),
  `data_conversione`, `esito`, `giorni_conversione`, `titolo`,
  **`ddl_id`** (chiave `senato_ddl.id_ddl`, #63), `ddl_ramo`, `n_id_ddl_iter`,
  `data_dl_fonte` (`titolo` | `presentazione`)
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

Multi-leg (run 2026-10-30, dopo il fix identità): **883 DL** distinti, 1996–2026.

| Fascia | DL | Anni |
|---|---:|---|
| Leg13 | 223 | 1996–2000 |
| Leg14 | 155 | 2001–2005 |
| Leg15 | 49 | 2006–2007 |
| Leg16 | 99 | 2008–2012 |
| Leg17 | 80 | 2013–2017 |
| Leg18 | 115 | 2018–2021 |
| Leg19 | 162 | 2022–2026 |

XIX leg. (anno calendario, riferimento):

| Anno | DL | Convertiti | Decaduti | Tempo medio |
|---|---|---|---|---|
| 2022 | 28 | 23 | 5 | 42 gg |
| 2023 | **40** | 36 | 4 | 56 gg |
| 2024 | 32 | 28 | 4 | 53 gg |
| 2025 | 34 | 32 | 2 | 53 gg |
| 2026 | 28 | 16 | 0 | 55 gg |

Il 2023 è il picco di decretazione d'urgenza nella XIX.

## Note / limiti

- **`giorni_conversione`**: da `min(data_presentazione)` (prima presentazione,
  Senato o Camera) a `max(data_legge)` (approvazione definitiva). È il ciclo
  parlamentare completo, non il solo ramo Senato.
- **Identità del DL (fix 2026-10-30)**: `dl_anno` è l'anno del **decreto**,
  ricavato dalla data nel titolo ("decreto-legge 27 dicembre 2024, n. 200"),
  non l'anno di presentazione del DDL. Prima si usava `year(data_presentazione)`:
  per un DL emanato a dicembre il ramo Camera presenta a gennaio dell'anno dopo,
  quindi lo stesso DL si sdoppiava e si fondeva con un DL diverso con lo stesso
  numero (5 righe con 338-401 giorni dichiarati, tutte impossibili). Con la
  chiave corretta: 930 → **883** righe, durata massima **62 giorni**, mediana
  **54**. `data_dl_fonte = 'presentazione'` segnala i titoli non interpretabili
  (oggi: 0).
- `dl_numero` estratto dal titolo (`n. <numero>`).
- Solo lato Senato: DL convertiti direttamente alla Camera senza passare
  dal Senato potrebbero mancare.
- Il raw `http_file` resta un file rappresentativo (Leg19); il clean legge
  **tutti** gli anni dal support multi-leg.

## Rebuild

```bash
toolkit run -c compose/decreti-legge/dataset.yml -y 2026
```
