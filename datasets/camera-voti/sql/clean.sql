-- clean.sql — camera_voti
-- Voti individuali dei Deputati (XIX leg.), da ocd:voto via SPARQL.
-- Una riga = stato di voto di un deputato su una votazione.
-- Gli stati includono anche i non-voti (partecipazione).
SELECT
    deputato_id,
    votazione,
    CASE
        WHEN voto = 'Favorevole'   THEN 'FAVOREVOLE'
        WHEN voto = 'Contrario'    THEN 'CONTRARIO'
        WHEN voto = 'Astensione'   THEN 'ASTENUTO'
        WHEN voto = 'Non ha votato' THEN 'NON_HA_VOTATO'
        WHEN voto = 'Ha votato'    THEN 'HA_VOTATO'
        WHEN voto = 'In missione'  THEN 'IN_MISSIONE'
        ELSE normalize_string(voto)
    END                                                         AS voto,
    normalize_string(sigla)                                     AS sigla_gruppo,
    gruppo,
    TRY_CAST(data AS DATE)                                      AS data
FROM raw_input
