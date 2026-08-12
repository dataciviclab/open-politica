-- clean.sql — profilo_politico
--
-- Scheda viva del parlamentare (XIX leg.), per CAMERA e SENATO, unificata
-- con dimensione `ramo`. Fonti (clean locali):
--   camera_voti / senato_votazioni → voti individuali
--   camera_deputati / senato_anagrafica → nome/cognome
--   senato_gruppi → membership gruppo (Senato, join per data)
--   camera_voti.sigla_gruppo       → gruppo al momento del voto (Camera)
--   ponte_persona → persona_id (identità unica per i senatori)
--   membri_governo → ruoli di governo
--
-- Metriche:
--   pct_coerente  : % voti in linea con l'esito della votazione (solo
--                   Senato: l'esito non è in camera_voti → NULL per la Camera)
--   pct_col_gruppo: % voti (F/C) in linea col voto dominante del PROPRIO
--                   gruppo sulla stessa votazione (affidabilità)

WITH

-- ─────────────────────────── SENATO ───────────────────────────
senato_voti AS (
    SELECT senatore_id, votazione, voto, data, esito
    FROM read_parquet('out/data/clean/senato_votazioni/2026/senato_votazioni_2026_clean.parquet')
),
senato_membr AS (
    SELECT senatore_id, gruppo_id, data_inizio, data_fine
    FROM read_parquet('out/data/clean/senato_gruppi/2026/senato_gruppi_2026_clean.parquet')
),
senato_vg AS (
    SELECT v.senatore_id, v.votazione, v.voto, g.gruppo_id,
           (v.esito = 'approvato' AND v.voto = 'FAVOREVOLE')
            OR (v.esito = 'respinto' AND v.voto = 'CONTRARIO') AS coerente
    FROM senato_voti v
    JOIN senato_membr g ON v.senatore_id = g.senatore_id
        AND v.data >= g.data_inizio
        AND (g.data_fine IS NULL OR v.data <= g.data_fine)
),
senato_gm AS (
    SELECT votazione, gruppo_id, arg_max(voto, n) AS voto_gruppo
    FROM (
        SELECT votazione, gruppo_id, voto, count(*) AS n
        FROM senato_vg
        WHERE voto IN ('FAVOREVOLE', 'CONTRARIO')
        GROUP BY votazione, gruppo_id, voto
    )
    GROUP BY votazione, gruppo_id
),
senato_align AS (
    SELECT v.senatore_id,
           count(*) AS n_voti_gruppo,
           count(*) FILTER (WHERE v.voto = g.voto_gruppo) AS n_col_gruppo
    FROM senato_vg v
    JOIN senato_gm g ON v.votazione = g.votazione AND v.gruppo_id = g.gruppo_id
    WHERE v.voto IN ('FAVOREVOLE', 'CONTRARIO')
    GROUP BY v.senatore_id
),
senato_anagrafica AS (
    SELECT DISTINCT senatore_id, nome, cognome
    FROM read_parquet('out/data/clean/senato_anagrafica/2026/senato_anagrafica_2026_clean.parquet')
),
senato_profilo AS (
    SELECT
        'senato' AS ramo,
        COALESCE(p.persona_id, a.senatore_id) AS id_parlamentare,
        p.persona_id,
        a.nome, a.cognome,
        v.n_voti, v.n_favorevoli, v.n_contrari, v.n_astenuti,
        round(100.0 * v.n_coerenti / NULLIF(v.n_voti, 0), 1) AS pct_coerente,
        round(100.0 * al.n_col_gruppo / NULLIF(al.n_voti_gruppo, 0), 1) AS pct_col_gruppo,
        COALESCE(g.n_cariche_governo, 0) AS n_cariche_governo,
        COALESCE(g.n_cariche_governo, 0) > 0 AS in_governo
    FROM senato_anagrafica a
    JOIN (
        SELECT senatore_id, count(*) AS n_voti,
               count(*) FILTER (WHERE voto = 'FAVOREVOLE') AS n_favorevoli,
               count(*) FILTER (WHERE voto = 'CONTRARIO')  AS n_contrari,
               count(*) FILTER (WHERE voto = 'ASTENUTO')   AS n_astenuti,
               count(*) FILTER (WHERE coerente)            AS n_coerenti
        FROM senato_vg
        GROUP BY senatore_id
    ) v ON a.senatore_id = v.senatore_id
    LEFT JOIN senato_align al ON a.senatore_id = al.senatore_id
    LEFT JOIN (
        SELECT senatore_id, persona_id FROM read_parquet('out/data/clean/ponte_persona/2026/ponte_persona_2026_clean.parquet')
        WHERE tipo_match = '1to1'
    ) p ON a.senatore_id = p.senatore_id
    LEFT JOIN (
        SELECT persona_id, count(*) AS n_cariche_governo
        FROM read_parquet('out/data/clean/membri_governo/2026/membri_governo_2026_clean.parquet')
        WHERE end_date IS NULL
        GROUP BY persona_id
    ) g ON p.persona_id = g.persona_id
),

-- ─────────────────────────── CAMERA ───────────────────────────
camera_voti AS (
    SELECT deputato_id, votazione, voto, sigla_gruppo
    FROM read_parquet('out/data/clean/camera_voti/2026/camera_voti_2026_clean.parquet')
    WHERE voto IN ('FAVOREVOLE', 'CONTRARIO', 'ASTENUTO')
),
-- moda del gruppo per votazione (gruppo = sigla al momento del voto)
camera_gm AS (
    SELECT votazione, sigla_gruppo, arg_max(voto, n) AS voto_gruppo
    FROM (
        SELECT votazione, sigla_gruppo, voto, count(*) AS n
        FROM camera_voti
        WHERE voto IN ('FAVOREVOLE', 'CONTRARIO')
        GROUP BY votazione, sigla_gruppo, voto
    )
    GROUP BY votazione, sigla_gruppo
),
camera_align AS (
    SELECT v.deputato_id,
           count(*) AS n_voti_gruppo,
           count(*) FILTER (WHERE v.voto = g.voto_gruppo) AS n_col_gruppo
    FROM camera_voti v
    JOIN camera_gm g ON v.votazione = g.votazione AND v.sigla_gruppo = g.sigla_gruppo
    WHERE v.voto IN ('FAVOREVOLE', 'CONTRARIO')
    GROUP BY v.deputato_id
),
camera_anagrafica AS (
    SELECT DISTINCT persona_id, nome, cognome
    FROM read_parquet('out/data/clean/camera_deputati_legislature/2026/camera_deputati_legislature_2026_clean.parquet')
),
camera_profilo AS (
    SELECT
        'camera' AS ramo,
        a.persona_id AS id_parlamentare,
        a.persona_id,
        a.nome, a.cognome,
        v.n_voti, v.n_favorevoli, v.n_contrari, v.n_astenuti,
        NULL AS pct_coerente,
        round(100.0 * al.n_col_gruppo / NULLIF(al.n_voti_gruppo, 0), 1) AS pct_col_gruppo,
        COALESCE(g.n_cariche_governo, 0) AS n_cariche_governo,
        COALESCE(g.n_cariche_governo, 0) > 0 AS in_governo
    FROM camera_anagrafica a
    JOIN (
        SELECT deputato_id, count(*) AS n_voti,
               count(*) FILTER (WHERE voto = 'FAVOREVOLE') AS n_favorevoli,
               count(*) FILTER (WHERE voto = 'CONTRARIO')  AS n_contrari,
               count(*) FILTER (WHERE voto = 'ASTENUTO')   AS n_astenuti
        FROM camera_voti
        GROUP BY deputato_id
    ) v ON a.persona_id = v.deputato_id
    LEFT JOIN camera_align al ON a.persona_id = al.deputato_id
    LEFT JOIN (
        SELECT persona_id, count(*) AS n_cariche_governo
        FROM read_parquet('out/data/clean/membri_governo/2026/membri_governo_2026_clean.parquet')
        WHERE end_date IS NULL
        GROUP BY persona_id
    ) g ON a.persona_id = g.persona_id
)

SELECT * FROM senato_profilo
UNION ALL
SELECT * FROM camera_profilo
