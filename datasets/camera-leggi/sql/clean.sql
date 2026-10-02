-- clean.sql — camera_leggi
--
-- Leggi Camera + ponte Normattiva/GU/atto.
-- Source 1: legislature 13–19 (rif_leg repubblica_{year}).
-- Source 2: costituzionali LC* globali (pre-1996 + atto/natura).
-- read.mode: all → union_by_name delle due sorgenti.
--
-- PARTIZIONE PER ANNO ({year}) — obbligatoria:
--   la source LC* è year-less e viene rilanciata a ogni run 13–19.
--   Senza filtro, ogni anno riscrive TUTTE le LC → nel union del
--   consumatore ogni LC compare 7 volte.
--   Regola:
--     · leggi con legislatura = {year} → solo in questo file
--     · costituzionali con legislatura mancante o fuori 13–19
--       → solo nell'ancora {year}=19 (una copia nel union)
--
-- PK clean: legge_camera (URI). L[C]{anno}_{n} restarta ogni anno.

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
        TRY_CAST(
            regexp_extract(normalize_string(leg), 'L[C]?\d+_(\d+)', 1) AS BIGINT
        )                                                                   AS id_legge,
        normalize_string(label)                                             AS titolo,
        normalize_string(tipo)                                              AS tipo,
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
            substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
            substr(CAST(data AS VARCHAR), 7, 2)
            AS DATE
        )                                                                   AS data_promulgazione,
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
            PARTITION BY normalize_string(leg)
            ORDER BY
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
  AND (
        -- 1) legge della legislatura di questo run
        legislatura = {year}
        -- 2) costituzionali orfane di legislatura 13–19: solo in Leg19
        OR (
            UPPER(COALESCE(tipo, '')) = 'COSTITUZIONALE'
            AND {year} = 19
            AND (legislatura IS NULL OR legislatura < 13 OR legislatura > 19)
        )
  )
