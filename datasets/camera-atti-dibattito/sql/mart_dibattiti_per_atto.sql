-- mart_dibattiti_per_atto.sql

SELECT
    atto_id,
    legislatura,
    COUNT(*) AS n_link,
    COUNT(*) FILTER (WHERE ruolo = 'dibattito') AS n_dibattiti,
    COUNT(*) FILTER (WHERE ruolo = 'abbinamento') AS n_abbinamenti,
    COUNT(*) FILTER (WHERE ruolo = 'atto_abbinato') AS n_atto_abbinato,
    COUNT(DISTINCT target_uri) AS n_target_distinti
FROM clean_input
WHERE atto_id IS NOT NULL
GROUP BY atto_id, legislatura
