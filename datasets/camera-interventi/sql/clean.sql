-- clean.sql — camera_interventi
-- Il deputato che parla in aula/commissione: una riga per intervento,
-- con la data della discussione (dc:date). Dedup su intervento_id
-- (la paginazione OFFSET può produrre overlap).
SELECT DISTINCT
    normalize_string(int)                                                    AS intervento_id,
    TRY_CAST(regexp_extract(dep, 'deputato\.rdf/d(\d+)_', 1) AS BIGINT) AS deputato_id,
    TRY_CAST(
        CASE WHEN length(CAST(data AS VARCHAR)) = 8
             THEN substr(CAST(data AS VARCHAR),1,4)||'-'||substr(CAST(data AS VARCHAR),5,2)||'-'||substr(CAST(data AS VARCHAR),7,2)
        END AS DATE
    )                                                                    AS data,
    normalize_string(titolo)                                             AS titolo,
    19                                                                   AS legislatura
FROM raw_input
WHERE int IS NOT NULL
