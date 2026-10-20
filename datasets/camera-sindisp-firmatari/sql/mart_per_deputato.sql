-- mart_per_deputato — atti firmati per deputato e legislatura
SELECT
    persona_id,
    firmatario_uri,
    legislatura,
    count(*)                                    AS n_firmate,
    count(*) FILTER (WHERE ruolo = 'primo')     AS n_primo,
    count(DISTINCT atto_id)                     AS n_atti,
    min(firmatario_label)                       AS label
FROM clean_input
WHERE persona_id IS NOT NULL
GROUP BY persona_id, firmatario_uri, legislatura
ORDER BY n_atti DESC
