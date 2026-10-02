-- mart_costituzionali.sql — camera_leggi
-- Copertura del ponte DDL↔Normattiva sulle sole leggi costituzionali.

SELECT
    COUNT(*) AS n_costituzionali,
    COUNT(CASE WHEN urn_normattiva IS NOT NULL THEN 1 END) AS con_urn,
    COUNT(CASE WHEN atto_camera IS NOT NULL THEN 1 END) AS con_atto,
    COUNT(CASE WHEN natura_atto IS NOT NULL THEN 1 END) AS con_natura_atto,
    COUNT(CASE WHEN legge_key_full IS NOT NULL THEN 1 END) AS con_key_full,
    COUNT(CASE WHEN legge_key_year IS NOT NULL THEN 1 END) AS con_key_year,
    MIN(data_promulgazione) AS prima_costituzionale,
    MAX(data_promulgazione) AS ultima_costituzionale
FROM clean_input
WHERE UPPER(COALESCE(tipo, '')) = 'COSTITUZIONALE'
   OR urn_normattiva LIKE '%legge.costituzionale%'
