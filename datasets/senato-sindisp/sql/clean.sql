-- clean.sql — senato_sindisp
--
-- Sindacato ispettivo del Senato (Leg13–Leg19).
-- Input: SPARQL sindisp_join + anagrafica senato via support.
-- Una riga per iniziativa (senatore × atto) — PK (atto_id, senatore_id).
--
-- ⚠️ Support senato_anagrafica multi-leg (Pattern C): {support.*.clean}
-- è un glob multi-anno → lo stesso senatore_id in più legislature.
-- Il dedup va SOLO su anag (arg_max per senatore_id); il raw sindisp
-- resta com'è (niente GROUP BY finale, niente filtro senatore NOT NULL:
-- le legislature storiche hanno iniziative senza URI senatore).

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
    s.tipo,
    s.numero,
    s.data_presentazione,
    s.esito,
    s.url_testo,
    s.label_atto,
    s.senatore_id,
    s.presentatore,
    s.tipo_iniziativa,
    s.tipo_categoria,
    s.legislatura,
    a.nome AS nome_senatore,
    a.cognome AS cognome_senatore,
    a.data_nascita,
    a.luogo_nascita
FROM sindisp s
LEFT JOIN anag a
       ON s.senatore_id = a.senatore_id
