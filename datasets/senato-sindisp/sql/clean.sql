-- clean.sql — senato_sindisp
--
-- Sindacato ispettivo del Senato (Leg13–Leg19).
-- Input: singola query SPARQL con JOIN Atto → Iniziativa.
-- Una riga per iniziativa (senatore × atto).
-- Atto senza iniziativa → senatore_id NULL (atto collettivo o senza firmatari).

SELECT
    TRY_CAST(
        regexp_extract(CAST(atto AS VARCHAR), '(\d+)', 1)
    AS BIGINT)                                               AS atto_id,
    normalize_string(tipo)                                    AS tipo,
    normalize_string(numero)                                  AS numero,
    TRY_CAST(data AS DATE)                                    AS data_presentazione,
    normalize_string(esito)                                   AS esito,
    normalize_string(url)                                     AS url_testo,
    normalize_string(label)                                   AS label_atto,
    -- iniziativa
    TRY_CAST(
        regexp_extract(CAST(senatore AS VARCHAR), '(\d+)', 1)
    AS BIGINT)                                               AS senatore_id,
    normalize_string(presentatore)                            AS presentatore,
    normalize_string(tipoIniziativa)                          AS tipo_iniziativa,
    -- derivati
    CASE
        WHEN tipo ILIKE '%interrogazione%' THEN 'Interrogazione'
        WHEN tipo ILIKE '%interpellanza%' THEN 'Interpellanza'
        WHEN tipo ILIKE '%mozione%' THEN 'Mozione'
        ELSE normalize_string(tipo)
    END                                                      AS tipo_categoria,
    {year}                                                   AS legislatura
FROM raw_input
