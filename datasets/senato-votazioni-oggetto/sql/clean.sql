-- clean.sql — senato_votazioni_oggetto
--
-- Ponte votazione → oggetto → DDL dal default graph dati.senato.it.
-- ddl_id = osr:idDdl (numerazione interna, contratto senato-ddl).
-- NON usare il numero dell'URI /ddl/N: è una numerazione diversa
-- (es. /ddl/32478 → idDdl=29965). Vedi senato-firmatari/clean.sql.
-- Dedup obbligatorio: OFFSET senza ORDER BY è non-deterministico.

WITH src AS (
    SELECT DISTINCT
        normalize_string(v)     AS votazione_uri,
        normalize_string(og)    AS oggetto_uri,
        normalize_string(ddl)   AS ddl_uri,
        normalize_string(idDdl) AS id_ddl_raw,
        normalize_string(esito) AS esito,
        normalize_string(tipo)  AS tipo_votazione
    FROM raw_input
    WHERE v IS NOT NULL AND v <> ''
),

parsed AS (
    SELECT
        regexp_extract(votazione_uri, 'votazione/([^/]+)$', 1) AS votazione_id,
        regexp_extract(oggetto_uri, 'oggettotrattazione/(\d+)', 1) AS oggetto_id,
        -- chiave contratto: idDdl interno (NON il numero URI)
        TRY_CAST(id_ddl_raw AS BIGINT) AS ddl_id,
        regexp_extract(ddl_uri, 'ddl/(\d+)', 1) AS ddl_uri_num,
        TRY_CAST(
            regexp_extract(votazione_uri, 'votazione/(\d+)-', 1) AS INTEGER
        ) AS legislatura,
        esito,
        tipo_votazione,
        votazione_uri,
        oggetto_uri,
        ddl_uri
    FROM src
    WHERE id_ddl_raw IS NOT NULL AND id_ddl_raw <> ''
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY votazione_id
            ORDER BY
                CASE WHEN ddl_id IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN oggetto_id IS NOT NULL THEN 0 ELSE 1 END,
                ddl_id,
                oggetto_id,
                votazione_uri
        ) AS _rn
    FROM parsed
    WHERE votazione_id IS NOT NULL AND votazione_id <> ''
)

SELECT
    votazione_id,
    votazione_uri,
    oggetto_id,
    oggetto_uri,
    ddl_id,
    ddl_uri,
    ddl_uri_num,
    legislatura,
    esito,
    tipo_votazione,
    CASE WHEN ddl_id IS NOT NULL THEN true ELSE false END AS has_ddl
FROM dedup
WHERE _rn = 1
