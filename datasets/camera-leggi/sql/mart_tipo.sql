-- mart_tipo.sql — camera_leggi
-- Distribuzione leggi per tipo

SELECT
    tipo,
    COUNT(*) AS n_leggi
FROM clean_input
WHERE tipo IS NOT NULL
GROUP BY tipo
ORDER BY n_leggi DESC
