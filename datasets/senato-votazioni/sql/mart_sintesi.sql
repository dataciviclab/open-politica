-- mart_sintesi — serie per anno delle votazioni del Senato (XIX leg.)
-- Una riga per anno: numero di votazioni e medie di partecipazione.
WITH vot AS (
    SELECT
        votazione,
        data,
        esito,
        max(n_votanti)        AS n_votanti,
        max(n_favorevoli)     AS n_favorevoli,
        max(n_contrari)       AS n_contrari,
        max(n_astenuti)       AS n_astenuti,
        max(n_presenti)       AS n_presenti
    FROM clean_input
    GROUP BY votazione, data, esito
)
SELECT
    year(data)                                          AS anno,
    count(*)                                            AS n_votazioni,
    round(avg(n_votanti), 1)                            AS media_votanti,
    round(avg(n_presenti), 1)                           AS media_presenti,
    round(avg(n_favorevoli), 1)                         AS media_favorevoli,
    round(avg(n_contrari), 1)                           AS media_contrari,
    round(avg(n_astenuti), 1)                           AS media_astenuti,
    count(*) FILTER (WHERE esito = 'approvato')         AS n_approvate,
    round(
        100.0 * count(*) FILTER (WHERE esito = 'approvato') / NULLIF(count(*), 0), 1
    )                                                   AS pct_approvate
FROM vot
GROUP BY year(data)
ORDER BY anno
