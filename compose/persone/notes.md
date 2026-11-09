# persone — note di contratto

Dimensione **identità**, non prodotto: risponde a "chi è questa persona" con
una chiave stabile. Le metriche (voti, presenze, coerenza di gruppo) restano
nel prodotto `osservatorio` (giro 3).

## Grain e chiave

Una riga per **(persona_key, ramo, sistema, legislatura)**.

`persona_key`:
- Camera: `persona_id` (numerico, id Camera);
- Senato: `persona_id` se il **ponte** Camera↔Senato la conosce, altrimenti
  `sen:{senatore_id}`.

Così lo stesso parlamentare che è stato deputato e senatore ha **una chiave**
e due righe (ramo diverso) — il ponte è il punto in cui le due identità si
uniscono. Con il ponte `persona_id` e `senatore_id` sono entrambi valorizzati
(`ponte = true`).

## Le due trappole dichiarate

1. **`persona_id` non è lo stesso identificatore ovunque.**
   `camera_deputati_legislature`, `camera_firmatari` e `ponte_persona` usano il
   **numerico Camera** (`4416`); `senato_dibattito` usa una stringa Senato
   (`'p1103'`) che è un namespace diverso. `persone` non usa mai quel valore:
   dal dibattito prende solo `senatore_id`.

2. **La Camera copre Regno + Costituente + Repubblica.**
   `camera_deputati_legislature` ha `regno_01..30`, `costituente`,
   `repubblica_01..19`: il **numero da solo collide** (`regno_19` =
   `repubblica_19`). Per questo ci sono `sistema` e `legislatura` separate, e
   il perimetro è **Repubblica 13-19** — lo stesso delle relazioni del grafo
   (fuori da lì le persone sono nodi isolati). Per estendere al Regno basta
   cambiare il filtro in `clean.sql`.

## Fonti (priorità per la stessa riga)

| Priorità | Fonte | Porta | Copertura |
|---|---|---|---|
| 1 | `senato_anagrafica` | nome, cognome, nascita, luogo | 2.246 righe, Leg13-19 |
| 2 | `senato_dibattito` (senato-akn) | solo cognome (`nome_oratore`) | copre **110 senatori** assenti dall'anagrafica, Leg17-19 |
| 3 | `camera_deputati_legislature` | nome, cognome, gender | 4.377 righe, Repubblica Leg13-19 |
| 4 | `camera_firmatari` | label (`COGNOME NOME, …`) | persone con un atto ma senza anagrafica (es. Renzi) |

Le colonne assenti nella fonte vincente si completano con `MAX()` sulle altre
righe della stessa chiave: nome dall'anagrafica, gender dalla Camera. `fonte`
è la fonte vincente, `n_fonti` quante righe contribuiscono.

## Non fa (di proposito)

- **Gruppi, commissioni, ruoli di governo**: sono attributi *di attività* per
  legislatura (many-to-many, con date), non identità. Vanno nel prodotto.
- **Metriche di voto**: prodotto (`osservatorio`).
- **Regno e Costituente**: fuori perimetro finché il grafo non ha relazioni
  lì (`sistema` esiste già per non dover rifare lo schema).
