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

`--incremental` non rilegge tutta la legislatura:

1. una query per le sedute, poi tiene solo quelle con `dataSeduta >= max(data)`;
2. **se non ci sono sedute nuove termina subito** (1 query, prima erano una
   per graph più una scoperta globale);
3. i metadati si chiedono solo per quelle sedute, non per tutte le ~8k
   votazioni;
4. i voti si chiedono solo per le votazioni nuove.

I graph sono una lista deterministica per legislatura
(`graphs_for_legislature`); `--discover-graphs` ripristina la query globale.

Se un graph fallisce il run **esce con errore** e non fa il merge: un parquet
parziale avanzerebbe `max(data)` e le votazioni mancanti non verrebbero più
riprese. Lo stderr del preprocess (retry WAF inclusi) è visibile nel log del
job: il source `script` del toolkit fa tee su stderr mentre il comando gira.

L'endpoint dati.senato.it ha un WAF restrittivo:
- **TLS-fingerprinting**: le librerie Python (requests/urllib) ricevono 403 o
  risposte vuote; lo script usa il binario `curl` via subprocess
- **Rate-limit a burst**: dopo poche query pesanti risponde 403 (HTML) per ~1
  minuto; lo script rileva l'HTML, attende (backoff fino a 300s) e ritenta
- **Variabili lunghe**: query con nomi variabile come `?votazione` vengono
  servite vuote; si usano variabili corte (`?v`, `?sen`, `?p`)
- Endpoint capisce a **10.000 righe** per query → paginazione OFFSET

## Limiti noti

- Copre solo la XIX legislatura; per le precedenti (XIII-XVIII) basta lanciare
  lo script con `--legislature N` (graph unici `/13`-`/16`, spezzati dal XVII)
- Il `data` deriva dalla seduta (`osr:dataSeduta`); raro NULL
- Presenza (presente/votante/congedo) solo come conteggi aggregati, non
  individuale — i singoli "assente/giustificato" richiedono un'estensione
