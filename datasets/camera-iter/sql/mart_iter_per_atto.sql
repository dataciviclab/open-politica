-- Mart: iter per atto — sintesi per (legislatura, atto_id)
-- Input: clean_input
-- Output: una riga per atto con stato iniziale/finale, durata e conteggi

WITH base AS (
    SELECT
        legislatura,
        atto_id,
        MIN(CASE WHEN NOT data_anomala THEN data END)                   AS data_primo_evento,
        MAX(CASE WHEN NOT data_anomala THEN data END)                   AS data_ultimo_evento,
        COUNT(DISTINCT evento_uri)                                      AS n_eventi,
        COUNT(DISTINCT CASE WHEN tipo_evento = 'assegnazione'
                            THEN evento_uri END)                        AS n_assegnazioni,
        COUNT(DISTINCT CASE WHEN tipo_evento = 'statoIter'
                            THEN evento_uri END)                        AS n_stati,
        COUNT(DISTINCT CASE WHEN tipo_evento = 'trasmissione'
                            THEN evento_uri END)                        AS n_trasmissioni,
        COUNT(DISTINCT CASE WHEN tipo_evento = 'richiestaParere'
                            THEN evento_uri END)                        AS n_pareri
    FROM clean_input
    WHERE atto_id IS NOT NULL
    GROUP BY legislatura, atto_id
),
stati AS (
    SELECT
        legislatura,
        atto_id,
        esito,
        evento_id,
        ROW_NUMBER() OVER (PARTITION BY legislatura, atto_id
                           ORDER BY data ASC NULLS LAST, evento_id) AS rn_asc,
        ROW_NUMBER() OVER (PARTITION BY legislatura, atto_id
                           ORDER BY data DESC NULLS LAST, evento_id DESC) AS rn_desc
    FROM clean_input
    WHERE tipo_evento = 'statoIter'
      AND atto_id IS NOT NULL
      AND esito IS NOT NULL
      AND NOT data_anomala
),
stato_iniziale AS (
    SELECT legislatura, atto_id, esito AS stato_iniziale
    FROM stati WHERE rn_asc = 1
),
stato_finale AS (
    SELECT legislatura, atto_id, esito AS stato_finale
    FROM stati WHERE rn_desc = 1
)
SELECT
    b.legislatura,
    b.atto_id,
    b.data_primo_evento,
    b.data_ultimo_evento,
    si.stato_iniziale,
    sf.stato_finale,
    b.n_eventi,
    CASE
        WHEN b.data_primo_evento IS NOT NULL AND b.data_ultimo_evento IS NOT NULL
        THEN date_diff('day', b.data_primo_evento, b.data_ultimo_evento)
        ELSE NULL
    END AS durata_giorni,
    b.n_assegnazioni,
    b.n_stati,
    b.n_trasmissioni,
    b.n_pareri
FROM base b
LEFT JOIN stato_iniziale si ON b.legislatura = si.legislatura AND b.atto_id = si.atto_id
LEFT JOIN stato_finale   sf ON b.legislatura = sf.legislatura AND b.atto_id = sf.atto_id
ORDER BY b.legislatura, b.atto_id