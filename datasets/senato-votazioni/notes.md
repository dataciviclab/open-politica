# senato_votazioni — voti individuali dei Senatori

Voti espressi da ogni senatore su ogni votazione elettronica della **XIX
legislatura** (2022-2026). Il primo dataset del Lab con il dettaglio di voto
individuale: chiude il gap "nessun voto in aula" del profilo politico.

## Dati

- **Fonte**: dati.senato.it — endpoint SPARQL, graph `votazioni/*/19`
- **Periodo**: 26/10/2022 → 05/08/2026
- **Volume**: 1.182.928 voti · 7.998 votazioni · ~200 senatori
- **Schema**: una riga = voto di un senatore su una votazione, con i metadati
  della votazione (seduta, data, esito, conteggi)

## Estrazione

```bash
# estrazione completa XIX (paginata, ~30 min per il rate-limit WAF)
python3 datasets/senato-votazioni/preprocess.py --legislature 19
# incrementale (corsia pesanti: parte dal max(data) del parquet esistente)
python3 datasets/senato-votazioni/preprocess.py --legislature 19 --incremental
# scoperta dinamica dei graph (se il Senato ne aggiunge uno)
python3 datasets/senato-votazioni/preprocess.py --legislature 19 --discover-graphs
# ri-merge senza re-estrarre (dopo un cambio di clean.sql/mart.sql)
python3 datasets/senato-votazioni/preprocess.py --merge-only
```

### Incrementale

`--incremental` non rilegge tutta la legislatura e, col delta tipico, fa
**6 richieste** (contro ~13 di prima):

1. **1 query** per le sedute, poi tiene solo quelle con `dataSeduta >= max(data)`;
2. **se non ci sono sedute nuove termina subito** (1 richiesta);
3. **query** per i metadati delle votazioni di quelle sedute, sull'unione dei
   graph (niente `GRAPH`, niente una query per graph), a batch;
4. **query** (paginata) per i voti di quelle votazioni, anch'essa sull'unione e
   a batch.

Il limite dell'endpoint è la **lunghezza della query (~1,5 KB)**, non il numero
di URI: misurato il 2026-11-19, 1.508 B passano, 1.568 B → **403 immediato**
(non è rate-limit). La full non ha IN-list (pagina per graph, query da 245
caratteri) e per questo 1,2M righe passano.

I batch si chiudono quindi **per lunghezza** (`_QUERY_MAX_CHARS = 1300`, ~210 B
di margine), non per conteggio. Conta la base della query: la meta ha ~800 B
più della voti, quindi sta in **~5 sedute per batch** mentre i voti stanno in
**~25 per batch**. Con la regola sul numero (20) la meta a 20 sedute era
1.968 B → 403.

L'altro limite è il numero di richieste (~8-16 in pochi minuti): un delta
molto grande moltiplica i batch (478 sedute → 96 query meta) e non è la strada
dopo una pausa lunga — lì la cache scade e si va di full, che non ha IN-list.

Le query "unione" usano il default graph di Virtuoso, che è l'insieme dei
graph (verificato dal vivo).

Il retry ha un **budget totale di attesa per run** (`SENATO_RETRY_BUDGET_S`):
default **480s in incrementale** (il blocco misurato dura >=257s), **nessun
tetto nel full** (un'estrazione completa deve poter finire; resta il ladder
per-query fino a 635s). Il budget limita l'attesa, non i tentativi: l'ultimo
tentativo avviene comunque dopo l'ultima pausa. Esaurito il budget il run
fallisce in pochi minuti invece di restare appeso per un'ora: il parquet non
viene toccato, `max(data)` non avanza e il run successivo riparte dallo stesso
punto (nessun buco).

Il run full (prima estrazione, o legislatura nuova) resta una query per graph
(`graphs_for_legislature`, lista deterministica; `--discover-graphs` per la
scoperta dinamica).

Se un graph fallisce il run **esce con errore** e non fa il merge: un parquet
parziale avanzerebbe `max(data)` e le votazioni mancanti non verrebbero più
riprese. Lo stderr del preprocess (retry WAF inclusi) è visibile nel log del
job: il source `script` del toolkit fa tee su stderr mentre il comando gira.

L'endpoint dati.senato.it ha un WAF restrittivo:
- **TLS-fingerprinting**: le librerie Python (requests/urllib) ricevono 403 o
  risposte vuote; lo script usa il binario `curl` via subprocess
- **Rate-limit a burst**: dopo ~8 richieste pesanti risponde 403 (HTML) per
  diversi minuti. Il retry ha un budget di attesa per run (480s in
  incrementale, nessun tetto nel full): oltre, il run fallisce invece di
  macinare per un'ora (misurato: stop a budget esaurito, parquet intatto)
- **Variabili lunghe**: query con nomi variabile come `?votazione` vengono
  servite vuote; si usano variabili corte (`?v`, `?sen`, `?p`)
- Endpoint capisce a **10.000 righe** per query → paginazione OFFSET

## Limiti noti

- Copre solo la XIX legislatura; per le precedenti (XIII-XVIII) basta lanciare
  lo script con `--legislature N` (graph unici `/13`-`/16`, spezzati dal XVII)
- Il `data` deriva dalla seduta (`osr:dataSeduta`); raro NULL
- Presenza (presente/votante/congedo) solo come conteggi aggregati, non
  individuale — i singoli "assente/giustificato" richiedono un'estensione
