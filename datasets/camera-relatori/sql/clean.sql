-- clean.sql — camera_relatori
-- Il deputato relatore di un atto (il "regista politico" che segue e dirige
-- la legge in commissione). Una riga per relatore-incarico (Leg13–19).
-- read.mode: all → union_by_name di 2 sorgenti:
--   1) discussione (chi-quando: dep, data, tipo)
--   2) atto diretto ocd:atto ocd:rif_relatore (#62) → atto_camera
-- I due flussi hanno colonne diverse: si aggrega per relatore_id (max).
--
-- Chiave atto (#62): atto_camera (URI) + atto_id + atto_legislatura
--   stessa convenzione di camera_firmatari (ac{leg}_{id}).
--   Copertura parziale (~45% Leg19): gli incarichi senza atto LOD restano
--   con atto_camera NULL — dichiarato, non bloccante.

WITH u AS (
    SELECT
        normalize_string(NULLIF(rel, ''))                                   AS relatore_id,
        TRY_CAST(
            regexp_extract(normalize_string(NULLIF(dep, '')), 'deputato\.rdf/d(\d+)_', 1) AS BIGINT
        )                                                                   AS deputato_id,
        TRY_CAST(
            CASE WHEN length(CAST(data AS VARCHAR)) = 8
                 THEN substr(CAST(data AS VARCHAR),1,4)||'-'||substr(CAST(data AS VARCHAR),5,2)||'-'||substr(CAST(data AS VARCHAR),7,2)
            END AS DATE
        )                                                                   AS data,
        normalize_string(NULLIF(tipo, ''))                                  AS tipo,
        normalize_string(NULLIF(atto, ''))                                  AS atto_camera
    FROM raw_input
    WHERE rel IS NOT NULL AND rel <> ''
),

per_rel AS (
    SELECT
        relatore_id,
        max(deputato_id)                                                    AS deputato_id,
        max(data)                                                           AS data,
        max(tipo)                                                           AS tipo,
        max(atto_camera)                                                    AS atto_camera,
        {year}                                                              AS legislatura
    FROM u
    GROUP BY relatore_id
)

SELECT
    relatore_id,
    deputato_id,
    data,
    tipo,
    legislatura,
    atto_camera,
    -- stessa chiave di camera_firmatari: ac{leg}_{id}
    TRY_CAST(
        regexp_extract(atto_camera, 'attocamera\.rdf/ac\d+_(\d+)', 1) AS BIGINT
    )                                                                       AS atto_id,
    TRY_CAST(
        regexp_extract(atto_camera, 'attocamera\.rdf/ac(\d+)_', 1) AS BIGINT
    )                                                                       AS atto_legislatura,
    CASE
        WHEN atto_camera IS NOT NULL
            THEN regexp_extract(atto_camera, 'ac(\d+)_(\d+)', 1)
                 || '_' || regexp_extract(atto_camera, 'ac(\d+)_(\d+)', 2)
        ELSE NULL
    END                                                                     AS atto_id_leg
FROM per_rel
WHERE relatore_id IS NOT NULL
  AND deputato_id IS NOT NULL
