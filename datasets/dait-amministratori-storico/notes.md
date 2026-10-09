## Tecnico

- **Fonte**: DAIT — 40 CSV annuali (snapshot 31/12) dal portale open-data
- **URL pattern**: `https://dait.interno.gov.it/documenti/storico_amministratori_comuni3112YYYY{,_0,_1}.csv` — naming variabile (4 pattern); mappa hardcoded in `preprocess.py` (catturata 2026-10-09)
- **Protocollo**: script source (preprocess.py) → CSV normalizzato → clean SQL
- **Encoding misti**: utf-8 (anni precoci + 2023+), latin-1 (~2010–2022) — `smart_decode` con fallback
- **Due ere schema**: A (1986–2022, 28 col) / B (2023–2025, 34 col) — unificate in preprocess con COL_MAP
- **Output raw**: 1 CSV unico ~1,6 GB, 6.075.430 righe, 35 col (poi 36 nel clean con codice_dait_completo)
- **Streaming**: preprocess genera e scrive riga-per-riga (no accumulation in memoria — il primo tentativo con list-of-dict ha crashato WSL)

## Run

- **Run ID**: `20261009T125024Z` (feat/dait-amm-storico)
- **Esito**: SUCCESS — readiness 8/8
- **Righe clean**: 6.075.430 (1986–2025, zero gap)
- **Durata**: ~8 min (raw 7min download+parse, clean 52s, mart <1s)
- **Anni per riga**: 134k (1986) → 195k (1989, picco) → 126k (2025)

## Scelte di design

- **preprocess.py necessario** (a differenza del dataset corrente): URL map variabile, encoding misti, due ere schema da unificare
- **years: [2025] + time_coverage full_series**: un singolo run produce la serie intera; anno di run = 2025 (snapshot più recente)
- **Streaming write**: il preprocess yield generator + DictWriter con lineterminator='\n'; campi sanitizzati da \r\n embedded (causava parser error DuckDB)
- **quote/escape espliciti** in clean.read: l'auto-detect DuckDB falliva su campi con apostrofi/virgolette (liste elettorali)
- **strict_mode: false** per resilienza su dati reali

## Analitico

- `anno_snapshot`: anno dello snapshot (31/12) — la dimensione temporale
- `codice_dait_completo`: regione(2)+provincia(3)+comune(4), 9 cifre — non ISTAT
- `data_inizio_carica`: unificata da DATA_NOMINA (Era A) / DATA_INIZIO_CARICA (Era B)
- `data_cessazione`: presente in entrambe le ere — fine mandato (naturale o anticipata)
- `incarico`/`funzione` + date: solo Era B (2023+) — NULL per 1986–2022
- `lista_appartenenza`: unificata da PARTITO_LISTA_COALIZIONE (A) / LISTA_APPARTENENZA/COLLEGAMENTO (B)
- `sigla_titolo_accademico`: droppata (solo Era A, superseded da titolo_studio)

## Trend chiave (mart_genere_anno)

- 1986: 6,7% F → 2025: 35,3% F (5× in 40 anni)
- Salti: 1990→1995 (8,3→17,5%, effetti legge Rosato), 2010→2015 (19,2→28,4%)
- Sindaci: 2,7% F (1986) → 15,3% F (2025); età media 45,7 → 55,1
- Comuni con organi: ~195k amministratori (1989) → ~126k (2025) — aggregazioni comunali

## Cautele

- **Script source**: richiede `TOOLKIT_ALLOW_SCRIPT_SOURCE=1` (Makefile del repo lo esporta)
- **Download pesante**: ~1,4 GB per run completo; per sviluppo usare `--years` nel preprocess
- **Naming file variabile**: la URL map è hardcoded — se il DAIT rinomina file, va aggiornata (scout periodico)
- **Encoding**: latin-1 nel blocco ~2010–2022; smart_decode gestisce, ma nuovi anni potrebbero introdurre altri encoding
- **Campi con newline**: la lista_appartenenza può contenere \r\n embedded; preprocess li sanifica
- **Dati personali**: stessa base giuridica del dataset corrente (cariche pubbliche, art. 6(1)(c) GDPR); la serie storica estende il trattamento su base continuativa — valutare liceità per riutilizzi downstream
- **Licenza**: CC BY 4.0 (per analogia con note legali Ministero, art. 52 CAD)

## Aggiornamento 2026-10-09 (creazione)

- Dataset creato da zero su branch feat/dait-amm-storico
- preprocess.py: URL map 40 anni, smart_decode, unificazione due ere, streaming write
- Serie completa 1986–2025: 6.075.430 righe, 0 gap, readiness 8/8
- 2 mart longitudinali: genere_anno (80 righe), profilo_anno (697 righe)
