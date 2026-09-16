-- mart_anno.sql — camera_ddl
-- DDL per anno di presentazione

SELECT
    anno,
    COUNT(*) AS n_ddl
FROM clean_input
WHERE anno IS NOT NULL
GROUP BY anno
ORDER BY anno
