-- Clean: eventi iter Camera (Leg16-19)
-- Input: raw_input (parquet prodotto da preprocess.py)
-- Output: una riga per evento (evento_id)
-- Note:
--   * Leg16 ha collegamento all'atto quasi assente per assegnazioni/stati:
--     atto_id è NULL e la legislatura viene dall'URI.
--   * richiestaParere non ha organo_id nel LOD: viene ricavato per label
--     dalla mappa (legislatura, label normalizzata) delle assegnazioni.

WITH typed AS (
    SELECT
        normalize_string(CAST(evento_id AS VARCHAR))     AS evento_id,
        normalize_string(CAST(evento_uri AS VARCHAR))    AS evento_uri,
        normalize_string(CAST(tipo_evento AS VARCHAR))   AS tipo_evento,
        CAST(legislatura AS INTEGER)                     AS legislatura,
        TRY_CAST(atto_id AS BIGINT)                      AS atto_id,
        normalize_string(CAST(atto_source AS VARCHAR))   AS atto_source,
        TRY_CAST(data AS DATE)                           AS data,
        COALESCE(TRY_CAST(data_anomala AS BOOLEAN), FALSE) AS data_anomala,
        normalize_string(CAST(organo_id AS VARCHAR))     AS organo_id,
        normalize_string(CAST(organo_label AS VARCHAR))  AS organo_label,
        normalize_string(CAST(sede AS VARCHAR))          AS sede,
        normalize_string(CAST(esito AS VARCHAR))         AS esito,
        normalize_string(CAST(target_uri AS VARCHAR))    AS target_uri,
        normalize_string(CAST(provenienza AS VARCHAR))   AS provenienza,
        normalize_string(CAST(senato_atto_num AS VARCHAR)) AS senato_atto_num,
        normalize_string(CAST(identifier AS VARCHAR))    AS identifier
    FROM raw_input
),
dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY evento_id
            ORDER BY data DESC NULLS LAST, atto_id DESC NULLS LAST, evento_uri
        ) AS rn
    FROM typed
),
organo_norm AS (
    SELECT
        legislatura,
        organo_id,
        regexp_replace(
            replace(
                upper(trim(translate(
                    replace(organo_label, '(', ' ('),
                    'àèéìòùÀÈÉÌÒÙ', 'aeeiouAEEIOU'))),
                '''', ''),
            ' +', ' ', 'g'
        ) AS label_key,
        organo_label
    FROM dedup
    WHERE rn = 1
      AND tipo_evento = 'assegnazione'
      AND organo_id IS NOT NULL
      AND organo_label IS NOT NULL
),
organo_map AS (
    SELECT legislatura, label_key, MIN(organo_id) AS organo_id
    FROM organo_norm
    GROUP BY legislatura, label_key
),
resolved AS (
    SELECT
        d.*,
        regexp_replace(
            replace(
                upper(trim(translate(
                    replace(d.organo_label, '(', ' ('),
                    'àèéìòùÀÈÉÌÒÙ', 'aeeiouAEEIOU'))),
                '''', ''),
            ' +', ' ', 'g'
        ) AS label_key
    FROM dedup d
    WHERE d.rn = 1
)
SELECT
    r.evento_id,
    r.evento_uri,
    r.tipo_evento,
    r.legislatura,
    r.atto_id,
    r.atto_source,
    r.data,
    r.data_anomala,
    CASE
        WHEN r.organo_id IS NOT NULL THEN r.organo_id
        WHEN r.tipo_evento = 'richiestaParere' THEN m.organo_id
        ELSE NULL
    END                         AS organo_id,
    r.organo_label,
    r.sede,
    r.esito,
    r.target_uri,
    r.provenienza,
    r.senato_atto_num,
    r.identifier
FROM resolved r
LEFT JOIN organo_map m
  ON r.legislatura = m.legislatura
 AND r.label_key = m.label_key
 AND r.tipo_evento = 'richiestaParere'