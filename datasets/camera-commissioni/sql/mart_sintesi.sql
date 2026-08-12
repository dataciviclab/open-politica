-- mart_sintesi — composizione per organo (membri attuali)
SELECT
    organo_id,
    max(nome)    AS nome,
    count(*)     AS n_membri,
    count(*) FILTER (WHERE carica = 'PRESIDENTE')     AS n_presidenti,
    count(*) FILTER (WHERE carica = 'VICEPRESIDENTE') AS n_vicepresidenti
FROM clean_input
WHERE data_fine IS NULL
GROUP BY organo_id
ORDER BY n_membri DESC
