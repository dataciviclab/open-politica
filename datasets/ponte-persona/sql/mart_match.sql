-- mart_match — qualità del ponte Camera↔Senato
SELECT
    tipo_match,
    count(*)                                          AS n,
    count(DISTINCT senatore_id)                       AS n_senatori,
    count(DISTINCT persona_id)                        AS n_personas
FROM clean_input
GROUP BY tipo_match
ORDER BY n DESC
