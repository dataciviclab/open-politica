# Roadmap — open-politica (piano interno, non ancora issues)

Stato: nota locale di pianificazione. Da trasformare in issues GitHub quando
decidiamo di partire.

## Contesto

Il repo copre oggi **24 dataset + 3 compose** (~8M righe): elezioni,
Parlamento (Camera+Senato), governo, amministratori locali. Due deliverable
chiave:
- `profilo_politico` — la scheda del parlamentare (voto + governo + commissioni)
- `osservatorio_parlamento` — i KPI istituzionali (la "pagella")

## 1. Cosa resta nei cataloghi (per valore)

| # | Cosa | Fonte | Valore | Costo |
|---|---|---|---|---|
| A | **Decreti-legge** (conversioni, decaduti) | Governo/PCM | 🔥 chiude il "decide o ratifica" | medio |
| B | **Interventi in aula** (chi parla) | Camera 1,15M + Senato 36k | alto | medio |
| C | **Relatori** (registi delle leggi) | Camera, 100k | alto | basso |
| D | **PDL Camera** (produzione + iter) | Camera | alto | medio |
| E | **Documenti patrimoniali** | Senato | medio | basso |
| F | **Estensione legislature** XIII-XVIII (voti, commissioni, gruppi) | Camera+Senato | alto | alto |
| G | **Eligendo storico**: referendum 1946, regionali 1970, Costituente 1946 | DAIT | medio | basso |
| H | **Ponte candidato→eletto** (data_nascita+nome) | cross | alto | medio |

## 2. Roadmap

### Fase 1 — chiudere la storia
- [x] A. Decreti-legge (`decreti_legge` — 108 DL XIX, 89% convertiti, + KPI in osservatorio)
- [ ] C. Relatori Camera (basso costo, alto valore)
- [ ] B. Interventi (la dimensione "chi parla")

### Fase 2 — infrastruttura (rendere sostenibile)
- [ ] PR toolkit: source `sparql` robusto (branch locale `fix/sparql-pagination` — keyset + anti-troncamento)
- [ ] Publish GCS + CI schedulata (estrazioni pesanti come job notturni)
- [ ] Compose riproducibili (leggono da GCS, non da path locali)

### Fase 3 — estendere
- [ ] F. Legislature storiche
- [ ] G. Eligendo storico
- [ ] H. Ponte candidato→eletto

### Fase 4 — raccontare
- [ ] Prima analisi pubblica: *"Il Parlamento decide o ratifica?"* (dai KPI dell'osservatorio)

## 3. Issue da aprire (quando si parte)

| # | Issue | Priorità |
|---|---|---|
| 1 | `intake`: Decreti-legge — conversione e decadenza | alta |
| 2 | `intake`: Interventi in aula Camera+Senato | alta |
| 3 | `intake`: Relatori Camera | alta |
| 4 | `intake`: Produzione legislativa Camera (PDL) | media |
| 5 | `intake`: Documenti patrimoniali Senato | media |
| 6 | `intake`: Estensione legislature XIII-XVIII | media |
| 7 | `intake`: Ponte candidato→eletto | media |
| 8 | `infra`: GCS + CI + compose riproducibili | alta |
| 9 | `infra`: PR toolkit source sparql | alta |
| 10 | `analisi`: "Il Parlamento decide o ratifica?" | media |

## Note tecniche accumulate

- **WAF Senato**: curl via HttpClient (POST/requests → 403); variabili SPARQL corte (le lunghe danno risultati vuoti); rate-limit a burst → backoff
- **Camera voti**: paginazione OFFSET instabile su Virtuoso → batch per votazione (IN-list) via POST (la GET con IN-list lunghe → 414)
- **`camera_votazioni_sparql`**: cattura solo le votazioni con `dc:date` nel formato atteso; per l'esito usa `approvato`
- **Elezioni**: source `script` richiede `TOOLKIT_ALLOW_SCRIPT_SOURCE=1`; il preprocess di `elezioni_politiche` genera comunque l'intera serie (il parametro anno è un'etichetta)
- **`camera_commissioni`**: grano = ruoli di organo (non membership completa); predicato fine = `dc:date`; serve `?dep a ocd:deputato`
