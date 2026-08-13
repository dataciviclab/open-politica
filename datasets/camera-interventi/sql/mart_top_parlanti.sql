-- mart_top_parlanti — chi parla di più
SELECT
    deputato_id,
    count(*)                AS n_interventi,
    min(data)               AS primo_intervento,
    max(data)               AS ultimo_intervento
FROM clean_input
GROUP BY deputato_id
ORDER BY n_interventi DESC
