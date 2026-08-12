-- mart_sintesi — serie per anno delle votazioni Camera (XIX leg.)
WITH vot AS (
    SELECT votazione, data
    FROM clean_input
    GROUP BY votazione, data
)
SELECT
    year(data)  AS anno,
    count(*)    AS n_votazioni
FROM vot
GROUP BY year(data)
ORDER BY anno
