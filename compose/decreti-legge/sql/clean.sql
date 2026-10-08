-- clean.sql — decreti_legge
--
-- I decreti-legge dal lato Parlamento: il DL emanato dal Governo arriva in
-- Senato come "disegno di legge di conversione" (senato_ddl, natura).
-- senato_ddl ha più righe per DDL (una per fase dell'iter) e, per lo stesso
-- DL, possono esistere più id_ddl (ramo Camera + Senato, o iter distinti).
-- Si aggrega per (dl_numero, dl_anno) e si sceglie UN ddl_id representative:
--   1) preferenza ramo Senato (ramo = 'S')
--   2) poi data_legge / data_presentazione più recente
-- ddl_id è representative, non univoco per costruzione (vedi notes #63).
--
-- external multi-anno: {support.*.clean} è una lista SQL di URL (no quote)
WITH conv AS (
    SELECT
        id_ddl,
        ramo,
        fase,
        data_presentazione,
        data_legge,
        numero_legge,
        stato,
        titolo
    FROM read_parquet({support.senato_ddl.clean})
    WHERE natura = 'di conversione di decreto-legge'
      AND regexp_extract(titolo, 'n\.\s*(\d+)', 1) != ''
)
SELECT
    TRY_CAST(regexp_extract(titolo, 'n\.\s*(\d+)', 1) AS BIGINT)     AS dl_numero,
    year(min(data_presentazione))                                     AS dl_anno,
    min(data_presentazione)                                           AS data_presentazione,
    max(data_legge)                                                   AS data_conversione,
    CASE
        WHEN bool_or(numero_legge IS NOT NULL) THEN 'convertito'
        WHEN bool_or(stato = 'D-L decaduto') THEN 'decaduto'
        WHEN bool_or(stato = 'restit. al Governo') THEN 'restituito'
        ELSE 'in_esame'
    END                                                               AS esito,
    round(date_diff('day', min(data_presentazione), max(data_legge)), 0)
                                                                      AS giorni_conversione,
    normalize_string(arg_max(titolo, coalesce(data_legge, '1900-01-01'))) AS titolo,
    -- Chiave verso senato_ddl / legal-graph (#63): 1 id_ddl representative.
    -- Ordine: ramo S > data più recente. Se un DL ha più iter (C+S o
    -- ripresentazioni), l'edge grafo punta a questo id_ddl — non univoco.
    arg_max(
        id_ddl,
        (CASE WHEN ramo = 'S' THEN 1 ELSE 0 END) * 1000000000000
        + epoch(coalesce(data_legge, data_presentazione, DATE '1900-01-01'))
    )                                                               AS ddl_id,
    arg_max(
        ramo,
        (CASE WHEN ramo = 'S' THEN 1 ELSE 0 END) * 1000000000000
        + epoch(coalesce(data_legge, data_presentazione, DATE '1900-01-01'))
    )                                                               AS ddl_ramo,
    count(DISTINCT id_ddl)                                          AS n_id_ddl_iter
FROM conv
-- multi-leg: i numeri DL ripartono ogni anno → PK (dl_numero, dl_anno)
GROUP BY
    regexp_extract(titolo, 'n\.\s*(\d+)', 1),
    year(data_presentazione)
