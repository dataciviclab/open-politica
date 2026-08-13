-- clean.sql — camera_relatori
-- Il deputato relatore di un atto (il "regista politico" che segue e dirige
-- la legge in commissione). Una riga per incarico da relatore.
SELECT
    normalize_string(rel)                                                AS relatore_id,
    TRY_CAST(regexp_extract(dep, 'deputato\.rdf/d(\d+)_', 1) AS BIGINT)  AS deputato_id,
    TRY_CAST(
        CASE WHEN length(CAST(data AS VARCHAR)) = 8
             THEN substr(CAST(data AS VARCHAR),1,4)||'-'||substr(CAST(data AS VARCHAR),5,2)||'-'||substr(CAST(data AS VARCHAR),7,2)
        END AS DATE
    )                                                                    AS data,
    normalize_string(tipo)                                               AS tipo,
    19                                                                   AS legislatura
FROM raw_input
GROUP BY rel, dep, data, tipo
