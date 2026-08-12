-- clean.sql — senato_commissioni
-- Membership dei senatori alle commissioni (XIX leg.): una riga per periodo
-- di appartenenza, con carica (Membro/Presidente/Vicepresidente...) e date.
SELECT
    TRY_CAST(regexp_extract(sen, '/senatore/(\d+)', 1) AS BIGINT)  AS senatore_id,
    -- id commissione = suffisso completo (es. "0-7"): il primo numero da
    -- solo colliderebbe (commissioni 0-7 e 0-21 hanno entrambe prefisso 0)
    regexp_extract(comm, '/commissione/(\d+-\d+)', 1)               AS commissione_id,
    normalize_string(max(titolo))                                  AS nome,
    normalize_string(max(breve))                                   AS materia,
    normalize_string(max(cat))                                     AS categoria,
    normalize_string(car)                                          AS carica,
    TRY_CAST(ini AS DATE)                                          AS data_inizio,
    TRY_CAST(fin AS DATE)                                          AS data_fine,
    19                                                             AS legislatura
FROM raw_input
GROUP BY sen, comm, car, ini, fin
