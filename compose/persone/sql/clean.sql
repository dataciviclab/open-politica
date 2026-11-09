-- clean.sql — persone (dimensione persona × legislatura × ramo)
--
-- Grain: una riga per (persona_key, ramo, sistema, legislatura).
--
-- `persona_key` è la chiave stabile della persona:
--   - Camera: `persona_id` (numerico, id Camera) quando esiste;
--   - Senato: `persona_id` se il ponte Camera↔Senato la conosce, altrimenti
--     `sen:{senatore_id}`. Così lo stesso parlamentare che è stato deputato
--     e senatore ha **una** chiave e due righe (ramo diverso).
--
-- ⚠️ `persona_id` NON è lo stesso identificatore ovunque:
--   - `camera_deputati_legislature` / `camera_firmatari` / `ponte_persona`:
--     numerico Camera (`4416`);
--   - `senato_dibattito`: stringa Senato (`'p1103'`), namespace diverso che
--     qui NON viene usato come persona_id (solo `senatore_id`).
--
-- ⚠️ `camera_deputati_legislature` copre **Regno (1-30) + Costituente +
-- Repubblica (1-19)**: il numero da solo collide (`regno_19` = `repubblica_19`).
-- Qui si tiene `sistema` + `legislatura`, e il perimetro è Repubblica 13-19
-- (lo stesso delle relazioni del grafo: fuori da lì le persone sono nodi
-- isolati). Per estendere al Regno basta cambiare il filtro.
--
-- Fonti, in ordine di priorità per la stessa riga:
--   1. `senato_anagrafica` (nome, nascita) — 13-19
--   2. `senato_dibattito` (solo cognome) — copre 110 senatori assenti
--      dall'anagrafica, Leg17-19
--   3. `camera_deputati_legislature` (nome, cognome, gender) — 13-19
--   4. `camera_firmatari` (label) — persone con un atto ma senza anagrafica

WITH ponte AS (
    SELECT
        CAST(senatore_id AS BIGINT) AS senatore_id,
        CAST(persona_id AS BIGINT)  AS persona_id
    FROM read_parquet('{support.ponte_persona.path}')
    WHERE senatore_id IS NOT NULL AND persona_id IS NOT NULL
      AND tipo_match = '1to1'   -- 'ambiguo' (18 righe) non è un'identità certa
),

-- ── Senato: anagrafica ────────────────────────────────────────────────
sen_anag AS (
    SELECT
        COALESCE(CAST(p.persona_id AS VARCHAR), 'sen:' || CAST(a.senatore_id AS VARCHAR)) AS persona_key,
        'senato'                        AS ramo,
        'repubblica'                    AS sistema,
        CAST(a.legislatura AS INTEGER)  AS legislatura,
        CAST(p.persona_id AS BIGINT)    AS persona_id,
        CAST(a.senatore_id AS BIGINT)   AS senatore_id,
        CAST(NULL AS VARCHAR)           AS deputato_uri,
        normalize_string(a.nome)        AS nome,
        normalize_string(a.cognome)     AS cognome,
        CAST(NULL AS VARCHAR)           AS nome_completo,
        CAST(NULL AS VARCHAR)           AS gender,
        TRY_CAST(a.data_nascita AS DATE) AS data_nascita,
        normalize_string(a.luogo_nascita) AS luogo_nascita,
        'senato_anagrafica'             AS fonte,
        1                               AS _prio
    FROM read_parquet({support.senato_anagrafica.outputs}, union_by_name = true) a
    LEFT JOIN ponte p ON p.senatore_id = CAST(a.senatore_id AS BIGINT)
    WHERE a.senatore_id IS NOT NULL
      AND a.legislatura BETWEEN 13 AND 19
),

-- ── Senato: chi parla in aula ma non è in anagrafica ──────────────────
-- `senato_dibattito` copre Leg17-19 e ha solo `nome_oratore` (spesso il
-- cognome) e un `persona_id` Senato (`pNNN`) che non è quello Camera.
sen_dib AS (
    SELECT
        COALESCE(CAST(p.persona_id AS VARCHAR), 'sen:' || CAST(d.senatore_id AS VARCHAR)) AS persona_key,
        'senato'                        AS ramo,
        'repubblica'                    AS sistema,
        TRY_CAST(regexp_extract(d.legislatura, '(\d+)$', 1) AS INTEGER) AS legislatura,
        CAST(p.persona_id AS BIGINT)    AS persona_id,
        CAST(d.senatore_id AS BIGINT)   AS senatore_id,
        CAST(NULL AS VARCHAR)           AS deputato_uri,
        CAST(NULL AS VARCHAR)           AS nome,
        CAST(NULL AS VARCHAR)           AS cognome,
        normalize_string(d.nome_oratore) AS nome_completo,
        CAST(NULL AS VARCHAR)           AS gender,
        CAST(NULL AS DATE)              AS data_nascita,
        CAST(NULL AS VARCHAR)           AS luogo_nascita,
        'senato_dibattito'              AS fonte,
        2                               AS _prio
    FROM read_parquet('{support.senato_dibattito.path}') d
    LEFT JOIN ponte p ON p.senatore_id = CAST(d.senatore_id AS BIGINT)
    WHERE d.senatore_id IS NOT NULL
      AND NULLIF(d.legislatura, '') IS NOT NULL
),

-- ── Camera: anagrafica (solo Repubblica 13-19) ────────────────────────
-- `legislatura` è una label: 'repubblica_19', 'regno_19', 'costituente'.
cam_anag AS (
    SELECT
        CAST(c.persona_id AS VARCHAR)   AS persona_key,
        'camera'                        AS ramo,
        split_part(c.legislatura, '_', 1) AS sistema,
        TRY_CAST(regexp_extract(c.legislatura, '(\d+)$', 1) AS INTEGER) AS legislatura,
        CAST(c.persona_id AS BIGINT)    AS persona_id,
        CAST(NULL AS BIGINT)            AS senatore_id,
        normalize_string(c.deputato)    AS deputato_uri,
        normalize_string(c.nome)        AS nome,
        normalize_string(c.cognome)     AS cognome,
        CAST(NULL AS VARCHAR)           AS nome_completo,
        normalize_string(c.gender)      AS gender,
        CAST(NULL AS DATE)              AS data_nascita,
        CAST(NULL AS VARCHAR)           AS luogo_nascita,
        'camera_deputati_legislature'   AS fonte,
        3                               AS _prio
    FROM read_parquet({support.camera_deputati.outputs}, union_by_name = true) c
    WHERE c.persona_id IS NOT NULL
      AND c.legislatura LIKE 'repubblica_%'
      AND TRY_CAST(regexp_extract(c.legislatura, '(\d+)$', 1) AS INTEGER) BETWEEN 13 AND 19
),

-- ── Camera: firmatari senza anagrafica ────────────────────────────────
-- `deputato_label` = "EDOUARD BALLAMAN, XIII Legislatura della Repubblica".
cam_firm AS (
    SELECT
        CAST(f.persona_id AS VARCHAR)   AS persona_key,
        'camera'                        AS ramo,
        'repubblica'                    AS sistema,
        CAST(f.legislatura AS INTEGER)  AS legislatura,
        CAST(f.persona_id AS BIGINT)    AS persona_id,
        CAST(NULL AS BIGINT)            AS senatore_id,
        normalize_string(f.deputato_uri) AS deputato_uri,
        CAST(NULL AS VARCHAR)           AS nome,
        CAST(NULL AS VARCHAR)           AS cognome,
        normalize_string(split_part(f.deputato_label, ',', 1)) AS nome_completo,
        CAST(NULL AS VARCHAR)           AS gender,
        CAST(NULL AS DATE)              AS data_nascita,
        CAST(NULL AS VARCHAR)           AS luogo_nascita,
        'camera_firmatari'              AS fonte,
        4                               AS _prio
    FROM read_parquet({support.camera_firmatari.outputs}, union_by_name = true) f
    WHERE f.persona_id IS NOT NULL
      AND f.legislatura BETWEEN 13 AND 19
),

-- ── Nomi Camera per persona_id (per completare i senatori) ────────────
-- 28% delle righe di `senato_anagrafica` (Leg13-16) non ha nome/cognome;
-- per i senatori con ponte lo stesso `persona_id` ha il nome in Camera.
-- Si usa l'intera Repubblica (non solo 13-19) perché il ponte può puntare
-- a un mandato più vecchio.
nomi_camera AS (
    SELECT
        CAST(c.persona_id AS BIGINT) AS persona_id,
        max(normalize_string(c.nome))    AS nome,
        max(normalize_string(c.cognome)) AS cognome,
        max(normalize_string(c.gender))  AS gender
    FROM read_parquet({support.camera_deputati.outputs}, union_by_name = true) c
    WHERE c.persona_id IS NOT NULL
      AND c.legislatura LIKE 'repubblica_%'
    GROUP BY 1
),

unione AS (
    SELECT * FROM sen_anag
    UNION ALL SELECT * FROM sen_dib
    UNION ALL SELECT * FROM cam_anag
    UNION ALL SELECT * FROM cam_firm
),

-- Una riga per chiave: le colonne assenti nella fonte vincente si completano
-- con MAX() sulle altre righe della stessa chiave (es. nome dall'anagrafica,
-- gender dalla Camera). La priorità della fonte è dentro ogni CTE.
aggregata AS (
    SELECT
        persona_key,
        ramo,
        sistema,
        legislatura,
        max(persona_id)                                        AS persona_id,
        max(senatore_id)                                       AS senatore_id,
        max(deputato_uri)                                      AS deputato_uri,
        max(nome)                                              AS nome,
        max(cognome)                                           AS cognome,
        max(nome_completo)                                     AS nome_completo,
        max(gender)                                            AS gender,
        max(data_nascita)                                      AS data_nascita,
        max(luogo_nascita)                                     AS luogo_nascita,
        arg_min(fonte, _prio)                                  AS fonte,
        count(*)                                               AS n_fonti
    FROM unione
    GROUP BY 1, 2, 3, 4
),

finale AS (
    SELECT
        a.*,
        COALESCE(a.nome, nc.nome)       AS nome_f,
        COALESCE(a.cognome, nc.cognome) AS cognome_f,
        COALESCE(a.gender, nc.gender)   AS gender_f,
        -- `ponte` a livello di persona: se una riga della persona ha il
        -- ponte, tutte le sue righe (anche il ramo senza senatore_id) lo
        -- dichiarano — l'identità è unificata.
        bool_or(a.persona_id IS NOT NULL AND a.senatore_id IS NOT NULL)
            OVER (PARTITION BY a.persona_key) AS ponte
    FROM aggregata a
    LEFT JOIN nomi_camera nc ON nc.persona_id = a.persona_id
)

SELECT
    persona_key,
    ramo,
    sistema,
    legislatura,
    persona_id,
    senatore_id,
    deputato_uri,
    nome_f     AS nome,
    cognome_f  AS cognome,
    -- nome leggibile: "Nome Cognome", altrimenti la label della fonte
    COALESCE(
        NULLIF(TRIM(CONCAT(COALESCE(nome_f, ''), ' ', COALESCE(cognome_f, ''))), ''),
        nome_completo
    ) AS nome_completo,
    gender_f   AS gender,
    data_nascita,
    luogo_nascita,
    fonte,
    n_fonti,
    ponte
FROM finale
ORDER BY persona_key, ramo, legislatura
