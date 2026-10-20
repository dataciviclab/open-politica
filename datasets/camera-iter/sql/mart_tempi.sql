-- Mart: tempi dell'iter — durate tra eventi consecutivi dello stesso atto
-- Input: clean_input
-- Output: durate per tipo_evento, esito, anno

WITH ordered AS (
    SELECT
        legislatura,
        atto_id,
        tipo_evento,
        esito,
        data,
        evento_id,
        EXTRACT(YEAR FROM data) AS anno,
        LAG(data) OVER (
            PARTITION BY legislatura, atto_id
            ORDER BY data, evento_id
        ) AS prev_data,
        LAG(tipo_evento) OVER (
            PARTITION BY legislatura, atto_id
            ORDER BY data, evento_id
        ) AS prev_tipo
    FROM clean_input
    WHERE atto_id IS NOT NULL
      AND data IS NOT NULL
      AND NOT data_anomala
      AND esito IS NOT NULL
),
durations AS (
    SELECT
        tipo_evento,
        esito,
        anno,
        date_diff('day', prev_data, data) AS durata_giorni
    FROM ordered
    WHERE prev_data IS NOT NULL
      AND data >= prev_data
)
SELECT
    tipo_evento,
    esito,
    anno,
    COUNT(*)                                                   AS n_eventi,
    AVG(CAST(durata_giorni AS DOUBLE))                         AS durata_media_giorni,
    MIN(durata_giorni)                                         AS durata_min_giorni,
    MAX(durata_giorni)                                         AS durata_max_giorni,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY durata_giorni) AS durata_mediana_giorni
FROM durations
GROUP BY tipo_evento, esito, anno
ORDER BY tipo_evento, esito, anno