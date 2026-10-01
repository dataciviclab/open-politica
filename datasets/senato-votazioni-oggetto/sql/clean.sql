-- clean.sql — senato_votazioni_oggetto
--
-- Ponte votazione → oggetto → DDL dal default graph dati.senato.it.
-- Dedup obbligatorio: OFFSET senza ORDER BY è non-deterministico (WAF/Virtuoso).

WITH src AS (
    SELECT DISTINCT
        normalize_string(v)   AS votazione_uri,
        normalize_string(og)  AS oggetto_uri,
        normalize_string(ddl) AS ddl_uri,
        normalize_string(esito) AS esito,
        normalize_string(tipo) AS tipo_votazione
    FROM raw_input
    WHERE v IS NOT NULL AND v <> ''
),

parsed AS (
    SELECT
        regexp_extract(votazione_uri, 'votazione/([^/]+)$', 1) AS votazione_id,
        regexp_extract(oggetto_uri, 'oggettotrattazione/(\d+)', 1) AS oggetto_id,
        regexp_extract(ddl_uri, 'ddl/(\d+)', 1) AS ddl_id,
        TRY_CAST(
            regexp_extract(votazione_uri, 'votazione/(\d+)-', 1) AS INTEGER
        ) AS legislatura,
        esito,
        tipo_votazione,
        votazione_uri,
        oggetto_uri,
        ddl_uri
    FROM src
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
    legislatura,
    esito,
    tipo_votazione,
    CASE WHEN ddl_id IS NOT NULL THEN true ELSE false END AS has_ddl
FROM dedup
WHERE _rn = 1
