-- mart_odg_ddl — ODG per disegno di legge (ponte testuale ODG → DDL)
--
-- Il numero del DDL è estratto dal titolo dell'ODG ("P.D.L. 9/00005[-A]/..."):
-- è un link testuale, non un campo strutturato del LOD. Copre la grande
-- maggioranza degli ODG (95,1% in Leg19); per gli altri tipi resta NULL.
-- Il support camera_ddl è multi-leg: il join usa id_ddl + legislatura.
-- `matched` distingue i numeri DDL presenti in camera_ddl da quelli orfani.
WITH ddl AS (
    SELECT DISTINCT
        id_ddl,
        legislatura,
        html_unescape(titolo) AS ddl_titolo,
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
      AND ddl_numero IS NOT NULL
)

SELECT
    o.legislatura,
    o.ddl_numero                AS id_ddl,
    d.ddl_titolo,
    (d.id_ddl IS NOT NULL)      AS matched,
    d.is_dl_o_bilancio,
    count(DISTINCT o.atto_id)   AS n_odg
FROM odg o
LEFT JOIN ddl d
       ON o.ddl_numero = d.id_ddl
      AND o.legislatura = d.legislatura
GROUP BY o.legislatura, o.ddl_numero, d.id_ddl, d.ddl_titolo, d.is_dl_o_bilancio
ORDER BY n_odg DESC
