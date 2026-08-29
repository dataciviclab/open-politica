-- Mart: voti per lista alle elezioni politiche (pre-aggregato)
-- Ogni riga: lista × anno × camera_senato
-- Fonte: mart_voti_elezioni_politiche (aggregato per comune)

SELECT
    anno,
    camera_senato,
    lista,
    descr_lista,
    SUM(tot_voti_lista) AS tot_voti_lista,
    COUNT(DISTINCT comune) AS comuni,
    ROUND(CAST(SUM(tot_voti_lista) AS DOUBLE)
        / NULLIF(SUM(SUM(tot_voti_lista)) OVER (PARTITION BY anno, camera_senato), 0)
        * 100, 2) AS pct_lista
FROM mart_voti_elezioni_politiche
GROUP BY anno, camera_senato, lista, descr_lista
ORDER BY anno, camera_senato, tot_voti_lista DESC
