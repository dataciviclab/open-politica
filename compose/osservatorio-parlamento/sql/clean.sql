-- clean.sql — osservatorio_parlamento
--
-- KPI istituzionali del Parlamento in formato lungo (periodo × dimensione
-- × kpi × valore), per rispondere a "il Parlamento funziona?".
-- Dimensione: produione, votazioni, fiducia, partecipazione, rappresentanza,
-- gruppi. Periodo: per anno (2022-2026) o per legislatura (XIX / tutte).

WITH

ddl AS (
    SELECT * FROM read_parquet('{support.senato_ddl.clean}')
),
cam_vot AS (
    SELECT * FROM read_parquet('{root_posix}/data/clean/camera_votazioni_sparql/*/*_clean.parquet')
),
cam_voti AS (
    SELECT * FROM read_parquet('{support.camera_voti.clean}')
),
sen_vot AS (
    SELECT * FROM read_parquet('{support.senato_votazioni.clean}')
),
gruppi AS (
    SELECT * FROM read_parquet('{support.senato_gruppi.clean}')
),
deputati AS (
    SELECT * FROM read_parquet('{support.camera_deputati.clean}')
),
dl AS (
    SELECT * FROM read_parquet('{support.decreti_legge.clean}')
),

kpi AS (
    -- ── A. Produzione legislativa (Senato, XIX leg.) ──────────────
    SELECT 'repubblica_19' AS periodo, 'produzione' AS dimensione,
           'ddl_presentati' AS kpi, CAST(count(*) AS DOUBLE) AS valore, 'senato_ddl' AS fonte
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'ddl_approvati',
           CAST(count(*) FILTER (WHERE numero_legge IS NOT NULL) AS DOUBLE), 'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'pct_conversione',
           round(100.0 * count(*) FILTER (WHERE numero_legge IS NOT NULL)
                 / NULLIF(count(*), 0), 1), 'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'pct_iniziativa_governativa',
           round(100.0 * count(*) FILTER (
               WHERE descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%'
           ) / NULLIF(count(*), 0), 1), 'senato_ddl'
    FROM ddl
    UNION ALL
    -- quota governativa tra le leggi APPROVATE: il "decide o ratifica"
    SELECT 'repubblica_19', 'produzione', 'pct_approvati_governativi',
           round(100.0 * count(*) FILTER (
               WHERE numero_legge IS NOT NULL
                 AND (descr_iniziativa LIKE 'Gov%' OR iniziativa LIKE '%Gov%')
           ) / NULLIF(count(*) FILTER (WHERE numero_legge IS NOT NULL), 0), 1),
           'senato_ddl'
    FROM ddl
    UNION ALL
    SELECT 'repubblica_19', 'produzione', 'giorni_iter_medio',
           round(avg(date_diff('day', data_presentazione, data_legge)), 1), 'senato_ddl'
    FROM ddl
    WHERE numero_legge IS NOT NULL

    -- ── B. Votazioni e fiducia Camera (per anno) ──────────────────
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
           CAST(count(*) FILTER (WHERE richiesta_fiducia) AS DOUBLE), 'camera_votazioni'
    FROM cam_vot GROUP BY year(data)

    -- ── C. Votazioni Senato (per anno) ────────────────────────────
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'n_votazioni',
           CAST(count(DISTINCT votazione) AS DOUBLE), 'senato_votazioni'
    FROM sen_vot GROUP BY year(data)
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'votazioni', 'pct_approvate',
           round(100.0 * count(DISTINCT CASE WHEN esito = 'approvato' THEN votazione END)
                 / NULLIF(count(DISTINCT votazione), 0), 1), 'senato_votazioni'
    FROM sen_vot GROUP BY year(data)

    -- ── D. Partecipazione Camera (per anno) ───────────────────────
    UNION ALL
    SELECT CAST(year(data) AS VARCHAR), 'partecipazione', 'pct_voti_espressi',
           round(100.0 * count(*) FILTER (WHERE voto IN ('FAVOREVOLE', 'CONTRARIO', 'ASTENUTO'))
                 / NULLIF(count(*), 0), 1), 'camera_voti'
    FROM cam_voti GROUP BY year(data)

    -- ── E. Rappresentanza Camera (per legislatura, tutte) ─────────
    -- periodo = valore legislatura completo (repubblica_19, regno_01,
    -- costituente): NO regexp che collasserebbe regno/repubblica
    UNION ALL
    SELECT legislatura, 'rappresentanza', 'n_deputati',
           CAST(count(*) AS DOUBLE), 'camera_deputati'
    FROM deputati GROUP BY legislatura
    UNION ALL
    SELECT legislatura, 'rappresentanza', 'pct_donne',
           round(100.0 * count(*) FILTER (WHERE gender = 'female') / NULLIF(count(*), 0), 1),
           'camera_deputati'
    FROM deputati GROUP BY legislatura

    -- ── F. Cambi di gruppo (Senato, XIX leg.) ─────────────────────
    UNION ALL
    SELECT 'repubblica_19', 'gruppi', 'senatori_con_cambi',
           CAST(count(*) FILTER (WHERE n_membership > 1) AS DOUBLE), 'senato_gruppi'
    FROM (SELECT senatore_id, count(*) AS n_membership FROM gruppi GROUP BY senatore_id)
    UNION ALL
    SELECT 'repubblica_19', 'gruppi', 'n_membership',
           CAST(count(*) AS DOUBLE), 'senato_gruppi'
    FROM gruppi

    -- ── G. Decreti-legge (da decreti_legge, dedupato per DL) ──────
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl',
           CAST(count(*) AS DOUBLE), 'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl_convertiti',
           CAST(count(*) FILTER (WHERE esito = 'convertito') AS DOUBLE), 'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'n_dl_decaduti',
           CAST(count(*) FILTER (WHERE esito = 'decaduto') AS DOUBLE), 'decreti_legge'
    FROM dl
    UNION ALL
    SELECT 'repubblica_19', 'decreti', 'pct_dl_convertiti',
           round(100.0 * count(*) FILTER (WHERE esito = 'convertito') / NULLIF(count(*), 0), 1),
           'decreti_legge'
    FROM dl
)

SELECT periodo, dimensione, kpi, valore, fonte FROM kpi
