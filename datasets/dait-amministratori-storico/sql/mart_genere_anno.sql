-- mart_genere_anno — Quota femminile nella classe politica comunale, 1986–2025
--
-- 1 riga = 1 anno × sesso: conteggi e quota percentuale.
-- La serie storica è lo snapshot al 31/12 di ogni anno.
-- Serve per: trend storico della presenza femminile negli enti locali —
-- la domanda chiave del dataset.
--
-- PK: (anno_snapshot, sesso)

SELECT
    anno_snapshot,
    sesso,
    COUNT(*) AS n_amministratori,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY anno_snapshot), 1)
                                                          AS quota_pct
FROM clean_input
WHERE sesso IS NOT NULL
GROUP BY anno_snapshot, sesso
ORDER BY anno_snapshot, sesso
