-- mart_sintesi.sql — sindacato ispettivo per legislature e tipo
SELECT
    legislatura,
    tipo_categoria AS tipo,
    count(DISTINCT atto_id) AS n_atti,
    count(DISTINCT senatore_id) AS n_senatori,
    sum(CASE WHEN esito IS NOT NULL THEN 1 ELSE 0 END) AS n_con_esito
FROM clean_input
GROUP BY legislatura, tipo_categoria
ORDER BY legislatura, n_atti DESC
