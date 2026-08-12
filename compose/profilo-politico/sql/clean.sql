-- clean.sql — profilo_politico
--
-- Scheda viva del senatore (XIX leg.), assemblata dai clean locali di:
--   senato_votazioni  → voti individuali
--   senato_anagrafica → nome/cognome
--   senato_gruppi     → membership gruppo (per periodo)
--   ponte_persona     → persona_id Camera
--   membri_governo    → ruoli di governo
--
-- Metriche:
--   pct_coerente  : % voti in linea con l'esito della votazione
--                   (proxy allineamento al governo)
--   pct_col_gruppo: % voti (F/C) in linea col voto dominante del PROPRIO
--                   gruppo sulla stessa votazione (affidabilità, stile
--                   Openpolis). È la metrica di "vota col suo gruppo".

WITH

voti_det AS (
    SELECT senatore_id, votazione, voto, data, esito
    FROM read_parquet('out/data/clean/senato_votazioni/2026/senato_votazioni_2026_clean.parquet')
),

membr AS (
    SELECT senatore_id, gruppo_id, data_inizio, data_fine
    FROM read_parquet('out/data/clean/senato_gruppi/2026/senato_gruppi_2026_clean.parquet')
),

-- voto del senatore sul gruppo di appartenenza a quella data
vg AS (
    SELECT v.senatore_id, v.votazione, v.voto,
           g.gruppo_id,
           (v.esito = 'approvato' AND v.voto = 'FAVOREVOLE')
            OR (v.esito = 'respinto' AND v.voto = 'CONTRARIO') AS coerente
    FROM voti_det v
    JOIN membr g ON v.senatore_id = g.senatore_id
        AND v.data >= g.data_inizio
        AND (g.data_fine IS NULL OR v.data <= g.data_fine)
),

-- posizione dominante del gruppo per votazione (moda su F/C)
gm AS (
    SELECT votazione, gruppo_id, arg_max(voto, n) AS voto_gruppo
    FROM (
        SELECT votazione, gruppo_id, voto, count(*) AS n
        FROM vg
        WHERE voto IN ('FAVOREVOLE', 'CONTRARIO')
        GROUP BY votazione, gruppo_id, voto
    )
    GROUP BY votazione, gruppo_id
),

-- senatore allineato al proprio gruppo
allineato AS (
    SELECT v.senatore_id,
           count(*) AS n_voti_gruppo,
           count(*) FILTER (
               WHERE v.voto = g.voto_gruppo
           ) AS n_col_gruppo
    FROM vg v
    JOIN gm g ON v.votazione = g.votazione AND v.gruppo_id = g.gruppo_id
    WHERE v.voto IN ('FAVOREVOLE', 'CONTRARIO')
    GROUP BY v.senatore_id
),

voti AS (
    SELECT senatore_id,
        count(*)                                                              AS n_voti,
        count(*) FILTER (WHERE voto = 'FAVOREVOLE')                           AS n_favorevoli,
        count(*) FILTER (WHERE voto = 'CONTRARIO')                            AS n_contrari,
        count(*) FILTER (WHERE voto = 'ASTENUTO')                             AS n_astenuti,
        count(*) FILTER (
            WHERE (esito = 'approvato' AND voto = 'FAVOREVOLE')
               OR (esito = 'respinto'   AND voto = 'CONTRARIO')
        )                                                                     AS n_coerenti
    FROM voti_det
    GROUP BY senatore_id
),

anagrafica AS (
    SELECT DISTINCT senatore_id, nome, cognome
    FROM read_parquet('out/data/clean/senato_anagrafica/2026/senato_anagrafica_2026_clean.parquet')
),

ponte AS (
    SELECT senatore_id, persona_id
    FROM read_parquet('out/data/clean/ponte_persona/2026/ponte_persona_2026_clean.parquet')
    WHERE tipo_match = '1to1'
),

governo AS (
    SELECT persona_id, count(*) AS n_cariche_governo
    FROM read_parquet('out/data/clean/membri_governo/2026/membri_governo_2026_clean.parquet')
    WHERE end_date IS NULL
    GROUP BY persona_id
)

SELECT
    a.senatore_id,
    a.nome,
    a.cognome,
    p.persona_id,
    v.n_voti,
    v.n_favorevoli,
    v.n_contrari,
    v.n_astenuti,
    round(100.0 * v.n_coerenti / NULLIF(v.n_voti, 0), 1)                      AS pct_coerente,
    round(100.0 * al.n_col_gruppo / NULLIF(al.n_voti_gruppo, 0), 1)           AS pct_col_gruppo,
    COALESCE(g.n_cariche_governo, 0)                                          AS n_cariche_governo,
    COALESCE(g.n_cariche_governo, 0) > 0                                      AS in_governo
FROM anagrafica a
JOIN voti v ON a.senatore_id = v.senatore_id
LEFT JOIN allineato al ON a.senatore_id = al.senatore_id
LEFT JOIN ponte p ON a.senatore_id = p.senatore_id
LEFT JOIN governo g ON p.persona_id = g.persona_id
