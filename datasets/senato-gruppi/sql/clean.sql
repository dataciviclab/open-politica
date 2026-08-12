-- clean.sql — senato_gruppi
-- Membership dei senatori ai gruppi parlamentari (XIX leg.): una riga per
-- periodo di adesione (cambi di gruppo e cariche nel tempo).
SELECT
    TRY_CAST(regexp_extract(sen, '/senatore/(\d+)', 1) AS BIGINT)      AS senatore_id,
    TRY_CAST(regexp_extract(grp, '/gruppo/(\d+)', 1) AS BIGINT)        AS gruppo_id,
    normalize_string(max(titolo))                                       AS nome_gruppo,
    normalize_string(max(sigla))                                        AS sigla,
    normalize_string(car)                                               AS carica,
    TRY_CAST(ini AS DATE)                                               AS data_inizio,
    TRY_CAST(fin AS DATE)                                               AS data_fine,
    19                                                                  AS legislatura
FROM raw_input
GROUP BY sen, grp, car, ini, fin
