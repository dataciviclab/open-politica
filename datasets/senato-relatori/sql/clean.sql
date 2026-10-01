-- clean.sql — senato_relatori
--
-- Ddl → relatore (bnode) → senatore URI. Default graph dati.senato.it.
-- ddl_id = osr:idDdl (contratto senato-ddl) — NON il numero URI /ddl/N
-- (es. /ddl/12537 → idDdl=11380). Vedi senato-firmatari/clean.sql.
-- Dedup: bnode multipli per stesso (ddl_id, label).

WITH src AS (
    SELECT DISTINCT
        normalize_string(d)      AS ddl_uri,
        normalize_string(idDdl)  AS id_ddl_raw,
        normalize_string(rel)    AS relatore_uri,
        normalize_string(sen)    AS senatore_uri,
        normalize_string(label)  AS relatore_label,
        normalize_string(organo) AS organo,
        normalize_string(tipo)   AS tipo_relatore
    FROM raw_input
    WHERE d IS NOT NULL AND d <> ''
),

parsed AS (
    SELECT
        TRY_CAST(id_ddl_raw AS BIGINT) AS ddl_id,
        regexp_extract(ddl_uri, 'ddl/(\d+)', 1) AS ddl_uri_num,
        TRY_CAST(
            regexp_extract(senatore_uri, 'senatore/(\d+)', 1) AS BIGINT
        ) AS senatore_id,
        relatore_uri,
        relatore_label,
        organo,
        tipo_relatore,
        ddl_uri,
        senatore_uri
    FROM src
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY ddl_id, relatore_label
            ORDER BY
                CASE WHEN senatore_id IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN organo IS NOT NULL AND organo <> '' THEN 0 ELSE 1 END,
                senatore_id,
                relatore_uri,
                tipo_relatore
        ) AS _rn
    FROM parsed
    WHERE ddl_id IS NOT NULL
      AND (relatore_label IS NOT NULL OR senatore_id IS NOT NULL)
)

SELECT
    ddl_id,
    ddl_uri,
    ddl_uri_num,
    senatore_id,
    senatore_uri,
    relatore_uri,
    relatore_label,
    COALESCE(NULLIF(organo, ''), 'sconosciuto') AS organo,
    tipo_relatore,
    CASE WHEN senatore_id IS NOT NULL THEN true ELSE false END AS has_senatore_id
FROM dedup
WHERE _rn = 1
