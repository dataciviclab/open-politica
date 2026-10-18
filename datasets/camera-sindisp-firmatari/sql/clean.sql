-- clean.sql — camera_sindisp_firmatari
--
-- URI firmatario: deputato.rdf/d{id}_{leg}; per atti misti può comparire
-- senatore.rdf/s{id}_{leg} (il dataset Camera esclude gli atti _S, ma non
-- esclude a priori un firmatario Senato su un atto Camera).
-- PK: (atto_id, firmatario_uri, ruolo).

WITH src AS (
    SELECT DISTINCT
        normalize_string(atto)  AS atto_id,
        normalize_string(firm)  AS firmatario_uri,
        normalize_string(ruolo) AS ruolo,
        normalize_string(label) AS firmatario_label
    FROM raw_input
    WHERE atto IS NOT NULL AND atto <> ''
      AND firm IS NOT NULL AND firm <> ''
),

parsed AS (
    SELECT
        atto_id,
        firmatario_uri,
        ruolo,
        firmatario_label,
        TRY_CAST(
            regexp_extract(
                firmatario_uri,
                '(?:deputato|senatore)[.]rdf/[ds](\d+)_',
                1
            ) AS BIGINT
        ) AS persona_id
    FROM src
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY atto_id, firmatario_uri, ruolo
            ORDER BY firmatario_label
        ) AS _rn
    FROM parsed
)

SELECT
    atto_id,
    firmatario_uri,
    persona_id,
    ruolo,
    firmatario_label,
    {year} AS legislatura
FROM dedup
WHERE _rn = 1
