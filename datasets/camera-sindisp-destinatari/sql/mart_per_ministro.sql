-- mart_per_ministro — atti ricevuti e tasso di risposta per ministro
SELECT
    organo_id,
    destinatario_label,
    legislatura,
    count(*)                                    AS n_atti,
    count(*) FILTER (WHERE ha_risposta)         AS n_con_risposta,
    round(
        100.0 * count(*) FILTER (WHERE ha_risposta) / count(*), 2
    )                                           AS pct_con_risposta
FROM clean_input
GROUP BY organo_id, destinatario_label, legislatura
ORDER BY legislatura, n_atti DESC
