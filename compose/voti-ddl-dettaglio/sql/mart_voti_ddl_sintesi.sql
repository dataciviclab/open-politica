-- mart_voti_ddl_sintesi.sql — aggregato per DDL (peso contenuto)

SELECT
    ddl_id,
    legislatura,
    COUNT(*) AS n_voti,
    COUNT(DISTINCT senatore_id) AS n_senatori,
    COUNT(DISTINCT votazione_id) AS n_votazioni,
    COUNT(*) FILTER (WHERE voto = 'FAVOREVOLE') AS n_fav,
    COUNT(*) FILTER (WHERE voto = 'CONTRARIO') AS n_contr,
    COUNT(*) FILTER (WHERE voto = 'ASTENUTO') AS n_ast,
    MIN(esito_votazione) AS esito_sample,
    MIN(ddl_titolo) AS titolo_sample
FROM clean_input
GROUP BY ddl_id, legislatura
