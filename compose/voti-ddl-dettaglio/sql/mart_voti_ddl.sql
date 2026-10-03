-- mart_voti_ddl.sql — dettaglio (una riga per voto su votazione con ddl)

SELECT
    votazione_id,
    senatore_id,
    nome,
    cognome,
    voto,
    data,
    ddl_id,
    oggetto_id,
    esito_votazione,
    tipo_votazione,
    legislatura,
    ddl_titolo,
    ddl_stato,
    numero_legge,
    urn_normattiva
FROM clean_input
ORDER BY ddl_id, votazione_id, senatore_id
