# open-politica

**La politica italiana in dati aperti: chi vota, come vota, cosa decide.**

Dati aperti e interrogabili su elezioni, Parlamento (Camera e Senato), governo
e amministratori locali. Il progetto nasce da una domanda semplice: **come fa
un cittadino a sapere davvero cosa fa chi lo rappresenta?**

Qui ogni dato è:

- **aperto** — da fonti ufficiali (Camera, Senato, Ministero dell'Interno)
- **pulito e interrogabile** — parquet pronti per l'analisi, senza scraping
- **collegato** — dalla scheda del singolo parlamentare alla "pagella"
  dell'intero Parlamento

---

## Cosa puoi scoprire

### 🗳️ Il tuo rappresentante, da tutte le angolazioni

Ogni parlamentare ha una **scheda** che risponde a tre domande:

| Domanda | Cosa c'è |
|---|---|
| **Come vota?** | quante volte, in che direzione, quanto è fedele al suo partito |
| **Cosa comanda?** | è ministro? presidente di commissione? |
| **Di cosa si occupa?** | lavoro, sanità, giustizia, esteri... |

Sapevi che la disciplina di partito in Italia è altissima? La fedeltà media al
proprio gruppo è **~99,5% in entrambe le Camere**: i "ribelli" sono pochi, e
sono quasi sempre i nomi che conosci (Calenda, Gelmini, Soumahoro).

### 🏛️ Il Parlamento come istituzione

L'**osservatorio** — la "pagella del Parlamento" — misura come funziona la
macchina legislativa. Numeri della XIX legislatura:

- **~36% delle leggi approvate nasce dal governo**, e il governo legifera
  d'urgenza con i **decreti-legge**: 108 nella XIX, **89% convertiti** in
  legge dal Parlamento, 8 decaduti
- **1,18 milioni di voti individuali** dei senatori e **7,7 milioni** dei
  deputati, tutti interrogabili
- le donne alla Camera: **11,5% (XIV leg.) → 36,4% (XVIII leg.)**
- 26 voti di fiducia nel solo 2023 — il governo che schiaccia il dibattito

### 📈 Le elezioni, dal 1948

Risultati per comune di ogni tornata: politiche, europee, regionali, comunali
e referendum. Per capire com'è cambiato il voto, territorio per territorio.

---

## Come si usa

I dati sono pubblici su GCS e interrogabili con SQL (DuckDB) o via MCP del
toolkit. Anche i parquet locali in `out/data/` funzionano allo stesso modo:

```sql
-- Chi vota MENO col proprio partito? (i "ribelli")
SELECT nome, cognome, pct_col_gruppo, ramo
FROM read_parquet('https://storage.googleapis.com/dataciviclab-mart/open-politica/profilo_politico/2026/mart_profilo.parquet')
ORDER BY pct_col_gruppo;
```

```bash
make run-<dataset>    # esegue un dataset (raw → clean → mart)
make check            # valida tutti i config
make registry-write   # aggiorna il catalogo
```

## Contenuto

```
datasets/    # un dataset per cartella (dataset.yml + sql/)
compose/     # dataset compositi: profilo_politico, osservatorio_parlamento, elezioni_voto, decreti_legge
registry/    # catalogo degli artifact
scripts/     # estrazione SPARQL, preprocessing elezioni
out/         # output runtime — mai versionato
```

## Fonti

- **Eligendo / DAIT** — Ministero dell'Interno (elezioni, amministratori locali)
- **dati.camera.it** — OpenData SPARQL (deputati, votazioni, voti, organi)
- **dati.senato.it** — OpenData SPARQL (senatori, gruppi, commissioni, ddl, voti)
- **dati.gov.it** — anagrafica PA

## Licenze

- **Codice**: MIT
- **Dati**: licenze originali delle fonti (CC BY per Camera e Senato;
  dati Eligendo/DAIT del Ministero dell'Interno) — vedi notes.md dei singoli
  dataset per la fonte di provenienza

## Pubblicazione

I dataset pubblicati (clean/mart) sono su GCS con prefisso `open-politica/`,
una cartella per anno (i multi-anno coprono tutta la serie storica):

- `gs://dataciviclab-clean/open-politica/<slug>/<anno>/`
- `gs://dataciviclab-mart/open-politica/<slug>/<anno>/`

Eccezione: i mart multi-anno flat (es. `camera_votazioni_sparql`) stanno
direttamente in `gs://dataciviclab-mart/open-politica/<slug>/`.

CI: `ci.yml` (preflight su PR) + `pipeline.yml` (post-merge + schedule mensile
con estrazioni pesanti + sync GCS + registry PR).

## Stato

Progetto di dominio del DataCivicLab (in incubazione). I dataset sono
sviluppati, validati e **pubblicati** su GCS in layout `$slug/$anno/`. Prossimi
passi: compositi leggibili da GCS (oggi usano i path locali), estensione alle
legislature precedenti, prime analisi pubbliche.
