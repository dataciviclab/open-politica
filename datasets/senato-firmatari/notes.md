# Notes — senato-firmatari

## Fonte

- Endpoint SPARQL Senato: `https://dati.senato.it/sparql` (GET obbligatorio, POST 403)
- Namespace `osr:` (`http://dati.senato.it/osr/`), graph `http://dati.senato.it/ddl/{year}`
- **Perimetro**: Leg13–19 (`years: [13..19]`). I–XII non pubblicati nel LOD Senato.
- **I firmatari NON sono un predicato diretto del ddl**: sono risorse
  `osr:iniziativa` collegate via `osr:iniziativa` dal ddl. La catena è:
  `ddl → iniziativa/INIZ-DDL-{n} → presentatore / primoFirmatario / tipoIniziativa / senatore`

## Quirk della fonte (verificati 2026-08-04)

- **`osr:presentatore` non esiste come predicato del ddl** — ho verificato che il
  graph ha 29 predicati per ddl e tra questi non c'è presentatore. Il predicato
  `osr:presentatore` esiste solo sulle risorse `iniziativa/*`.
- **⚠️ `osr:idDdl` ≠ URI `/ddl/N`**: sono due numerazioni diverse. Es. il ddl
  `/ddl/59716` ha `osr:idDdl = 55017`. La chiave di join con `senato-ddl` è
  `osr:idDdl` (che senato-ddl usa come `id_ddl`), NON l'id dall'URI.
- **⚠️ Un `idDdl` può avere più URI `/ddl/N`**: la stessa "pratica" è legata a
  più versioni del ddl (es. presentato alla Camera e al Senato). Per questo la
  PK del clean è `(ddl, iniziativa)`, non `(ddl_id, iniziativa)`.
- **`primoFirmatario`**: presente su ~16% delle iniziative (32/200 nel campione).
  Il resto dei firmatari è nel testo `descrIniziativa` ("ed altri") non espanso
  in risorse separate — limite della fonte, non del dataset.
- **`senatore`**: solo i firmatari senatori hanno URL `/senatore/N` (~34%).
  I presentatori "On." (deputati) e "Ministro" (governativi) non ce l'hanno.
- **`tipoIniziativa`**: presente al 100% — Parlamentare, Governativa, Regionale,
  CNEL, Popolare.
- **⚠️ WAF Senato tronca a ~10.000 righe/risposta**: la query firmatari produce
  ~38.000 righe su Leg19 → paginazione OFFSET (`pages: 4, step: 10000`).
  Legislature storiche generalmente sotto le 10k (extra pagine innocue).
- **`dataAggiuntaFirma`/`dataRitiroFirma`**: la fonte le fornisce in formato ISO
  (es. 2023-05-26), NON YYYYMMDD — il clean le casta direttamente a DATE.

## Volumi

- Leg19 (riferimento): DDL con metadati ~5.124 · iniziative ~38k · idDdl ~4.659
- min_rows clean abbassato a 1.000 (per-leg, non sul totale multi-anno)
- I–XII: graph `ddl/{1..12}` = 0 triple live (2026-10-02) — non espandibile

## 2026-10-02 — Pattern C multi-legislature

- `years: [13..19]`, query `GRAPH <.../ddl/{year}>`
- Clean non espone `legislatura`: join a `senato-ddl` via `ddl_id` = `osr:idDdl`
- Con `data_aggiunta_firma`: 6.731 · con `data_ritiro_firma`: 161
- Con `deputato_url` (link Camera): 21.755 · con `senatore_id`: 12.792
- Firma media: ~8.1 iniziative per idDdl

### `osr:idDdl` è globale su Leg13–19 (review PR #52)

Verifica su clean multi-leg (2026-10-02):

- `ddl_id` firmatari **disgiunti** tra legislature (leg13 `2–12014`, leg19 `50862–55687`; overlap = 0)
- `senato-ddl.id_ddl` in >1 legislatura: **0 / 34.360**
- Join firmatari → senato-ddl: 27.969 match **1:1**, 0 match multipli
- Leg19: 4.753 / 4.754 id firmatari presenti in `senato-ddl`

Quindi `ddl_id` **non** riparte per graph: la join multi-anno collassa solo se si unisce senza filtrare legislatura sul lato ddl.  
Il clean firmatari resta senza colonna `legislatura` di proposito (una riga = iniziativa; la leg. è nel path `{year}` del run e in `senato-ddl`).

~34% id senza match `senato-ddl`: ddl senza metadati nel graph o esclusi dal clean ddl (`HAVING fase IS NOT NULL`) — non collisione di chiave.

## Limiti dichiarati

- **NON risponde "tutti i firmatari"**: il graph espande i presentatori dichiarati
  (per idDdl), non l'elenco completo "ed altri" del testo `descrIniziativa`.
- Presentatori non-senatori (deputati, ministri) inclusi con `senatore_id = NULL`.
- Join a `senato-ddl` solo sugli id presenti in entrambi i clean; id firmatari
  senza controparte ddl non sono un bug di Pattern C.
