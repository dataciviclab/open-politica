-- mart_anno.sql — camera_leggi
-- Leggi per anno di promulgazione

SELECT
    anno,
    COUNT(*) AS n_leggi
FROM clean_input
WHERE anno IS NOT NULL
GROUP BY anno
ORDER BY anno
