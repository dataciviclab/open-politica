-- mart_profilo.sql — scheda del parlamentare (XIX), per Camera e Senato
--
-- Porta dentro `persone` la logica di `compose/profilo-politico` (rimosso):
-- le metriche sono le stesse, ma **l'identità viene da `mart_persone`**
-- (tabella precedente nella stessa sessione) invece di essere ricostruita
-- da anagrafica + ponte.
--
-- Fonti metriche:
--   camera_voti / senato_votazioni → voti individuali
--   senato_gruppi → membership gruppo (Senato, join per data)
--   camera_voti.sigla_gruppo → gruppo al momento del voto (Camera)
--   membri_governo → ruoli di governo
--   commissioni/relatori/interventi → attività
--
-- Metriche:
--   pct_coerente  : % voti in linea con l'esito della votazione (solo Senato:
--                   l'esito non è in camera_voti → NULL per la Camera)
--   pct_col_gruppo: % voti (F/C) in linea col voto dominante del PROPRIO
--                   gruppo sulla stessa votazione (affidabilità)

WITH persone19 AS (
    SELECT * FROM mart_persone WHERE legislatura = 19
),

-- ─────────────────────────── SENATO ───────────────────────────
senato_voti AS (
    SELECT senatore_id, votazione, voto, data, esito
    FROM read_parquet('{support.senato_votazioni.path}')
),
senato_membr AS (
    SELECT senatore_id, gruppo_id, data_inizio, data_fine
    FROM read_parquet({support.senato_gruppi.outputs}, union_by_name = true)
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
-- Maggioranza del gruppo per votazione. Due scelte esplicite:
--   - niente `arg_max(voto, n)`: con i pareggi è arbitrario e due build
--     davano 16 righe diverse (misurato 2026-11-09);
--   - `ROW_NUMBER ... ORDER BY count(*) DESC, voto` + `LEAD`: il tie-break
--     è esplicito, e senza `rn = 1` l'ultima riga della partizione (con
--     `LEAD` NULL) sarebbe passata anche in caso di parità;
--   - **parità = nessuna maggioranza**: la votazione esce dalla metrica
--     invece di scegliere un lato a caso.
senato_gm AS (
    SELECT votazione, gruppo_id, voto AS voto_gruppo
    FROM (
        SELECT
            votazione, gruppo_id, voto, count(*) AS n,
            ROW_NUMBER() OVER (
                PARTITION BY votazione, gruppo_id
                ORDER BY count(*) DESC, voto
            ) AS rn,
            LEAD(count(*)) OVER (
                PARTITION BY votazione, gruppo_id
                ORDER BY count(*) DESC, voto
            ) AS n_secondo
        FROM senato_vg
        WHERE voto IN ('FAVOREVOLE', 'CONTRARIO')
        GROUP BY votazione, gruppo_id, voto
    )
    WHERE rn = 1 AND (n_secondo IS NULL OR n > n_secondo)
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
senato_interventi_agg AS (
    SELECT senatore_id, count(*) AS n_interventi
    FROM read_parquet({support.senato_interventi.outputs}, union_by_name = true)
    GROUP BY senatore_id
),
senato_comm_agg AS (
    SELECT
        senatore_id,
        count(*) FILTER (WHERE data_fine IS NULL)              AS n_commissioni_attuali,
        count(*) FILTER (
            WHERE data_fine IS NULL AND carica = 'Presidente'
        ) > 0                                                  AS presidente_commissione,
        string_agg(
            nome || ' (' || carica || ')',
            '; ' ORDER BY nome
        ) FILTER (WHERE data_fine IS NULL)                     AS commissioni_attuali
    FROM read_parquet({support.senato_commissioni.outputs}, union_by_name = true)
    GROUP BY senatore_id
),
senato_profilo AS (
    SELECT
        'senato' AS ramo,
        COALESCE(p.persona_id, p.senatore_id) AS id_parlamentare,
        p.persona_id,
        p.nome, p.cognome,
        v.n_voti, v.n_favorevoli, v.n_contrari, v.n_astenuti,
        round(100.0 * v.n_coerenti / NULLIF(v.n_voti, 0), 1) AS pct_coerente,
        round(100.0 * al.n_col_gruppo / NULLIF(al.n_voti_gruppo, 0), 1) AS pct_col_gruppo,
        COALESCE(g.n_cariche_governo, 0) AS n_cariche_governo,
        COALESCE(g.n_cariche_governo, 0) > 0 AS in_governo,
        COALESCE(c.n_commissioni_attuali, 0) AS n_commissioni_attuali,
        COALESCE(c.presidente_commissione, FALSE) AS presidente_commissione,
        c.commissioni_attuali,
        0 AS n_relatori,
        0 AS anni_relatore,
        COALESCE(i.n_interventi, 0) AS n_interventi
    FROM persone19 p
    JOIN (
        SELECT senatore_id, count(*) AS n_voti,
               count(*) FILTER (WHERE voto = 'FAVOREVOLE') AS n_favorevoli,
               count(*) FILTER (WHERE voto = 'CONTRARIO')  AS n_contrari,
               count(*) FILTER (WHERE voto = 'ASTENUTO')   AS n_astenuti,
               count(*) FILTER (WHERE coerente)            AS n_coerenti
        FROM senato_vg
        GROUP BY senatore_id
    ) v ON p.senatore_id = v.senatore_id
    LEFT JOIN senato_align al ON p.senatore_id = al.senatore_id
    LEFT JOIN (
        SELECT persona_id, count(*) AS n_cariche_governo
        FROM read_parquet('{support.membri_governo.path}')
        WHERE end_date IS NULL
        GROUP BY persona_id
    ) g ON p.persona_id = g.persona_id
    LEFT JOIN senato_comm_agg c ON p.senatore_id = c.senatore_id
    LEFT JOIN senato_interventi_agg i ON p.senatore_id = i.senatore_id
    WHERE p.ramo = 'senato'
),

-- ─────────────────────────── CAMERA ───────────────────────────
camera_esito AS (
    SELECT DISTINCT votazione, approvato
    FROM read_parquet({support.camera_votazioni_sparql.outputs}, union_by_name = true)
),
camera_voti AS (
    SELECT v.deputato_id, v.votazione, v.voto, v.sigla_gruppo,
           (e.approvato AND v.voto = 'FAVOREVOLE')
            OR (NOT e.approvato AND v.voto = 'CONTRARIO') AS coerente
    FROM read_parquet('{support.camera_voti.path}') v
    LEFT JOIN camera_esito e ON v.votazione = e.votazione
    WHERE v.voto IN ('FAVOREVOLE', 'CONTRARIO', 'ASTENUTO')
),
-- Maggioranza del gruppo per votazione (stessa regola del Senato):
-- deterministico e con la parità esclusa.
camera_gm AS (
    SELECT votazione, sigla_gruppo, voto AS voto_gruppo
    FROM (
        SELECT
            votazione, sigla_gruppo, voto, count(*) AS n,
            ROW_NUMBER() OVER (
                PARTITION BY votazione, sigla_gruppo
                ORDER BY count(*) DESC, voto
            ) AS rn,
            LEAD(count(*)) OVER (
                PARTITION BY votazione, sigla_gruppo
                ORDER BY count(*) DESC, voto
            ) AS n_secondo
        FROM camera_voti
        WHERE voto IN ('FAVOREVOLE', 'CONTRARIO')
        GROUP BY votazione, sigla_gruppo, voto
    )
    WHERE rn = 1 AND (n_secondo IS NULL OR n > n_secondo)
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
camera_comm_agg AS (
    SELECT
        deputato_id,
        count(*) FILTER (WHERE data_fine IS NULL)                 AS n_organi_ruolo,
        count(*) FILTER (
            WHERE data_fine IS NULL AND carica = 'PRESIDENTE'
        ) > 0                                                     AS presidente_organo,
        string_agg(
            nome || ' (' || carica || ')',
            '; ' ORDER BY nome
        ) FILTER (WHERE data_fine IS NULL)                        AS organi_ruoli
    FROM read_parquet({support.camera_commissioni.outputs}, union_by_name = true)
    GROUP BY deputato_id
),
camera_relatori_agg AS (
    SELECT
        deputato_id,
        count(*)                                AS n_relatori,
        count(DISTINCT year(data))              AS anni_attivi
    FROM read_parquet({support.camera_relatori.outputs}, union_by_name = true)
    GROUP BY deputato_id
),
camera_interventi_agg AS (
    SELECT deputato_id, count(*) AS n_interventi
    FROM read_parquet('{support.camera_interventi.path}')
    GROUP BY deputato_id
),
camera_profilo AS (
    SELECT
        'camera' AS ramo,
        p.persona_id AS id_parlamentare,
        p.persona_id,
        p.nome, p.cognome,
        v.n_voti, v.n_favorevoli, v.n_contrari, v.n_astenuti,
        round(100.0 * v.n_coerenti / NULLIF(v.n_voti, 0), 1) AS pct_coerente,
        round(100.0 * al.n_col_gruppo / NULLIF(al.n_voti_gruppo, 0), 1) AS pct_col_gruppo,
        COALESCE(g.n_cariche_governo, 0) AS n_cariche_governo,
        COALESCE(g.n_cariche_governo, 0) > 0 AS in_governo,
        COALESCE(c.n_organi_ruolo, 0) AS n_commissioni_attuali,
        COALESCE(c.presidente_organo, FALSE) AS presidente_commissione,
        c.organi_ruoli AS commissioni_attuali,
        COALESCE(r.n_relatori, 0) AS n_relatori,
        COALESCE(r.anni_attivi, 0) AS anni_relatore,
        COALESCE(iv.n_interventi, 0) AS n_interventi
    FROM persone19 p
    JOIN (
        SELECT deputato_id, count(*) AS n_voti,
               count(*) FILTER (WHERE voto = 'FAVOREVOLE') AS n_favorevoli,
               count(*) FILTER (WHERE voto = 'CONTRARIO')  AS n_contrari,
               count(*) FILTER (WHERE voto = 'ASTENUTO')   AS n_astenuti,
               count(*) FILTER (WHERE coerente)            AS n_coerenti
        FROM camera_voti
        GROUP BY deputato_id
    ) v ON p.persona_id = v.deputato_id
    LEFT JOIN camera_align al ON p.persona_id = al.deputato_id
    LEFT JOIN camera_comm_agg c ON p.persona_id = c.deputato_id
    LEFT JOIN camera_relatori_agg r ON p.persona_id = r.deputato_id
    LEFT JOIN camera_interventi_agg iv ON p.persona_id = iv.deputato_id
    LEFT JOIN (
        SELECT persona_id, count(*) AS n_cariche_governo
        FROM read_parquet('{support.membri_governo.path}')
        WHERE end_date IS NULL
        GROUP BY persona_id
    ) g ON p.persona_id = g.persona_id
    WHERE p.ramo = 'camera'
)

SELECT * FROM senato_profilo
UNION ALL
SELECT * FROM camera_profilo
ORDER BY pct_col_gruppo ASC NULLS LAST, n_voti DESC
