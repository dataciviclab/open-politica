-- clean.sql — senato_gruppi
-- Membership dei senatori ai gruppi parlamentari (Leg13–19, graph composizione/{year}).
-- Una riga per periodo di adesione (cambi di gruppo e cariche nel tempo).
-- PK (senatore_id, gruppo_id, data_inizio): max(carica) evita doppioni quando
-- la stessa adesione espone più cariche/sotto-triple sullo stesso periodo.
SELECT
    TRY_CAST(regexp_extract(sen, '/senatore/(\d+)', 1) AS BIGINT)      AS senatore_id,
    TRY_CAST(regexp_extract(grp, '/gruppo/(\d+)', 1) AS BIGINT)        AS gruppo_id,
    normalize_string(max(titolo))                                       AS nome_gruppo,
    normalize_string(max(sigla))                                        AS sigla,
    normalize_string(max(car))                                          AS carica,
    TRY_CAST(max(ini) AS DATE)                                          AS data_inizio,
    TRY_CAST(max(fin) AS DATE)                                          AS data_fine,
    {year}                                                              AS legislatura
FROM raw_input
GROUP BY sen, grp, ini, fin
