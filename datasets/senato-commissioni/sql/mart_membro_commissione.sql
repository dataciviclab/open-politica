-- mart_membro_commissione — quante commissioni ha (avuto) ogni senatore
SELECT
    senatore_id,
    count(*)                                                    AS n_membership,
    count(DISTINCT commissione_id)                              AS n_commissioni,
    count(*) FILTER (WHERE data_fine IS NULL)                   AS n_attuali
FROM clean_input
GROUP BY senatore_id
ORDER BY n_commissioni DESC
