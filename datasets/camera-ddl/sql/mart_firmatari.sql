-- mart_firmatari.sql — camera_ddl
-- Top firmatari per numero di DDL presentati

SELECT
    primo_firmatario,
    COUNT(*) AS n_ddl
FROM clean_input
WHERE primo_firmatario IS NOT NULL
  AND primo_firmatario != ''
GROUP BY primo_firmatario
ORDER BY n_ddl DESC
