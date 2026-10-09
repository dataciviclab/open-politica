-- mart_profilo_anno — Profilo per anno × carica, 1986–2025
--
-- 1 riga = 1 anno × descrizione_carica: conteggi, età media (al 31/12
-- dell'anno di snapshot), % femmine.
-- Serve per: come è cambiata la composizione per carica nel tempo —
-- sindaci più giovani? più donne tra gli assessori? quanti commissari?
--
-- PK: (anno_snapshot, descrizione_carica)

SELECT
    anno_snapshot,
    descrizione_carica,
    COUNT(*) AS n_amministratori,
    ROUND(AVG(DATE_DIFF('year', data_nascita, MAKE_DATE(anno_snapshot, 12, 31))), 1)
                                                          AS eta_media,
    ROUND(100.0 * SUM(CASE WHEN sesso = 'F' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)
                                                          AS quota_femmine_pct,
    ROUND(100.0 * SUM(CASE WHEN sesso = 'M' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)
                                                          AS quota_maschi_pct
FROM clean_input
WHERE descrizione_carica IS NOT NULL
GROUP BY anno_snapshot, descrizione_carica
ORDER BY anno_snapshot, n_amministratori DESC
