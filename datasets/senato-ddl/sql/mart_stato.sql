-- mart_stato — DDL per stato dell'iter, per legislatura
--
-- 1 riga = 1 stato × legislatura: numero di DDL DISTINTI.
-- Risponde: come si distribuisce l'iter legislativo in ogni legislature?
-- Come cambia la produttività tra legislature?
--
-- PK: (legislatura, stato)

SELECT
    legislatura,
    stato,
    count(DISTINCT id_ddl)                   AS n_ddl
FROM clean_input
WHERE stato IS NOT NULL
  AND legislatura IS NOT NULL
GROUP BY legislatura, stato
ORDER BY legislatura, n_ddl DESC
