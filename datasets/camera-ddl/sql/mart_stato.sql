-- mart_stato.sql — camera_ddl
-- DDL per stato dell'iter (distribuzione)

SELECT
    stato,
    COUNT(*) AS n_ddl
FROM clean_input
WHERE stato IS NOT NULL
GROUP BY stato
ORDER BY n_ddl DESC
