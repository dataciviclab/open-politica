-- mart_sintesi — composizione per organo nella legislatura.
-- Multi-leg (13–19): le legislature storiche hanno data_fine su tutte le
-- membership → senza filtro "attuali" (Leg19-only).
SELECT
    organo_id,
    max(nome)    AS nome,
    count(*)     AS n_membri,
    count(*) FILTER (WHERE carica = 'PRESIDENTE')     AS n_presidenti,
    count(*) FILTER (WHERE carica = 'VICEPRESIDENTE') AS n_vicepresidenti,
    count(*) FILTER (WHERE data_fine IS NULL)         AS n_in_carica
FROM clean_input
GROUP BY organo_id
ORDER BY n_membri DESC
