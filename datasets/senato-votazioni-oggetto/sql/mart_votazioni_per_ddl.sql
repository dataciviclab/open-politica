-- mart_votazioni_per_ddl.sql — sintesi votazioni raggiungibili per DDL
-- ddl_id = osr:idDdl (BIGINT)

SELECT
    ddl_id,
    legislatura,
    COUNT(*) AS n_votazioni,
    COUNT(*) FILTER (WHERE esito = 'approvato') AS n_approvate,
    COUNT(*) FILTER (WHERE esito = 'respinto') AS n_respinte,
    COUNT(*) FILTER (WHERE esito IS NULL OR esito = '') AS n_senza_esito,
    COUNT(DISTINCT oggetto_id) AS n_oggetti,
    MIN(votazione_id) AS sample_votazione
FROM clean_input
WHERE ddl_id IS NOT NULL
GROUP BY ddl_id, legislatura
