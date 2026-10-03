-- clean.sql — senato_interventi
-- Il senatore che parla in aula/commissione (Leg13–19): una riga per intervento,
-- con la data della seduta (osr:dataSeduta). Dedup su intervento_id.
SELECT DISTINCT
    normalize_string(int)                                                    AS intervento_id,
    TRY_CAST(regexp_extract(sen, '/senatore/(\d+)', 1) AS BIGINT)           AS senatore_id,
    TRY_CAST(data AS DATE)                                                   AS data,
    normalize_string(ogg)                                                    AS oggetto,
    {year}                                                                   AS legislatura
FROM raw_input
WHERE int IS NOT NULL
