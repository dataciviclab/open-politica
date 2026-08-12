-- mart_gruppi_attuali — composizione dei gruppi in carica (fine IS NULL)
SELECT
    gruppo_id,
    max(nome_gruppo)  AS nome_gruppo,
    max(sigla)        AS sigla,
    count(*)          AS n_senatori
FROM clean_input
WHERE data_fine IS NULL
GROUP BY gruppo_id
ORDER BY n_senatori DESC
