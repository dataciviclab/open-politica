-- clean.sql — decreti_legge
--
-- I decreti-legge dal lato Parlamento: il DL emanato dal Governo arriva in
-- Senato come "disegno di legge di conversione" (senato_ddl, natura).
-- senato_ddl ha più righe per DDL (una per fase dell'iter) → si aggrega
-- per (numero, anno) prendendo l'esito "migliore" (convertito > decaduto >
-- restituito > in esame). La data di presentazione coincide con quella del DL.
WITH conv AS (
    SELECT *
    FROM read_parquet('{support.senato_ddl.clean}')
    WHERE natura = 'di conversione di decreto-legge'
      AND regexp_extract(titolo, 'n\.\s*(\d+)', 1) != ''
)
SELECT
    TRY_CAST(regexp_extract(titolo, 'n\.\s*(\d+)', 1) AS BIGINT) AS dl_numero,
    year(min(data_presentazione))                                 AS dl_anno,
    min(data_presentazione)                                       AS data_presentazione,
    max(data_legge)                                               AS data_conversione,
    CASE
        WHEN bool_or(numero_legge IS NOT NULL) THEN 'convertito'
        WHEN bool_or(stato = 'D-L decaduto') THEN 'decaduto'
        WHEN bool_or(stato = 'restit. al Governo') THEN 'restituito'
        ELSE 'in_esame'
    END                                                           AS esito,
    round(date_diff('day', min(data_presentazione), max(data_legge)), 0)
                                                                  AS giorni_conversione,
    normalize_string(arg_max(titolo, coalesce(data_legge, '1900-01-01'))) AS titolo
FROM conv
GROUP BY regexp_extract(titolo, 'n\.\s*(\d+)', 1)
