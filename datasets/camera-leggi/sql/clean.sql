-- clean.sql — camera_leggi
--
-- Leggi approvate dalla Camera dei Deputati (XIX leg.).
-- Input: SPARQL da dati.camera.it — ocd:legge con ocd:lex → Normattiva.
-- Il titolo contiene il numero del DDL tra parentesi: "..." (3053)
-- → estraiamo ddl_numero come ponte verso camera_ddl.

WITH raw_dedup AS (
    SELECT
        normalize_string(leg)                                               AS legge_camera,
        -- ID numerico: L2026_145 → 145, LC2026_2 → 2
        TRY_CAST(
            regexp_extract(normalize_string(leg), 'L[C]?\d+_(\d+)', 1) AS BIGINT
        )                                                                   AS id_legge,
        normalize_string(label)                                             AS titolo,
        normalize_string(tipo)                                              AS tipo,
        -- Data promulgazione: YYYYMMDD → DATE
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
            substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
            substr(CAST(data AS VARCHAR), 7, 2)
            AS DATE
        )                                                                   AS data_promulgazione,
        -- Legislatura: estratta da URI
        TRY_CAST(
            REPLACE(
                REPLACE(normalize_string(leg_num),
                    'http://dati.camera.it/ocd/legislatura.rdf/repubblica_', ''),
                'http://dati.camera.it/ocd/legislatura.rdf/', ''
            ) AS INTEGER
        )                                                                   AS legislatura,
        -- Anno
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) AS INTEGER
        )                                                                   AS anno,
        -- URN Normattiva: estratta da ocd:lex
        CASE
            WHEN lex IS NOT NULL AND lex != '' THEN
                REPLACE(normalize_string(lex),
                        'http://www.normattiva.it/uri-res/N2Ls?', '')
            ELSE NULL
        END                                                                 AS urn_normattiva,
        -- Pubblicazione GU
        normalize_string(gu)                                                AS gu_pubblicazione,
        -- DDL number: estratto dal titolo tra parentesi "(3053)" → 3053
        TRY_CAST(
            regexp_extract(normalize_string(label), '\((\d+)(?:-\w+)?\)\s*$', 1) AS BIGINT
        )                                                                   AS ddl_numero,
        ROW_NUMBER() OVER (
            PARTITION BY
                TRY_CAST(regexp_extract(normalize_string(leg), 'L[C]?\d+_(\d+)', 1) AS BIGINT)
            ORDER BY
                TRY_CAST(
                    substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
                    substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
                    substr(CAST(data AS VARCHAR), 7, 2)
                    AS DATE
                ) DESC
        )                                                                   AS _rn
    FROM raw_input
)
SELECT
    legge_camera, id_legge, titolo, tipo, data_promulgazione,
    legislatura, anno, urn_normattiva, gu_pubblicazione, ddl_numero
FROM raw_dedup
WHERE _rn = 1
