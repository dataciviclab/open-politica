-- clean.sql — camera_sindisp_destinatari
--
-- Una riga = (atto, organo di governo destinatario).
-- organo_id è l'ultimo segmento dell'URI organoGoverno (es. og182_624).
-- ha_risposta replica il flag dell'atto, per il tasso di risposta per ministro.

WITH src AS (
    SELECT DISTINCT
        normalize_string(atto)     AS atto_id,
        normalize_string(dest)     AS destinatario_uri,
        normalize_string(label)    AS destinatario_label,
        normalize_string(risposta) AS risposta_uri
    FROM raw_input
    WHERE atto IS NOT NULL AND atto <> ''
      AND dest IS NOT NULL AND dest <> ''
),

parsed AS (
    SELECT
        *,
        regexp_extract(destinatario_uri, 'organoGoverno[.]rdf/([^/]+)$', 1) AS organo_id,
        CASE
            WHEN destinatario_uri LIKE '%/organoGoverno.rdf/og'
                THEN 'GOVERNO'
            ELSE destinatario_label
        END AS destinatario_label_norm,
        (risposta_uri IS NOT NULL) AS ha_risposta
    FROM src
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY atto_id, destinatario_uri
            ORDER BY destinatario_label
        ) AS _rn
    FROM parsed
)

SELECT
    atto_id,
    destinatario_uri,
    organo_id,
    destinatario_label_norm AS destinatario_label,
    ha_risposta,
    {year} AS legislatura
FROM dedup
WHERE _rn = 1
