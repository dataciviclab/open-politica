-- mart_per_atto.sql — emendamenti per atto (solo dove il bridge oggetto→ddl esiste)
SELECT
    legislatura,
    atto_num,
    count(*)                                             AS n_emendamenti,
    CAST(sum(CASE WHEN ramo = 'aula'        THEN 1 ELSE 0 END) AS BIGINT) AS n_aula,
    CAST(sum(CASE WHEN ramo = 'commissione' THEN 1 ELSE 0 END) AS BIGINT) AS n_commissione
FROM clean_input
WHERE atto_num IS NOT NULL
GROUP BY legislatura, atto_num
ORDER BY legislatura, n_emendamenti DESC
