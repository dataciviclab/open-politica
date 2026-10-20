-- mart_odg_ddl_sintesi — copertura del ponte ODG → DDL e peso di DL/bilancio
WITH ddl AS (
    SELECT DISTINCT
        id_ddl,
        legislatura,
        (
            lower(html_unescape(titolo)) LIKE '%conversione in legge%'
            OR lower(html_unescape(titolo)) LIKE '%bilancio%'
        ) AS is_dl_o_bilancio
    FROM read_parquet('{support.camera_ddl.clean}')
    WHERE id_ddl IS NOT NULL
),

odg AS (
    SELECT
        atto_id,
        legislatura,
        ddl_numero
    FROM clean_input
    WHERE tipo_categoria = 'Ordine del giorno'
)

SELECT
    o.legislatura,
    count(*)                                                    AS n_odg,
    count(*) FILTER (WHERE o.ddl_numero IS NOT NULL)            AS n_con_numero,
    count(*) FILTER (WHERE d.id_ddl IS NOT NULL)                AS n_con_match,
    round(
        100.0 * count(*) FILTER (WHERE d.id_ddl IS NOT NULL) / count(*), 2
    )                                                           AS pct_con_match,
    count(*) FILTER (WHERE d.is_dl_o_bilancio)                  AS n_dl_o_bilancio,
    round(
        100.0 * count(*) FILTER (WHERE d.is_dl_o_bilancio) / count(*), 2
    )                                                           AS pct_dl_o_bilancio
FROM odg o
LEFT JOIN ddl d
       ON o.ddl_numero = d.id_ddl
      AND o.legislatura = d.legislatura
GROUP BY o.legislatura
