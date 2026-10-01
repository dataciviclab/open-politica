-- mart_firmatari_per_deputato.sql

SELECT
    persona_id,
    deputato_uri,
    MIN(deputato_label) AS label,
    legislatura,
    COUNT(*) AS n_firmate,
    COUNT(DISTINCT atto_id) AS n_atti
FROM clean_input
WHERE persona_id IS NOT NULL
GROUP BY persona_id, deputato_uri, legislatura
