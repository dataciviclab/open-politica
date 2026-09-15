-- mart_normattiva.sql — camera_leggi
-- Copertura ponte Normattiva: quante leggi hanno URN

SELECT
    COUNT(CASE WHEN urn_normattiva IS NOT NULL THEN 1 END) AS con_urn,
    COUNT(CASE WHEN urn_normattiva IS NULL THEN 1 END) AS senza_urn
FROM clean_input
