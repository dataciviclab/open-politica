-- mart_membro_organo — organi per deputato
SELECT
    deputato_id,
    count(*)                                    AS n_membership,
    count(DISTINCT organo_id)                   AS n_organi,
    count(*) FILTER (WHERE data_fine IS NULL)   AS n_attuali
FROM clean_input
GROUP BY deputato_id
ORDER BY n_organi DESC
