-- mart_profilo_livello — Profilo per livello di ente e carica
--
-- 1 riga = 1 livello_ente × descrizione_carica: conteggi, età media
-- (al 2026-06-01), % femmine. Include tutti e 3 i livelli
-- (comune, provincia, regione) del clean layer.
-- Serve per: come si confrontano composizione e profilo demografico
-- della classe dirigente tra comuni, province e regioni.
--
-- PK: (livello_ente, descrizione_carica)

SELECT
    livello_ente,
    descrizione_carica,
    COUNT(*) AS n_amministratori,
    COUNT(DISTINCT CASE
        WHEN livello_ente = 'comune' THEN codice_dait_completo
        WHEN livello_ente = 'provincia' THEN codice_provincia
        WHEN livello_ente = 'regione' THEN codice_regione
    END) AS n_enti,
    ROUND(AVG(DATE_DIFF('year', data_nascita, DATE '2026-06-01')), 1) AS eta_media,
    ROUND(100.0 * SUM(CASE WHEN sesso = 'F' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS quota_femmine_pct,
    ROUND(100.0 * SUM(CASE WHEN sesso = 'M' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS quota_maschi_pct
FROM clean_input
WHERE livello_ente IS NOT NULL
  AND descrizione_carica IS NOT NULL
GROUP BY livello_ente, descrizione_carica
ORDER BY livello_ente, n_amministratori DESC
