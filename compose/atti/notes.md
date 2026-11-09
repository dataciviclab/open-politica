# atti — note di contratto

Compose di **integrazione**, non prodotto analitico: è il livello che mancava tra
i 29 mirror di `datasets/` e i compose analitici (`profilo`, `kpi`).

## Perché esiste

La stessa identità dell'atto era ricostruita in quattro punti diversi:

| Dove | Cosa ricostruiva |
|---|---|
| `compose/decreti-legge` | identità DL da `(dl_numero, dl_anno)` letta dal titolo |
| `compose/voti-ddl-dettaglio` | `ddl_id` per agganciare i voti |
| `compose/senato-corpus-parlamento` | `atto_num == id_ddl` per il corpus AKN |
| `legal-graph` (`nodes_*`, `decreti_legge_urn`) | namespace, dedup, URN |

Con `atti` la chiave e il tipo vivono in un posto solo.

## Contratto

- **Grain**: una riga per atto nella **numerazione d'origine**
  (`ramo` + `legislatura` + `numero`). Non è "l'atto unico cross-ramo": Camera
  (`ac{LEG}_{NUM}`) e Senato (`id_ddl`) sono numerazioni indipendenti — 3.191
  valori numerici coincidono per caso, non per identità. Il ponte affidabile è
  `urn_normattiva` quando l'atto è promulgato.
- **`atto_id`**:
  - `senato:{id_ddl}` — unico globalmente (34.362 distinti su 36.208 righe di
    `senato_ddl`, che è atto×fase)
  - `camera:{legislatura}:{id_ddl}` — **la legislatura è obbligatoria**:
    6.328 valori di `id_ddl` su 7.614 compaiono in più legislature
- **`tipo`**: enum chiuso (4 valori). I valori di `natura` fuori elenco —
  la fonte ci mette anche date, codici e stati — finiscono in `ALTRO`, mai
  persi: `natura_raw` conserva l'originale.
- **`numero_legge` / `data_legge` / `urn_normattiva`**: valorizzati quando
  l'atto è promulgato. Senato: dalla fase rappresentativa di `senato_ddl`.
  Camera: join `(legislatura, ddl_numero) = (legislatura, id_ddl)` su
  `camera_leggi` (376/387 leggi Leg19 agganciate; le altre sono leggi senza
  DDL Camera).
- **`dl_numero` / `dl_anno` / `data_dl`**: solo per i DDL di conversione,
  ricalcati da `compose/decreti-legge` (la data del decreto è nel titolo, non
  in `data_presentazione`: per un DL di dicembre il DDL di conversione può
  essere presentato a gennaio). 933 atti → 894 DL distinti: un DL può avere
  due iter (Camera + Senato).

## Mart

| Tabella | Grain | Cosa aggiunge |
|---|---|---|
| `mart_atti` | atto (ramo+legislatura+numero) | la dimensione |
| `mart_dl` | (dl_numero, dl_anno) | esito conversione, tempi, atto rappresentativo |
| `mart_dl_anno` | anno | sintesi DL (stesso schema del vecchio `decreti_legge/mart_sintesi`) |

`mart_dl` sostituisce `compose/decreti-legge` (stessa semantica, un solo
punto di verità). L'esito usa un
match per pattern: la fonte scrive lo stato in più varianti e la vecchia
uguaglianza esatta perdeva 105 DL "decreto legge decaduto" e 16 "restituito al
Governo per essere ripresentato". Sono passati da `in_esame` all'esito vero.

### Definizioni delle date (per chi legge il mart)

- `giorni_conversione` = `data_conversione − data_dl`: dalla **data del
  decreto**, non dalla prima presentazione del DDL di conversione. Per 458 DL
  su 894 la prima data dell'iter è successiva alla data del decreto (+16,9
  giorni medi): partire dall'iter sottostimava i tempi (DL 200/2025 segnava
  3 giorni invece di 58). Range attuale 4–77 giorni.
- `data_presentazione` = **prima data dell'iter parlamentare** (presentazione
  del DDL di conversione), non la data del decreto. Per i DL convertiti è
  tipicamente 1–2 mesi dopo `data_dl`.
- `data_dl_fonte` = `titolo` (data letta dal titolo, 933/933 casi) oppure
  `presentazione` (fallback quando il titolo non è interpretabile).

### Perimetro e buchi noti della fonte

- **`dl_numero`/`dl_anno` esistono solo sul ramo Senato** (933 DDL di
  conversione, 0 Camera): il mart non può contenere DL mai arrivati al Senato.
  È coerente col vecchio `decreti-legge`, che aveva la stessa sorgente.
- **`stato` Camera è NULL prima della Leg17** (Leg13-15 0%, Leg16 0,2%,
  Leg17-19 100%; 21.626 atti su 34.315). Non è un buco del clean: la fonte
  Camera non lo fornisce. Il `tipo` non ne dipende; l'esito DL sì, ma i DL
  arrivano dal ramo Senato dove `stato` c'è.

## Bug che questo livello rende impossibile

`legal-graph` deduplicava `PARTITION BY id_ddl` senza `legislatura` su
`camera_ddl` (7 legislature): i 34.313 atti Camera diventavano **7.614 nodi**,
con la riga più recente a sopravvivere. Con `camera:{legislatura}:{id_ddl}`
il collasso non è rappresentabile.

## Non fa (di proposito)

- Non unisce lo stesso atto tra i rami: il bridge per fase `S./C.` è
  documentato in `legal-graph/KEYS.md` e richiede una decisione, non un
  `LIKE`.
- Non normalizza `stato` (resta il testo della fonte) né le entità HTML nei
  titoli Camera (`&rsquo;`, `&deg;`): è igiene della fonte, non identità.
