-- clean.sql — camera_leggi
--
-- Leggi Camera + ponte Normattiva/GU/atto.
-- Source 1: legislature 13–19 (tutte le leggi collegate a repubblica_{year}).
-- Source 2: costituzionali LC* su TUTTE le legislature (pre-1996 + atto/natura).
-- Unione con read.mode: all → colonne atto/natura presenti solo sulla source 2.
--
-- Il titolo contiene il numero del DDL tra parentesi: "..." (3053)
-- → ddl_numero. Per le costituzionali si usa anche ocd:rif_attoCamera
-- (URI ac{leg}_{n}, es. ac19_715) come chiave atto Camera.

WITH raw_norm AS (
    SELECT
        raw_input.*,
        REPLACE(COALESCE(normalize_string(lex), ''),
                'http://www.normattiva.it/uri-res/N2Ls?', '')              AS urn_normattiva_norm
    FROM raw_input
),

raw_dedup AS (
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
        -- Legislatura: estratta da URI (opzionale sul source costituzionali)
        TRY_CAST(
            REPLACE(
                REPLACE(normalize_string(leg_num),
                    'http://dati.camera.it/ocd/legislatura.rdf/repubblica_', ''),
                'http://dati.camera.it/ocd/legislatura.rdf/', ''
            ) AS INTEGER
        )                                                                   AS legislatura,
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) AS INTEGER
        )                                                                   AS anno,
        NULLIF(urn_normattiva_norm, '')                                     AS urn_normattiva,
        normalize_string(gu)                                                AS gu_pubblicazione,
        -- ddl_numero: parentesi finale del titolo, oppure numero in URI atto
        COALESCE(
            TRY_CAST(
                regexp_extract(normalize_string(label), '\((\d+)(?:-\w+)?\)(?:\s*\^\^.*)?$', 1) AS BIGINT
            ),
            TRY_CAST(
                regexp_extract(normalize_string(atto), 'ac\d+_(\d+)', 1) AS BIGINT
            )
        )                                                                   AS ddl_numero,
        NULLIF(normalize_string(atto), '')                                  AS atto_camera,
        NULLIF(normalize_string(natura_atto), '')                           AS natura_atto,
        -- Chiavi URN per join con revisioni_costituzionali
        -- full-date: 2001-10-18;3  |  year-form: 2001;3
        CASE
            WHEN NULLIF(urn_normattiva_norm, '') IS NOT NULL
             AND regexp_extract(urn_normattiva_norm, '(\d{4}-\d{2}-\d{2});(\d+)', 2) <> ''
                THEN regexp_extract(urn_normattiva_norm, '(\d{4}-\d{2}-\d{2});(\d+)', 1)
                    || ';' || regexp_extract(urn_normattiva_norm, '(\d{4}-\d{2}-\d{2});(\d+)', 2)
            ELSE NULL
        END                                                                 AS legge_key_full,
        CASE
            WHEN NULLIF(urn_normattiva_norm, '') IS NOT NULL
             AND regexp_extract(urn_normattiva_norm, '(\d{4})(?:-\d{2}-\d{2})?;(\d+)', 2) <> ''
                THEN regexp_extract(urn_normattiva_norm, '(\d{4})(?:-\d{2}-\d{2})?;(\d+)', 1)
                    || ';' || regexp_extract(urn_normattiva_norm, '(\d{4})(?:-\d{2}-\d{2})?;(\d+)', 2)
            ELSE NULL
        END                                                                 AS legge_key_year,
        ROW_NUMBER() OVER (
            -- PK = legge_camera (URI): L[C]{anno}_{n} restarta ogni anno,
            -- NON è univoca su solo id_legge (es. LC2022_1 vs LC2013_1).
            -- Dedup solo su URI evita che una costituzionale sovrascriva un'altra.
            PARTITION BY normalize_string(leg)
            ORDER BY
                -- priorità: costituzionale > data più recente
                CASE WHEN UPPER(COALESCE(normalize_string(tipo), '')) = 'COSTITUZIONALE' THEN 0 ELSE 1 END,
                TRY_CAST(
                    substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
                    substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
                    substr(CAST(data AS VARCHAR), 7, 2)
                    AS DATE
                ) DESC
        )                                                                   AS _rn
    FROM raw_norm
)
SELECT
    legge_camera, id_legge, titolo, tipo, data_promulgazione,
    legislatura, anno, urn_normattiva, gu_pubblicazione, ddl_numero,
    atto_camera, natura_atto, legge_key_full, legge_key_year
FROM raw_dedup
WHERE _rn = 1
