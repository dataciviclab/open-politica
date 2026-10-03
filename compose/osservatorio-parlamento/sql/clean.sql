-- clean.sql — osservatorio_parlamento
--
-- KPI in formato lungo (periodo × dimensione × kpi).
-- Produzione/ddl: multi-leg da GCS (senato_ddl_multi, 13–19) — periodo = legislatura.
-- Votazioni/rappresentanza: ancora XIX (path GCS …/2026/).

WITH

ddl_multi AS (
    -- external multi-anno: lista URL SQL (no quote)
    SELECT * FROM read_parquet({support.senato_ddl_multi.clean})
),
ddl AS (
    SELECT * FROM raw_input
),
cam_vot AS (
    SELECT * FROM read_parquet({support.camera_votazioni_sparql.clean})
),
cam_voti AS (
    SELECT * FROM read_parquet({support.camera_voti.clean})
),
sen_vot AS (
    SELECT * FROM read_parquet({support.senato_votazioni.clean})
),
gruppi AS (
    SELECT * FROM read_parquet({support.senato_gruppi.clean})
),
deputati AS (
    SELECT * FROM read_parquet({support.camera_deputati.clean})
),
dl AS (
    SELECT * FROM read_parquet({support.decreti_legge.clean})
),

kpi AS (
    -- ── A. Produzione legislativa PER LEGISLATURA (multi-leg GCS) ──
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR) AS periodo,
        'produzione' AS dimensione,
        'ddl_presentati' AS kpi,
        CAST(count(*) AS DOUBLE) AS valore,
        'senato_ddl' AS fonte
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'produzione',
        'ddl_approvati',
        CAST(count(*) FILTER (WHERE numero_legge IS NOT NULL) AS DOUBLE),
        'senato_ddl'
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'produzione',
        'pct_conversione',
        round(100.0 * count(*) FILTER (WHERE numero_legge IS NOT NULL)
              / NULLIF(count(*), 0), 1),
        'senato_ddl'
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'produzione',
        'pct_iniziativa_governativa',
        round(100.0 * count(*) FILTER (
            WHERE descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%'
        ) / NULLIF(count(*), 0), 1),
        'senato_ddl'
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'produzione',
        'pct_approvati_governativi',
        round(100.0 * count(*) FILTER (
            WHERE numero_legge IS NOT NULL
              AND (descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%')
        ) / NULLIF(count(*) FILTER (WHERE numero_legge IS NOT NULL), 0), 1),
        'senato_ddl'
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'produzione',
        'giorni_iter_medio',
        round(avg(date_diff('day', data_presentazione, data_legge)), 1),
        'senato_ddl'
    FROM ddl_multi
    WHERE legislatura IS NOT NULL
      AND numero_legge IS NOT NULL
    GROUP BY legislatura

    -- ── A2. Snapshot XIX (raw leg19, backward compat) ─────────────
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'ddl_presentati_xix',
           CAST(count(*) AS DOUBLE), 'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'ddl_approvati_xix',
           CAST(count(*) FILTER (WHERE numero_legge IS NOT NULL) AS DOUBLE),
           'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'pct_conversione_xix',
           round(100.0 * count(*) FILTER (WHERE numero_legge IS NOT NULL)
                 / NULLIF(count(*), 0), 1),
           'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'pct_iniziativa_governativa_xix',
           round(100.0 * count(*) FILTER (
               WHERE descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%'
           ) / NULLIF(count(*), 0), 1),
           'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'pct_approvati_governativi_xix',
           round(100.0 * count(*) FILTER (
               WHERE numero_legge IS NOT NULL
                 AND (descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%')
           ) / NULLIF(count(*) FILTER (WHERE numero_legge IS NOT NULL), 0), 1),
           'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'giorni_iter_medio_xix',
           round(avg(date_diff('day', data_presentazione, data_legge)), 1),
           'senato_ddl'
    FROM ddl
    WHERE numero_legge IS NOT NULL

    -- ── B. Votazioni e fiducia Camera (per anno, XIX) ─────────────
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'n_votazioni',
           CAST(count(*) AS DOUBLE), 'camera_votazioni'
    FROM cam_vot GROUP BY year(data)
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'pct_approvate',
           round(100.0 * count(*) FILTER (WHERE approvato) / NULLIF(count(*), 0), 1),
           'camera_votazioni'
    FROM cam_vot GROUP BY year(data)
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'fiducia', 'n_fiducia',
           CAST(count(*) AS DOUBLE), 'camera_votazioni'
    FROM cam_vot GROUP BY year(data)

    -- ── C. Votazioni Senato (per anno, XIX) ───────────────────────
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'n_votazioni',
           CAST(count(DISTINCT votazione) AS DOUBLE), 'senato_votazioni'
    FROM sen_vot GROUP BY year(data)
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'pct_approvate',
           round(100.0 * count(DISTINCT CASE WHEN esito = 'approvato' THEN votazione END)
                 / NULLIF(count(DISTINCT votazione), 0), 1),
           'senato_votazioni'
    FROM sen_vot GROUP BY year(data)

    -- ── D. Partecipazione Camera (per anno, XIX) ──────────────────
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'partecipazione', 'pct_voti_espressi',
           round(100.0 * count(*) FILTER (WHERE voto IN ('FAVOREVOLE', 'CONTRARIO', 'ASTENUTO'))
                 / NULLIF(count(*), 0), 1),
           'camera_voti'
    FROM cam_voti GROUP BY year(data)

    -- ── E. Rappresentanza Camera (per legislatura, tutte) ─────────
    UNION ALL
    SELECT legislatura, 'rappresentanza', 'n_deputati',
           CAST(count(*) AS DOUBLE), 'camera_deputati'
    FROM deputati GROUP BY legislatura
    UNION ALL
    SELECT legislatura, 'rappresentanza', 'pct_donne',
           round(100.0 * count(*) FILTER (WHERE gender = 'female') / NULLIF(count(*), 0), 1),
           'camera_deputati'
    FROM deputati GROUP BY legislatura

    -- ── F. Gruppi Senato PER LEGISLATURA (multi-leg GCS) ──────────
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'gruppi',
        'senatori_con_cambi',
        CAST(count(*) FILTER (WHERE n_membership > 1) AS DOUBLE),
        'senato_gruppi'
    FROM (
        SELECT senatore_id, legislatura, count(*) AS n_membership
        FROM gruppi
        WHERE legislatura IS NOT NULL
        GROUP BY senatore_id, legislatura
    )
    GROUP BY legislatura
    UNION ALL
    SELECT
        'repubblica_' || CAST(legislatura AS VARCHAR),
        'gruppi',
        'n_membership',
        CAST(count(*) AS DOUBLE),
        'senato_gruppi'
    FROM gruppi
    WHERE legislatura IS NOT NULL
    GROUP BY legislatura

    -- ── G. Decreti-legge (XIX) ────────────────────────────────────
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl',
           CAST(count(*) AS DOUBLE), 'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl_convertiti',
           CAST(count(*) FILTER (WHERE esito = 'convertito') AS DOUBLE),
           'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl_decaduti',
           CAST(count(*) FILTER (WHERE esito = 'decaduto') AS DOUBLE),
           'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'pct_dl_convertiti',
           round(100.0 * count(*) FILTER (WHERE esito = 'convertito') / NULLIF(count(*), 0), 1),
           'decreti_legge'
    FROM dl
)

SELECT periodo, dimensione, kpi, valore, fonte FROM kpi
