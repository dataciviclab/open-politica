-- mart_anni — serie per anno di presentazione (data della discussione/atto)
SELECT
    legislatura,
    anno,
    tipo_categoria,
    count(*) AS n_atti
FROM clean_input
WHERE anno IS NOT NULL
GROUP BY legislatura, anno, tipo_categoria
ORDER BY legislatura, anno, n_atti DESC
