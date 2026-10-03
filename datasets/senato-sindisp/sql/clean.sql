-- clean.sql — senato_sindisp
--
-- Sindacato ispettivo del Senato (Leg13–Leg19).
-- Input: SPARQL sindisp_join + anagrafica senato via support.
-- Una riga per iniziativa (senatore × atto) — PK (atto_id, senatore_id).
--
-- ⚠️ Support senato_anagrafica multi-leg (Pattern C): {support.*.clean}
-- diventa un glob su tutte le legislature → lo stesso senatore_id compare
-- in più file. Senza dedup, il LEFT JOIN fan-out e rompe la PK.
-- anag = UNA riga per senatore_id (priorità alla legislatura di questo run).

WITH sindisp AS (
    SELECT
        TRY_CAST(
            regexp_extract(CAST(atto AS VARCHAR), '(\d+)', 1)
        AS BIGINT)                                           AS atto_id,
        normalize_string(tipo)                                AS tipo,
        normalize_string(numero)                              AS numero,
        TRY_CAST(data AS DATE)                                AS data_presentazione,
        normalize_string(esito)                               AS esito,
        normalize_string(url)                                 AS url_testo,
        normalize_string(label)                               AS label_atto,
        TRY_CAST(
            regexp_extract(CAST(senatore AS VARCHAR), '(\d+)', 1)
        AS BIGINT)                                           AS senatore_id,
        normalize_string(presentatore)                        AS presentatore,
        normalize_string(tipoIniziativa)                      AS tipo_iniziativa,
        CASE
            WHEN tipo ILIKE '%interrogazione%' THEN 'Interrogazione'
            WHEN tipo ILIKE '%interpellanza%'  THEN 'Interpellanza'
            WHEN tipo ILIKE '%mozione%'        THEN 'Mozione'
            ELSE normalize_string(tipo)
        END                                                  AS tipo_categoria,
        {year}                                               AS legislatura
    FROM raw_input
    WHERE atto IS NOT NULL
      AND senatore IS NOT NULL
),
anag AS (
    SELECT
        senatore_id,
        arg_max(nome,          legislatura) AS nome,
        arg_max(cognome,       legislatura) AS cognome,
        arg_max(data_nascita,  legislatura) AS data_nascita,
        arg_max(luogo_nascita, legislatura) AS luogo_nascita
    FROM read_parquet('{support.senato_anagrafica.clean}')
    WHERE senatore_id IS NOT NULL
    GROUP BY senatore_id
)
SELECT
    s.atto_id,
    MAX(s.tipo)                 AS tipo,
    MAX(s.numero)               AS numero,
    MAX(s.data_presentazione)   AS data_presentazione,
    MAX(s.esito)                AS esito,
    MAX(s.url_testo)            AS url_testo,
    MAX(s.label_atto)           AS label_atto,
    s.senatore_id,
    MAX(s.presentatore)         AS presentatore,
    MAX(s.tipo_iniziativa)      AS tipo_iniziativa,
    MAX(s.tipo_categoria)       AS tipo_categoria,
    MAX(s.legislatura)          AS legislatura,
    MAX(a.nome)                 AS nome_senatore,
    MAX(a.cognome)              AS cognome_senatore,
    MAX(a.data_nascita)         AS data_nascita,
    MAX(a.luogo_nascita)        AS luogo_nascita
FROM sindisp s
LEFT JOIN anag a
       ON s.senatore_id = a.senatore_id
GROUP BY s.atto_id, s.senatore_id
