-- mart_relatori_per_senatore.sql

SELECT
    senatore_id,
    COUNT(*) AS n_relazioni,
    COUNT(DISTINCT ddl_id) AS n_ddl,
    MIN(relatore_label) AS sample_label
FROM clean_input
WHERE senatore_id IS NOT NULL
GROUP BY senatore_id
