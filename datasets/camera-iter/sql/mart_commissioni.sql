-- Mart: carico commissioni — assegnazioni e pareri per organo
-- Input: clean_input
-- Output: una riga per (legislatura, organo_id)

SELECT
    legislatura,
    organo_id,
    MAX(CASE WHEN tipo_evento = 'assegnazione' THEN organo_label END) AS organo_label,
    COUNT(CASE WHEN tipo_evento = 'assegnazione' THEN 1 END)     AS n_assegnazioni,
    COUNT(CASE WHEN tipo_evento = 'richiestaParere' THEN 1 END)  AS n_pareri,
    COUNT(DISTINCT atto_id)                                      AS n_atti_toccati,
    MIN(CASE WHEN NOT data_anomala THEN data END)                AS primo_evento,
    MAX(CASE WHEN NOT data_anomala THEN data END)                AS ultimo_evento
FROM clean_input
WHERE organo_id IS NOT NULL
  AND tipo_evento IN ('assegnazione', 'richiestaParere')
GROUP BY legislatura, organo_id
ORDER BY legislatura, n_assegnazioni DESC