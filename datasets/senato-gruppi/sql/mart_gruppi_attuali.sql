-- mart_gruppi_attuali — composizione dei gruppi nella legislatura.
-- Multi-leg (13–19): le legislature storiche hanno data_fine su tutte le
-- membership (nessuna è "ancora in carica" al runtime). Il mart cattura
-- quindi TUTTI i periodi di adesione della legislatura, non solo i null.
SELECT
    gruppo_id,
    max(nome_gruppo)  AS nome_gruppo,
    max(sigla)        AS sigla,
    count(*)          AS n_senatori,
    count(*) FILTER (WHERE data_fine IS NULL) AS n_in_carica
FROM clean_input
GROUP BY gruppo_id
ORDER BY n_senatori DESC
