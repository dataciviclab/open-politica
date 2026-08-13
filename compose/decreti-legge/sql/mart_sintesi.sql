-- mart_sintesi — decreti-legge per anno (il "governo che legifera da solo")
SELECT
    dl_anno                                                          AS anno,
    count(*)                                              AS n_dl,
    count(*) FILTER (WHERE esito = 'convertito')          AS n_convertiti,
    count(*) FILTER (WHERE esito = 'decaduto')            AS n_decaduti,
    count(*) FILTER (WHERE esito = 'restituito')          AS n_restituiti,
    round(100.0 * count(*) FILTER (WHERE esito = 'convertito')
          / NULLIF(count(*), 0), 1)                       AS pct_convertiti,
    round(avg(giorni_conversione) FILTER (WHERE esito = 'convertito'), 1)
                                                          AS giorni_conversione_medio
FROM clean_input
GROUP BY dl_anno
ORDER BY anno
