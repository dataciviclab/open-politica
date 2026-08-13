-- mart_top_relatori — i deputati più "registi"
SELECT
    deputato_id,
    count(*)                AS n_incarichi,
    min(data)               AS primo_incarico,
    max(data)               AS ultimo_incarico
FROM clean_input
GROUP BY deputato_id
ORDER BY n_incarichi DESC
