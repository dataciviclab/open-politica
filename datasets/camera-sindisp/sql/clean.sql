-- clean.sql — camera_sindisp
--
-- Un atto di indirizzo e controllo della Camera per riga.
-- Fonte: ocd:aic (default graph), già filtrata sul ramo Camera nella query.
-- PK: atto_id (URI completo). La legislatura arriva dal run {year}.
--
-- Dedup: il graph Virtuoso può restituire triple duplicate (es. rdf:type);
-- il raw può quindi contenere righe identiche o con label leggermente diverse.
-- Si deduplica sull'URI, scegliendo la riga più informativa.

WITH src AS (
    SELECT DISTINCT
        normalize_string(atto)         AS atto_id,
        normalize_string(tipo)         AS tipo,
        normalize_string(numero)       AS numero,
        normalize_string(data)         AS data_raw,
        normalize_string(titolo)       AS titolo,
        normalize_string(descrizione)  AS descrizione,
        normalize_string(ramo)         AS ramo_raw,
        normalize_string(primo)        AS primo_firmatario_uri,
        normalize_string(primo_label)  AS primo_firmatario_label,
        normalize_string(concluso)     AS concluso_raw,
        normalize_string(risposta)     AS risposta_uri
    FROM raw_input
    WHERE atto IS NOT NULL AND atto <> ''
),

parsed AS (
    SELECT
        *,
        -- dc:date è YYYYMMDD; alcune legislature storiche possono avere ISO.
        TRY_CAST(
            CASE
                -- Leg13 (e altre storiche) usa YYYYMMDD con suffisso "-"
                WHEN regexp_matches(data_raw, '^\d{8}')
                    THEN substr(data_raw, 1, 4) || '-'
                      || substr(data_raw, 5, 2) || '-'
                      || substr(data_raw, 7, 2)
                WHEN regexp_matches(data_raw, '^\d{4}-\d{2}-\d{2}')
                    THEN substr(data_raw, 1, 10)
                ELSE NULL
            END AS DATE
        ) AS data_presentazione,
        CASE
            WHEN tipo IS NULL THEN NULL
            WHEN tipo ILIKE 'INTERROGAZIONE A RISPOSTA SCRITTA%'       THEN 'Interrogazione scritta'
            WHEN tipo ILIKE 'INTERROGAZIONE A RISPOSTA ORALE%'         THEN 'Interrogazione orale'
            WHEN tipo ILIKE 'INTERROGAZIONE A RISPOSTA IN COMMISSIONE%' THEN 'Interrogazione in commissione'
            WHEN tipo ILIKE 'INTERPELLANZA%'                            THEN 'Interpellanza'
            WHEN tipo ILIKE 'MOZIONE%'                                  THEN 'Mozione'
            WHEN tipo ILIKE 'RISOLUZIONE%'                              THEN 'Risoluzione'
            WHEN tipo ILIKE 'ODG%' OR tipo ILIKE 'ORDINE DEL GIORNO%'   THEN 'Ordine del giorno'
            ELSE tipo
        END AS tipo_categoria,
        CASE
            WHEN concluso_raw IN ('1', 'true', 'TRUE')  THEN TRUE
            WHEN concluso_raw IN ('0', 'false', 'FALSE') THEN FALSE
            ELSE NULL
        END AS concluso,
        CASE
            WHEN ramo_raw ILIKE '%Camera%' THEN 'Camera'
            WHEN ramo_raw ILIKE '%Senato%' THEN 'Senato'
            ELSE ramo_raw
        END AS ramo,
        regexp_extract(atto_id, 'aic[.]rdf/(.*)$', 1) AS atto_key
    FROM src
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY atto_id
            ORDER BY data_presentazione DESC NULLS LAST, titolo
        ) AS _rn
    FROM parsed
)

SELECT
    atto_id,
    atto_key,
    tipo,
    tipo_categoria,
    numero,
    data_presentazione,
    titolo,
    descrizione,
    ramo,
    primo_firmatario_uri,
    primo_firmatario_label,
    concluso,
    risposta_uri,
    (risposta_uri IS NOT NULL) AS ha_risposta,
    year(data_presentazione)   AS anno,
    {year}                     AS legislatura
FROM dedup
WHERE _rn = 1
