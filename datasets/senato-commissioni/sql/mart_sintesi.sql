-- mart_sintesi — composizione per commissione (membri attuali)
SELECT
    commissione_id,
    max(nome)     AS nome,
    max(categoria) AS categoria,
    max(materia)  AS materia,
    count(*)      AS n_membri,
    count(*) FILTER (WHERE carica = 'Presidente')     AS n_presidenti,
    count(*) FILTER (WHERE carica = 'Vicepresidente') AS n_vicepresidenti
FROM clean_input
WHERE data_fine IS NULL
GROUP BY commissione_id
ORDER BY n_membri DESC
