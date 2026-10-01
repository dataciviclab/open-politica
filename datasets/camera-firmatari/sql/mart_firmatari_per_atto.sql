-- mart_firmatari_per_atto.sql

SELECT
    atto_id,
    legislatura,
    COUNT(*) AS n_firmatari,
    COUNT(*) FILTER (WHERE ruolo = 'primo') AS n_primo,
    COUNT(*) FILTER (WHERE ruolo = 'altro') AS n_altro,
    COUNT(DISTINCT persona_id) AS n_persone,
    MIN(deputato_label) AS sample_firmatario
FROM clean_input
WHERE atto_id IS NOT NULL
GROUP BY atto_id, legislatura
