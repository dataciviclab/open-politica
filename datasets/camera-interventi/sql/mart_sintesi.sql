-- mart_sintesi — interventi per anno
SELECT
    year(data)              AS anno,
    count(*)                AS n_interventi,
    count(DISTINCT deputato_id) AS n_parlanti
FROM clean_input
WHERE data IS NOT NULL
GROUP BY year(data)
ORDER BY anno
