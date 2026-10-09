## Tecnico

- **Fonte**: DAIT — snapshot corrente CSV via HTTP (3 file multi-livello)
- **URL diretti**: `ammcom.csv` (comuni), `ammprov.csv` (province), `ammreg.csv` (regioni) — stessa pagina open-data
- **Protocollo**: HTTP file (non CKAN)
- **CSV**: UTF-8, delim `;`, header alla riga 3 (prime 2 righe = metadati da skippare) — identico nei 3 file
- **Dimensioni raw**: ammcom ~30 MB, ammprov ~250 KB, ammreg ~200 KB
- **Granularità**: amministratori comunali + provinciali + regionali (snapshot corrente)
- **Unione multi-livello**: `inject_column: livello_ente` + `read.mode: all` + `union_by_name` (toolkit nativo, nessun preprocess). Colonne mancanti a un livello → NULL.

## Run

- **Dataset**: ammcom + ammprov + ammreg (snapshot 2026)
- **Run ID**: `20261009T111043Z` (feat/dait-amm-unificati)
- **Esito**: SUCCESS — readiness 8/8
- **Righe clean**: 127.805 (125.953 comuni + 986 province + 866 regioni)
- **Confronto**: il precedente run solo-comuni aveva 124.716 righe; la differenza (~1.2k) è dovuta all'aggiornamento del file ammcom.csv a monte

## Confronto altri CSV DAIT

I CSV della pagina open-data hanno schemi parzialmente diversi. Con `union_by_name` + `inject_column` il toolkit li unisce nativamente:

| CSV | Colonne raw | Unito nel dataset? |
|---|---|---|
| `ammcom.csv` | 18 | ✅ (primary) |
| `ammprov.csv` | 17 (+ data_elezione_max_carica, - codice_comune) | ✅ (union_by_name) |
| `ammreg.csv` | 14 (solo regione) | ✅ (union_by_name) |
| `maggiororgano.csv` | 18 (identico ad ammcom) | ❌ ridondante (sottoinsieme) |
| `sindaciincarica.csv` | 19 (sottoinsieme ammcom) | ❌ ridondante |
| `ammmetropolitani.csv` | 17 (come ammprov) | ❌ non incluso (nichilistica) |
| `organistraordinariincarica.csv` | 11 | ❌ non incluso |

## Analitico

- `livello_ente`: colonna iniettata da `inject_column` — `comune` / `provincia` / `regione`
- `denominazione_ente`: unificata da `denominazione_{comune,provincia,regione}` via COALESCE (prima era `denominazione_comune` — breaking change documentato)
- `codice_dait_completo`: 9 cifre (regione2+provincia3+comune4), valorizzato solo per `livello_ente='comune'`. Non è un codice ISTAT — serve mappatura verificata per join
- `popolazione_censita`: solo comuni; auto-detect DuckDB la tipizza BIGINT (non serve NULLIF per vuoti)
- `data_elezione_max_carica`: solo province (986/986 valorizzate)
- `codice_regione`: codice DAIT (2 cifre), non ISTAT
- Date (`data_nascita`, `data_elezione`, `data_entrata_in_carica`, `data_elezione_max_carica`): DD/MM/YYYY nel raw, DATE nel clean via `dateformat`
- `lista_appartenenza/collegamento`: colonna con slash — richiede quoting DuckDB nel clean.sql

## Licenza e trattamento dati personali

- **Fonte**: DAIT — Ministero dell'Interno, open data amministratori locali
- **URL**: https://dait.interno.gov.it/elezioni/open-data/amministratori-locali-e-regionali-in-carica
- **Sezione open data**: la pagina è pubblicata nell'archivio [open-data del DAIT](/elezioni/open-data) con etichetta esplicita "Open-data"
- **Licenza**: non espressa direttamente sulla pagina DAIT. Tuttavia:
  - Le [Note legali](https://www.interno.gov.it/it/note-legali) del Ministero dell'Interno (ente capofila) rilasciano i contenuti testuali in **CC BY 4.0**
  - DAIT è un dipartimento del Ministero — per analogia, la licenza applicabile ai dati è **CC BY 4.0**
  - L'**art. 52 del CAD (D.Lgs 82/2005)** stabilisce che i dati pubblicati dalla PA senza licenza espressa si intendono rilasciati come dati di tipo aperto
- **Base giuridica trattamento dati personali**: i dati anagrafici (nome, cognome, data nascita, sesso, titolo di studio, professione) sono pubblicati dalla PA in quanto relativi a cariche pubbliche. Base giuridica: art. 2-ter D.Lgs 196/2003 (GDPR nazionale) e art. 6(1)(c) GDPR (obbligo di legge). Il Lab non effettua operazioni di profilazione o arricchimento. Per qualsiasi riutilizzo downstream, verificare compatibilità con il GDPR e la licenza della fonte.
- **Conservazione**: lo snapshot 2026 è singolo anno. Una serie storica richiederebbe valutazione della liceità del trattamento su base continuativa.

## Cautele

- **mode: all obbligatorio**: con `mode: latest` il toolkit seleziona solo il file primary — per multi-source serve `mode: all`
- **Niente clean.read.columns espliciti**: disattiverebbero `union_by_name` e romperebbero l'unione con schemi diversi
- **Auto-inferenza tipi**: con union_by_name, DuckDB tipizza `popolazione` come BIGINT e le date come DATE — il clean.sql non deve rifare cast con NULLIF su stringhe
- **Mart filtrate su comune**: le 3 mart sono `WHERE livello_ente='comune'` per preservare le metriche storiche; province/regioni analizzabili ad hoc sul clean
- **Encoding**: attuali UTF-8; la serie storica 1986–2022 usa latin-1 in parte (gestire nel preprocess del dataset storico)
- **Serie storica**: da implementare come dataset separato (`dait_amministratori_storico`) — vedi piano

## Aggiornamento 2026-10-09 (multi-livello)

- Esteso il dataset da solo-ammcom a 3 livelli (comune/provincia/regione)
- `inject_column: livello_ente` + `read.mode: all` + union_by_name (nessun preprocess)
- Breaking change: `denominazione_comune` → `denominazione_ente`; aggiunte `livello_ente` e `data_elezione_max_carica`
- Run: 127.805 righe, readiness 8/8; 4 mart (le 3 storiche filtrate su comune + mart_profilo_livello su tutti i livelli)
- Numeri chiave: 7.783 sindaci su 7.880 comuni; sindaci F 15,5% (età media 55,8); regione 03 (Lombardia) 23.558 amministratori totali
- Pattern da mart_profilo_livello: più si sale di livello, meno donne (Sindaci com F 15,5% → Presidenti prov F 9,0% → Presidenti reg F 11,8%) e più età (55,8 → 54,9 → 58,3)
