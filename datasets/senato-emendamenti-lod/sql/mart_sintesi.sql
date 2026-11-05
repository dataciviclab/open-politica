-- mart_sintesi.sql — emendamenti per legislatura e ramo (aula/commissione)
SELECT
    legislatura,
    ramo,
    count(*) AS n_emendamenti
FROM clean_input
GROUP BY legislatura, ramo
ORDER BY legislatura, ramo
