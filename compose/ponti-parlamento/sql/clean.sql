-- clean.sql — ponti_parlamento
--
-- KPI ponti in formato lungo. Placeholder toolkit + raw_input (GCS).
-- external multi-anno: {support.*.clean} è una lista SQL di URL (no quote).

WITH

og AS (
    SELECT * FROM raw_input
),
sen_rel AS (
    SELECT * FROM read_parquet({support.senato_relatori.clean})
),
sen_ddl AS (
    SELECT * FROM read_parquet({support.senato_ddl.clean})
),
sen_vot AS (
    SELECT * FROM read_parquet({support.senato_votazioni.clean})
),
cam_firm AS (
    SELECT * FROM read_parquet({support.camera_firmatari.clean})
),
cam_dib AS (
    SELECT * FROM read_parquet({support.camera_atti_dibattito.clean})
),
cam_ddl AS (
    SELECT * FROM read_parquet({support.camera_ddl.clean})
),

voti_ddl AS (
    SELECT v.votazione_id, v.senatore_id, v.voto,
           o.ddl_id, o.esito
    FROM sen_vot v
    JOIN og o ON o.votazione_id = v.votazione_id
    WHERE o.ddl_id IS NOT NULL
),

ponti AS (
    SELECT 'voti_ddl' AS ponte, 'n_votazioni_con_oggetto' AS metrica,
           CAST(count(*) AS DOUBLE) AS valore, 'senato_votazioni_oggetto' AS fonte
    FROM og
    UNION ALL
    SELECT 'voti_ddl', 'n_votazioni_con_ddl',
           CAST(count(*) FILTER (WHERE ddl_id IS NOT NULL) AS DOUBLE),
           'senato_votazioni_oggetto'
    FROM og
    UNION ALL
    SELECT 'voti_ddl', 'pct_votazioni_con_ddl',
           round(100.0 * count(*) FILTER (WHERE ddl_id IS NOT NULL)
                 / NULLIF(count(*), 0), 1), 'senato_votazioni_oggetto'
    FROM og
    UNION ALL
    SELECT 'voti_ddl', 'ddl_raggiunti',
           CAST(count(DISTINCT ddl_id) AS DOUBLE), 'senato_votazioni_oggetto'
    FROM og WHERE ddl_id IS NOT NULL
    UNION ALL
    SELECT 'voti_ddl', 'voti_individuali_su_ddl',
           CAST(count(*) AS DOUBLE), 'senato_votazioni×oggetto'
    FROM voti_ddl
    UNION ALL
    SELECT 'voti_ddl', 'senatori_su_ddl',
           CAST(count(DISTINCT senatore_id) AS DOUBLE), 'senato_votazioni×oggetto'
    FROM voti_ddl
    UNION ALL
    SELECT 'voti_ddl', 'ddl_in_senato_ddl',
           CAST(count(DISTINCT o.ddl_id) AS DOUBLE), 'oggetto×senato_ddl'
    FROM og o
    JOIN (SELECT DISTINCT id_ddl FROM sen_ddl WHERE id_ddl IS NOT NULL) d
      ON d.id_ddl = o.ddl_id
    WHERE o.ddl_id IS NOT NULL

    UNION ALL
    SELECT 'relatori', 'n_relazioni',
           CAST(count(*) AS DOUBLE), 'senato_relatori'
    FROM sen_rel
    UNION ALL
    SELECT 'relatori', 'n_con_senatore',
           CAST(count(*) FILTER (WHERE senatore_id IS NOT NULL) AS DOUBLE),
           'senato_relatori'
    FROM sen_rel
    UNION ALL
    SELECT 'relatori', 'ddl_distinti',
           CAST(count(DISTINCT ddl_id) AS DOUBLE), 'senato_relatori'
    FROM sen_rel
    UNION ALL
    SELECT 'relatori', 'senatori_distinti',
           CAST(count(DISTINCT senatore_id) AS DOUBLE), 'senato_relatori'
    FROM sen_rel WHERE senatore_id IS NOT NULL
    UNION ALL
    SELECT 'relatori', 'ddl_con_relatore',
           CAST(count(DISTINCT r.ddl_id) AS DOUBLE), 'relatori×senato_ddl'
    FROM sen_rel r
    JOIN (SELECT DISTINCT id_ddl FROM sen_ddl WHERE id_ddl IS NOT NULL) d
      ON d.id_ddl = r.ddl_id

    UNION ALL
    SELECT 'firmatari_camera', 'n_firmature',
           CAST(count(*) AS DOUBLE), 'camera_firmatari'
    FROM cam_firm
    UNION ALL
    SELECT 'firmatari_camera', 'atti_distinti',
           CAST(count(DISTINCT f.atto_id_leg) AS DOUBLE), 'camera_firmatari'
    FROM cam_firm f
    UNION ALL
    SELECT 'firmatari_camera', 'persone_distinte',
           CAST(count(DISTINCT persona_id) AS DOUBLE), 'camera_firmatari'
    FROM cam_firm WHERE persona_id IS NOT NULL
    UNION ALL
    SELECT 'firmatari_camera', 'legislature_coperte',
           CAST(count(DISTINCT legislatura) AS DOUBLE), 'camera_firmatari'
    FROM cam_firm WHERE legislatura IS NOT NULL
    UNION ALL
    SELECT 'firmatari_camera', 'atti_in_camera_ddl',
           CAST(count(DISTINCT f.atto_id_leg) AS DOUBLE), 'firmatari×camera_ddl'
    FROM cam_firm f
    JOIN cam_ddl d
      ON d.id_ddl = TRY_CAST(f.atto_id AS BIGINT)
     AND d.legislatura = f.legislatura

    UNION ALL
    SELECT 'dibattito_camera', 'n_link',
           CAST(count(*) AS DOUBLE), 'camera_atti_dibattito'
    FROM cam_dib
    UNION ALL
    SELECT 'dibattito_camera', 'atti_distinti',
           CAST(count(DISTINCT atto_id_leg) AS DOUBLE), 'camera_atti_dibattito'
    FROM cam_dib
    UNION ALL
    SELECT 'dibattito_camera', 'link_dibattito',
           CAST(count(*) FILTER (WHERE ruolo = 'dibattito') AS DOUBLE),
           'camera_atti_dibattito'
    FROM cam_dib
    UNION ALL
    SELECT 'dibattito_camera', 'legislature_coperte',
           CAST(count(DISTINCT legislatura) AS DOUBLE), 'camera_atti_dibattito'
    FROM cam_dib WHERE legislatura IS NOT NULL
)

SELECT ponte, metrica, valore, fonte FROM ponti
