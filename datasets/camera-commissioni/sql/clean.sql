-- clean.sql — camera_commissioni
-- Membership dei deputati agli organi (commissioni, giunte, comitati) della
-- Camera (Leg13–19): una riga per periodo, con carica e date.
-- Le date arrivano in formato YYYYMMDD (startDate) e "YYYYMMDD-" / "YYYYMMDD-YYYYMMDD"
-- (date: solo inizio per i membri in carica, range per quelli cessati).
-- PK (deputato_id, organo_id, carica, data_inizio): max(fine) evita doppioni
-- quando la stessa membership ha più URI up/* con date di fine diverse.
SELECT
    TRY_CAST(regexp_extract(dep, 'deputato\.rdf/d(\d+)_', 1) AS BIGINT) AS deputato_id,
    regexp_extract(org, '/organo\.rdf/o(\d+_\d+)', 1)                  AS organo_id,
    normalize_string(max(nome))                                        AS nome,
    normalize_string(max(car))                                         AS carica,
    TRY_CAST(
        max(substr(CAST(inizio AS VARCHAR), 1, 4) || '-' ||
            substr(CAST(inizio AS VARCHAR), 5, 2) || '-' ||
            substr(CAST(inizio AS VARCHAR), 7, 2))
        AS DATE
    )                                                                  AS data_inizio,
    TRY_CAST(
        max(CASE WHEN length(CAST(fine AS VARCHAR)) >= 17
             THEN substr(CAST(fine AS VARCHAR), 10, 4) || '-' ||
                  substr(CAST(fine AS VARCHAR), 14, 2) || '-' ||
                  substr(CAST(fine AS VARCHAR), 16, 2)
        END) AS DATE
    )                                                                  AS data_fine,
    {year}                                                             AS legislatura
FROM raw_input
GROUP BY dep, org, car, inizio
