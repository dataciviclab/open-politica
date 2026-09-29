-- mart_per_senatore.sql — atti per senatore
SELECT
    senatore_id,
    presentatore,
    count(DISTINCT atto_id) AS n_atti,
    count(DISTINCT tipo_categoria) AS n_tipi,
    min(data_presentazione) AS primo_atto,
    max(data_presentazione) AS ultimo_atto
FROM clean_input
WHERE senatore_id IS NOT NULL
GROUP BY senatore_id, presentatore
ORDER BY n_atti DESC
