-- clean.sql — camera_atti_dibattito
--
-- URI: attocamera.rdf/ac{leg}_{id} · dibattito.rdf/dib{id}_{leg} · abbinamenti vari
-- Dedup obbligatorio: UNION + OFFSET non deterministico.

WITH src AS (
    SELECT DISTINCT
        normalize_string(atto) AS atto_uri,
        normalize_string(dib)  AS target_uri,
        normalize_string(ruolo) AS ruolo
    FROM raw_input
    WHERE atto IS NOT NULL AND atto <> ''
      AND dib IS NOT NULL AND dib <> ''
),

parsed AS (
    SELECT
        regexp_extract(atto_uri, 'ac\d+_(\d+)', 1) AS atto_id,
        TRY_CAST(
            regexp_extract(atto_uri, 'ac(\d+)_', 1) AS INTEGER
        ) AS legislatura,
        target_uri,
        ruolo,
        atto_uri
    FROM src
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY atto_id, target_uri, ruolo
            ORDER BY target_uri, ruolo
        ) AS _rn
    FROM parsed
    WHERE atto_id IS NOT NULL AND atto_id <> ''
)

SELECT
    atto_id,
    atto_uri,
    legislatura,
    target_uri,
    ruolo
FROM dedup
WHERE _rn = 1
