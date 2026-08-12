-- mart_voto_senatore — profilo di voto di ogni senatore (XIX leg.)
-- Una riga per senatore: quanti voti espressi e in quale direzione.
-- È la base per l'analisi di "coerenza" e partecipazione in aula.
SELECT
    senatore_id,
    count(*)                                            AS n_voti,
    count(*) FILTER (WHERE voto = 'FAVOREVOLE')         AS n_favorevoli,
    count(*) FILTER (WHERE voto = 'CONTRARIO')          AS n_contrari,
    count(*) FILTER (WHERE voto = 'ASTENUTO')           AS n_astenuti,
    round(
        100.0 * count(*) FILTER (WHERE voto = 'FAVOREVOLE') / NULLIF(count(*), 0), 1
    )                                                   AS pct_favorevoli,
    round(
        100.0 * count(*) FILTER (WHERE voto = 'CONTRARIO') / NULLIF(count(*), 0), 1
    )                                                   AS pct_contrari
FROM clean_input
GROUP BY senatore_id
ORDER BY n_voti DESC
