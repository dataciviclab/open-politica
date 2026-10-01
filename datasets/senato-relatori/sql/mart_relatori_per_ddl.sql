-- mart_relatori_per_ddl.sql

SELECT
    ddl_id,
    COUNT(*) AS n_relazioni,
    COUNT(DISTINCT relatore_label) AS n_relatori,
    COUNT(*) FILTER (WHERE senatore_id IS NOT NULL) AS n_con_senatore,
    COUNT(DISTINCT organo) AS n_organi,
    MIN(relatore_label) AS sample_relatore
FROM clean_input
GROUP BY ddl_id
