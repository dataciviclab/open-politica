-- clean.sql — camera_ddl
--
-- Iter legislativo dei disegni di legge della Camera (XIX leg.).
-- Input: SPARQL da dati.camera.it con 8 predicati per atto.
-- URI pattern: ac{LEG}_{NUM} o ac{LEG}_{NUM}-B (versione dopo navata) → estraiamo NUM come id_ddl.
-- Stato iter: etichetta testuale da ocd:statoIter/rdfs:label.
-- Dedup: un DDL può avere stati multipli e versioni multiple → teniamo la più recente.

WITH raw_dedup AS (
    SELECT
        normalize_string(atto)                                               AS atto_camera,
        TRY_CAST(
            regexp_extract(normalize_string(atto), 'ac\d+_(\d+)', 1) AS BIGINT
        )                                                                   AS id_ddl,
        normalize_string(title)                                             AS titolo,
        normalize_string(tipo)                                              AS tipo,
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
            substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
            substr(CAST(data AS VARCHAR), 7, 2)
            AS DATE
        )                                                                   AS data_presentazione,
        TRY_CAST(
            REPLACE(
                REPLACE(normalize_string(leg),
                    'http://dati.camera.it/ocd/legislatura.rdf/repubblica_', ''),
                'http://dati.camera.it/ocd/legislatura.rdf/', ''
            ) AS INTEGER
        )                                                                   AS legislatura,
        normalize_string(stato_label)                                       AS stato,
        normalize_string(primo_firm)                                        AS primo_firmatario,
        TRY_CAST(
            substr(CAST(data AS VARCHAR), 1, 4) AS INTEGER
        )                                                                   AS anno,
        -- Dedup: tieni la versione più recente per ogni id_ddl
        ROW_NUMBER() OVER (
            PARTITION BY
                TRY_CAST(regexp_extract(normalize_string(atto), 'ac\d+_(\d+)', 1) AS BIGINT)
            ORDER BY
                TRY_CAST(
                    substr(CAST(data AS VARCHAR), 1, 4) || '-' ||
                    substr(CAST(data AS VARCHAR), 5, 2) || '-' ||
                    substr(CAST(data AS VARCHAR), 7, 2)
                    AS DATE
                ) DESC,
                -- Preferisci versione con suffisso -B (dopo navata)
                CASE WHEN atto LIKE '%-B' THEN 1 ELSE 0 END DESC
        )                                                                   AS _rn
    FROM raw_input
    WHERE tipo = 'Progetto di Legge'
)
SELECT
    atto_camera, id_ddl, titolo, tipo, data_presentazione,
    legislatura, stato, primo_firmatario, anno
FROM raw_dedup
WHERE _rn = 1
