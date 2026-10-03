-- mart_sintesi — composizione per commissione nella legislatura.
-- Multi-leg (13–19): le legislature storiche hanno data_fine su tutte le
-- afferenze → senza filtro "attuali" (Leg19-only). Conta tutti i periodi.
SELECT
    commissione_id,
    max(nome)     AS nome,
    max(categoria) AS categoria,
    max(materia)  AS materia,
    count(*)      AS n_membri,
    count(*) FILTER (WHERE carica = 'Presidente')     AS n_presidenti,
    count(*) FILTER (WHERE carica = 'Vicepresidente') AS n_vicepresidenti,
    count(*) FILTER (WHERE data_fine IS NULL)         AS n_in_carica
FROM clean_input
GROUP BY commissione_id
ORDER BY n_membri DESC
