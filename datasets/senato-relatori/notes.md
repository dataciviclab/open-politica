# senato_relatori — relatore → DDL → senatore

Collega i **DDL del Senato** ai **relatori** (e ai relativi `senatore_id`).

## Catena

```text
Ddl  →  osr:relatore (bnode)  →  osr:senatore  →  senatore/ID
```

## Volume atteso

- ~55k relazioni relatore·DDL
- ~23k con `senatore` URI (estratto come `senatore_id`)
- Etichette tipo "Sen. Luigi Biscardi"

## Join utili

- `senato_relatori.ddl_id` → `senato_ddl.id_ddl`
- `senato_relatori.senatore_id` → `senato_anagrafica.senatore_id` / `senato_votazioni.senatore_id`

## Limiti

- I nodi relatore sono bnode (`nodeID://…`) — non hanno URI stabili
- `senatore` non sempre presente (~40% delle relazioni)
- Default graph (i named graph spezzano il join)
