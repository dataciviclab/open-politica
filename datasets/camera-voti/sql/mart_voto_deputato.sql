-- mart_voto_deputato — profilo di voto di ogni deputato (XIX leg.)
SELECT
    deputato_id,
    count(*)                                            AS n_voti,
    count(*) FILTER (WHERE voto = 'FAVOREVOLE')         AS n_favorevoli,
    count(*) FILTER (WHERE voto = 'CONTRARIO')          AS n_contrari,
    count(*) FILTER (WHERE voto = 'ASTENUTO')           AS n_astenuti,
    count(*) FILTER (WHERE voto = 'NON_HA_VOTATO')      AS n_non_votati,
    count(*) FILTER (WHERE voto = 'IN_MISSIONE')        AS n_in_missione,
    round(
        100.0 * count(*) FILTER (WHERE voto = 'FAVOREVOLE') / NULLIF(count(*), 0), 1
    )                                                   AS pct_favorevoli
FROM clean_input
GROUP BY deputato_id
ORDER BY n_voti DESC
