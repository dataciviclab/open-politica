-- clean.sql — decreti_legge
--
-- I decreti-legge dal lato Parlamento: il DL emanato dal Governo arriva in
-- Senato come "disegno di legge di conversione" (senato_ddl, natura).
-- senato_ddl ha più righe per DDL (una per fase dell'iter) e, per lo stesso
-- DL, possono esistere più id_ddl (ramo Camera + Senato, o iter distinti).
--
-- IDENTITÀ DEL DL: `(dl_numero, anno del decreto)`.
-- Non si può usare `year(data_presentazione)`: la data di presentazione è
-- quella del DDL di conversione, e per un DL emanato a dicembre il ramo
-- Senato presenta a dicembre (anno X) mentre la Camera a gennaio (anno X+1).
-- Con quell'anno come chiave lo stesso DL si sdoppia e finisce per fondersi
-- con un DL diverso che ha lo stesso numero l'anno dopo, producendo durate
-- impossibili (es. 401 giorni: misurato 2026-10-30). La data del decreto si
-- legge dal titolo ("decreto-legge 27 dicembre 2024, n. 200"), con fallback
-- sulla forma numerica ("del 30/12/1999"); se il titolo non è interpretabile
-- si ricade su `year(data_presentazione)` e lo si dichiara in `data_dl_fonte`.
--
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
),

-- Data del decreto: parte variabile ("27 dicembre 2024", "1° ottobre 2005").
-- Il prefisso ha tre forme in circolazione: "decreto-legge", "decreto legge",
-- "decreto - legge", a volte seguito da "del".
m AS (
    SELECT
        *,
        regexp_extract(
            titolo,
            '(?i)decreto\s*-?\s*legge\s+(?:del\s+)?(\d{1,2}(?:°)?\s+[a-zà-ù]+\s+\d{4})',
            1
        ) AS data_txt
    FROM conv
),

parsed AS (
    SELECT
        *,
        TRY_CAST(regexp_extract(data_txt, '^(\d{1,2})', 1) AS INTEGER) AS gg,
        CASE lower(regexp_extract(data_txt, '^\d{1,2}°?\s+([a-zà-ù]+)', 1))
            WHEN 'gennaio' THEN 1 WHEN 'febbraio' THEN 2 WHEN 'marzo' THEN 3
            WHEN 'aprile' THEN 4 WHEN 'maggio' THEN 5 WHEN 'giugno' THEN 6
            WHEN 'luglio' THEN 7 WHEN 'agosto' THEN 8 WHEN 'settembre' THEN 9
            WHEN 'ottobre' THEN 10 WHEN 'novembre' THEN 11 WHEN 'dicembre' THEN 12
        END AS mm,
        TRY_CAST(regexp_extract(data_txt, '(\d{4})$', 1) AS INTEGER) AS aaaa,
        -- fallback: "decreto legge n.500 del 30/12/1999"
        TRY_CAST(try_strptime(
            regexp_extract(titolo, 'del\s+(\d{1,2}/\d{1,2}/\d{4})', 1), '%d/%m/%Y'
        ) AS DATE) AS data_num
    FROM m
),

con_dl AS (
    SELECT
        *,
        COALESCE(
            TRY_CAST(printf('%04d-%02d-%02d', aaaa, mm, gg) AS DATE),
            data_num
        ) AS data_dl
    FROM parsed
),

pre AS (
    SELECT
        TRY_CAST(regexp_extract(titolo, 'n\.\s*(\d+)', 1) AS BIGINT) AS dl_numero,
        COALESCE(year(data_dl), year(data_presentazione))             AS dl_anno,
        data_presentazione,
        data_legge,
        numero_legge,
        stato,
        id_ddl,
        ramo,
        titolo,
        data_dl
    FROM con_dl
)

SELECT
    dl_numero,
    dl_anno,
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
    count(DISTINCT id_ddl)                                          AS n_id_ddl_iter,
    -- Data del decreto ricavata dal titolo (NULL se non interpretabile)
    min(data_dl)                                                    AS data_dl,
    CASE WHEN count(data_dl) > 0 THEN 'titolo' ELSE 'presentazione' END AS data_dl_fonte
FROM pre
-- multi-leg: i numeri DL ripartono ogni anno → PK (dl_numero, dl_anno)
GROUP BY dl_numero, dl_anno
