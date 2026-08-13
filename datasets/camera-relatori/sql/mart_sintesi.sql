-- mart_sintesi — incarichi da relatore per anno
SELECT
    year(data)              AS anno,
    count(*)                AS n_incarichi,
    count(DISTINCT deputato_id) AS n_relatori
FROM clean_input
WHERE data IS NOT NULL
GROUP BY year(data)
ORDER BY anno
