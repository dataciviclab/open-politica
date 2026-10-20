-- mart_sintesi — atti per legislatura e tipo, con tasso di risposta
SELECT
    legislatura,
    tipo_categoria,
    count(*)                                                AS n_atti,
    count(*) FILTER (WHERE ha_risposta)                     AS n_con_risposta,
    round(
        100.0 * count(*) FILTER (WHERE ha_risposta) / count(*), 2
    )                                                       AS pct_con_risposta,
    count(DISTINCT primo_firmatario_uri)                    AS n_primi_firmatari
FROM clean_input
GROUP BY legislatura, tipo_categoria
ORDER BY legislatura, n_atti DESC
