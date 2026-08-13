-- clean.sql — senato_interventi
-- Il senatore che parla in aula/commissione: una riga per intervento,
-- con la data della seduta (osr:dataSeduta). Dedup su intervento_id.
SELECT DISTINCT
    normalize_string(int)                                                    AS intervento_id,
    TRY_CAST(regexp_extract(sen, '/senatore/(\d+)', 1) AS BIGINT)           AS senatore_id,
    TRY_CAST(data AS DATE)                                                   AS data,
    normalize_string(ogg)                                                    AS oggetto,
    19                                                                       AS legislatura
FROM raw_input
WHERE int IS NOT NULL
