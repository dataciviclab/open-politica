# senato_emendamenti_lod — note tecniche

## 2026-11-05 — bootstrap (issue #109)

- Fonte: `dati.senato.it` SPARQL, `osr:Emendamento`, grafi `emendamenti/{leg}_{part}`.
- Multi-leg 13–19 con `{year}` = legislatura. **I grafi sono spezzati in parti**
  (Leg14 `14_1..2`, Leg16 `16_1..2`, Leg17 `17_1..4`, Leg18 `18_1..3`,
  Leg19 `19_1..3`): la query usa `GRAPH ?g` + `FILTER(CONTAINS(STR(?g), 'emendamenti/{year}'))`
  per prendere tutte le parti della legislatura.
- ⚠️ L'inventario del Source Observatory è **vecchio**: conosce solo `19_1`,
  ma la XIX ha anche `19_2` (55.784) e `19_3` (22.214) → Leg19 = 131.335.

## Bridge all'atto

`oggetto → osr:relativoA → ddl/N` è nel **default graph** (l'emendamento è nel
named graph). Copertura del bridge (misurata 2026-11-05):

| Leg | emendamenti | con `atto_num` |
|---|---:|---:|
| 13 | 709 | 143 (~20%) |
| 19 | 131.335 | 127.433 (~97%) |

`atto_num` è quindi **nullable**; il `mart_per_atto` filtra i NULL.

## Join con senato-akn

Verificato su atto 56260 / S.391: `atto_num` = `ddl/N`, `emend_id` = `numero`,
`ramo` (`aula`/`commissione`) ↔ `tipologia` (`emend`/`emendc`).
Conteggi identici: 119 = 119 (aula 47, commissione 72).

⚠️ Attenzione: in `senato_ddl`, **`id_ddl` ≠ `ddl_url`** (es. id 55759 vs
`/ddl/60579`). Il bridge con questo dataset passa da **`ddl_url`**, non da `id_ddl`.

## WAF

- Tronca ~10k righe/risposta → `pages`/`step` (Leg19 → 14 pagine).
- Rate-limit a burst: 403 HTML per ~1 min. La query `GRAPH ?g` + `FILTER` è
  sensibile; le estrazioni lunghe vanno fatte con calma.

## Rebuild

```bash
make run-senato-emendamenti-lod
```
