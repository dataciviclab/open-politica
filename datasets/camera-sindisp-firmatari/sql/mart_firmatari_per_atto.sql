-- mart_firmatari_per_atto — quanti firmatari per atto
SELECT
    atto_id,
    count(*)                                        AS n_firmatari,
    count(*) FILTER (WHERE ruolo = 'primo')         AS n_primo,
    count(*) FILTER (WHERE ruolo = 'altro')         AS n_altro,
    count(DISTINCT persona_id)                      AS n_persone
FROM clean_input
GROUP BY atto_id
