-- clean.sql — camera_firmatari
--
-- URI: attocamera.rdf/ac{leg}_{id} · deputato.rdf/d{id}_{leg}
-- Chiave atto: atto_id (numero) + legislatura + atto_id_leg = '{leg}_{id}'
--   I numeri restartano per legislatura: la join a camera_ddl deve usare
--   (atto_id, legislatura) o atto_id_leg, non atto_id solo.
-- Dedup obbligatorio: OFFSET non deterministico + UNION può duplicare.

WITH src AS (
    SELECT DISTINCT
        normalize_string(atto)  AS atto_uri,
        normalize_string(dep)   AS deputato_uri,
        normalize_string(label) AS deputato_label,
        normalize_string(ruolo) AS ruolo
    FROM raw_input
    WHERE atto IS NOT NULL AND atto <> ''
      AND dep IS NOT NULL AND dep <> ''
),

parsed AS (
    SELECT
        regexp_extract(atto_uri, 'ac\d+_(\d+)', 1) AS atto_id,
        TRY_CAST(
            regexp_extract(atto_uri, 'ac(\d+)_', 1) AS INTEGER
        ) AS legislatura,
        regexp_extract(deputato_uri, 'd(\d+)_', 1) AS persona_id,
        deputato_uri,
        deputato_label,
        ruolo,
        atto_uri
    FROM src
),

qualified AS (
    SELECT
        *,
        CASE
            WHEN legislatura IS NOT NULL AND atto_id IS NOT NULL
                THEN CAST(legislatura AS VARCHAR) || '_' || atto_id
            ELSE atto_id
        END AS atto_id_leg
    FROM parsed
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY atto_id_leg, deputato_uri, ruolo
            ORDER BY deputato_uri, atto_uri
        ) AS _rn
    FROM qualified
    WHERE atto_id IS NOT NULL AND atto_id <> ''
)

SELECT
    atto_id,
    atto_uri,
    legislatura,
    atto_id_leg,
    deputato_uri,
    TRY_CAST(persona_id AS BIGINT) AS persona_id,
    deputato_label,
    ruolo
FROM dedup
WHERE _rn = 1
