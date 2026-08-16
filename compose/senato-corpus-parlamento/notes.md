# senato_corpus_parlamento — il testo degli atti agganciato all'iter (XIX leg.)

Il compose unisce il **corpus Akoma Ntoso del Senato** (senato-akn, pubblicato
su GCS) con l'**iter legislativo** (`senato_ddl`): per ogni atto la sua
dimensione documentale (famiglie, peso testuale, articoli) accanto a fase,
stato, esito e numero legge.

## Dati

- **Fonte**: `senato_corpus` (senato-akn, `http_file` su GCS) + `senato_ddl`
- **Chiave di bridge**: `atto_num` ↔ `ddl_url` (`http://dati.senato.it/ddl/N`)
- **Righe**: 1.889 atti (una per atto) — join con senato_ddl 100%
- **Campi**: `atto_num`, `famiglie`, `tipologie`, `n_documenti`,
  `testo_totale`, `articoli_totali` + iter (`fase`, `stato`, `natura`,
  `data_presentazione`, `numero_legge`)

## Granularità: documento → atto

Il corpus di senato-akn è a livello **documento** (18 colonne). Il compose
aggrega per **atto** (13 colonne): le 17 colonne documentali (titolo, testo
integrale, date, frbr) vengono scartate — il dettaglio vive nel dataset
`senato_corpus` di senato-akn su GCS, interrogabile separatamente. Il drop
~0,1% di righe è la dedup doc→atto (2 atti con 2 versioni).

## Mart

- **`mart_atto_corpus`**: un atto con peso documentale + esito iter
- **`mart_decreti_peso`**: i DDL di conversione per peso documentale
  (finding senato-akn applicato all'iter: 120 convertiti, 8 decaduti,
  3 restituiti, 4 in esame)

## Note / limiti

- **Solo ddlpres** (il corpus pubblicato oggi copre i disegni di legge;
  emendamenti e dibattito sono follow-up — issue #12/#13/#14 di senato-akn).
- Solo XIX legislatura e solo lato Senato.
- `testo_totale` = somma dei caratteri dei documenti dell'atto; un atto con 2
  versioni conta entrambe.

## Rebuild

```bash
make run-senato-corpus-parlamento
```
