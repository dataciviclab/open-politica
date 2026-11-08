-- clean.sql — atti (dimensione conformata del Parlamento)
--
-- Grain: una riga per ATTO nella sua numerazione d'origine
-- (ramo + legislatura + numero). Non è il grain della fonte:
-- `senato_ddl` è atto×fase (36.397 righe → 34.362 atti, 2026-11).
--
-- Chiave canonica `atto_id`:
--   senato:{id_ddl}                id_ddl Senato è unico globalmente
--                                  (34.362 distinti su 36.208 righe, verificato 2026-11)
--   camera:{legislatura}:{id_ddl}  l'id_ddl Camera riparte ogni legislatura:
--                                  6.328 valori su 7.614 compaiono in più legislature.
--                                  Senza legislatura 34.313 atti collassano su 7.614
--                                  nodi (bug presente in legal-graph fino a 2026-11).
--
-- Non fonde lo stesso atto tra i due rami: `ac{LEG}_{NUM}` (Camera) e
-- `id_ddl` (Senato) sono numerazioni indipendenti — 3.191 valori numerici
-- coincidono per caso, non per identità. L'unico ponte affidabile è
-- `urn_normattiva` quando l'atto è promulgato; il bridge per fase (S./C.) è
-- documentato in legal-graph/KEYS.md e non viene replicato qui.
--
-- `tipo` è un ENUM CHIUSO; `natura_raw` conserva il valore della fonte
-- (che include drift: date, codici, stati finiti nel campo `natura`).
--
-- Identità DL (dl_numero, dl_anno, data_dl): stessa logica di
-- compose/decreti-legge. La data del decreto è nel titolo ("decreto-legge
-- 27 dicembre 2024, n. 200"), NON in data_presentazione: per un DL emanato
-- a dicembre il DDL di conversione può essere presentato a gennaio, e usare
-- quell'anno sdoppia l'identità (misurato in #63).

WITH sen AS (
    SELECT * FROM read_parquet({support.senato_ddl.clean})
    WHERE id_ddl IS NOT NULL
),

cam AS (
    SELECT * FROM read_parquet({support.camera_ddl.clean})
),

leg AS (
    SELECT * FROM read_parquet({support.camera_leggi.clean})
),

-- ── Senato: atto×fase → atto ─────────────────────────────────────────────────
-- Riga rappresentativa per id_ddl: prima la fase con legge approvata, poi
-- la più recente. `data` è la PRIMA presentazione (min sulla partizione),
-- `stato` quello della fase rappresentativa (stato corrente dell'iter).
sen_pick AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY id_ddl
            ORDER BY
                (numero_legge IS NULL),
                coalesce(data_legge, data_fase) DESC NULLS LAST,
                progressivo_iter DESC NULLS LAST
        ) AS _rn
    FROM (
        SELECT
            'senato:' || CAST(id_ddl AS VARCHAR)                     AS atto_id,
            'senato'                                                 AS ramo,
            CAST(legislatura AS INTEGER)                             AS legislatura,
            CAST(id_ddl AS BIGINT)                                   AS numero_atto,
            CAST(id_ddl AS BIGINT)                                   AS id_ddl,
            TRY_CAST(atto_num AS BIGINT)                             AS atto_num,
            ddl_url                                                  AS atto_uri,
            normalize_string(titolo)                                 AS titolo,
            normalize_string(titolo_breve)                           AS titolo_breve,
            CAST(data_presentazione AS DATE)                         AS data_fase,
            min(CAST(data_presentazione AS DATE))
                OVER (PARTITION BY id_ddl)                           AS data_min,
            CAST(anno AS INTEGER)                                    AS anno,
            normalize_string(stato)                                  AS stato,
            normalize_string(natura)                                 AS natura_raw,
            CAST(numero_legge AS BIGINT)                             AS numero_legge,
            CAST(data_legge AS DATE)                                 AS data_legge,
            TRY_CAST(progressivo_iter AS BIGINT)                     AS progressivo_iter,
            NULLIF(normalize_string(urn_normattiva), '')             AS urn_normattiva,
            count(*) OVER (PARTITION BY id_ddl)                      AS n_fasi
        FROM sen
    )
),

sen_atto AS (
    SELECT
        atto_id,
        ramo,
        legislatura,
        numero_atto,
        id_ddl,
        atto_num,
        atto_uri,
        titolo,
        titolo_breve,
        CAST(data_min AS DATE) AS data,
        anno,
        stato,
        natura_raw,
        numero_legge,
        data_legge,
        urn_normattiva,
        n_fasi
    FROM sen_pick
    WHERE _rn = 1
),

-- ── DL di conversione: numero e data del decreto dal titolo ──────────────────
-- Forme in circolazione: "decreto-legge", "decreto legge", "decreto - legge",
-- a volte seguite da "del". Il numero può essere scritto "n. 91" o "n 91".
-- Fallback numerico per la data: "del 30/12/1999".
sen_dl_src AS (
    SELECT
        *,
        regexp_extract(
            titolo,
            '(?i)decreto\s*-?\s*legge\s+(?:del\s+)?(\d{1,2}(?:°)?\s+[a-zà-ù]+\s+\d{4})',
            1
        ) AS data_txt
    FROM sen_atto
    WHERE natura_raw ILIKE '%conversione%decreto-legge%'
),

sen_dl AS (
    SELECT
        atto_id,
        TRY_CAST(regexp_extract(titolo, 'n\.?\s*(\d+)', 1) AS BIGINT) AS dl_numero,
        COALESCE(
            TRY_CAST(
                printf(
                    '%04d-%02d-%02d',
                    TRY_CAST(regexp_extract(data_txt, '(\d{4})$', 1) AS INTEGER),
                    CASE lower(regexp_extract(data_txt, '^\d{1,2}°?\s+([a-zà-ù]+)', 1))
                        WHEN 'gennaio' THEN 1 WHEN 'febbraio' THEN 2 WHEN 'marzo' THEN 3
                        WHEN 'aprile' THEN 4 WHEN 'maggio' THEN 5 WHEN 'giugno' THEN 6
                        WHEN 'luglio' THEN 7 WHEN 'agosto' THEN 8 WHEN 'settembre' THEN 9
                        WHEN 'ottobre' THEN 10 WHEN 'novembre' THEN 11 WHEN 'dicembre' THEN 12
                    END,
                    TRY_CAST(regexp_extract(data_txt, '^(\d{1,2})', 1) AS INTEGER)
                ) AS DATE),
            TRY_CAST(
                try_strptime(
                    regexp_extract(titolo, 'del\s+(\d{1,2}/\d{1,2}/\d{4})', 1),
                    '%d/%m/%Y'
                ) AS DATE)
        ) AS data_dl
    FROM sen_dl_src
),

-- ── Camera: una riga per (legislatura, id_ddl) ───────────────────────────────
-- camera_leggi può avere più righe per lo stesso ddl_numero: si sceglie la
-- legge più recente (una sola legge per atto è l'invariante attesa).
leg_uniq AS (
    SELECT
        CAST(legislatura AS INTEGER) AS legislatura,
        CAST(ddl_numero AS BIGINT)   AS ddl_numero,
        arg_max(CAST(id_legge AS BIGINT), data_promulgazione) AS numero_legge,
        max(CAST(data_promulgazione AS DATE))                 AS data_legge,
        arg_max(NULLIF(normalize_string(urn_normattiva), ''), data_promulgazione) AS urn_normattiva
    FROM leg
    WHERE ddl_numero IS NOT NULL
    GROUP BY 1, 2
),

cam_atto AS (
    SELECT
        'camera:' || CAST(c.legislatura AS VARCHAR) || ':' || CAST(c.id_ddl AS VARCHAR) AS atto_id,
        'camera'                             AS ramo,
        CAST(c.legislatura AS INTEGER)       AS legislatura,
        CAST(c.id_ddl AS BIGINT)             AS numero_atto,
        CAST(c.id_ddl AS BIGINT)             AS id_ddl,
        CAST(NULL AS BIGINT)                 AS atto_num,
        normalize_string(c.atto_camera)      AS atto_uri,
        normalize_string(c.titolo)           AS titolo,
        CAST(NULL AS VARCHAR)                AS titolo_breve,
        CAST(c.data_presentazione AS DATE)   AS data,
        CAST(c.anno AS INTEGER)              AS anno,
        normalize_string(c.stato)            AS stato,
        normalize_string(c.tipo)             AS natura_raw,
        l.numero_legge                       AS numero_legge,
        l.data_legge                         AS data_legge,
        l.urn_normattiva                     AS urn_normattiva,
        1                                    AS n_fasi
    FROM cam c
    LEFT JOIN leg_uniq l
      ON l.legislatura = CAST(c.legislatura AS INTEGER)
     AND l.ddl_numero  = CAST(c.id_ddl AS BIGINT)
),

-- ── Unione dei due rami sullo schema canonico ────────────────────────────────
atti AS (
    SELECT
        s.atto_id,
        s.ramo,
        s.legislatura,
        s.numero_atto,
        s.id_ddl,
        s.atto_num,
        s.atto_uri,
        -- enum chiuso: i valori fuori elenco (drift: date, codici, stati
        -- finiti in `natura`) finiscono in ALTRO, con natura_raw intatta
        CASE
            WHEN s.natura_raw IS NULL THEN 'ALTRO'
            WHEN lower(s.natura_raw) = 'ordinaria' THEN 'DISEGNO DI LEGGE'
            WHEN lower(s.natura_raw) = 'costituzionale' THEN 'DISEGNO DI LEGGE COSTITUZIONALE'
            WHEN lower(s.natura_raw) = 'di conversione di decreto-legge'
                THEN 'DISEGNO DI LEGGE DI CONVERSIONE'
            WHEN lower(s.natura_raw) = 'di approvazione di bilancio'
                THEN 'DISEGNO DI LEGGE DI BILANCIO'
            ELSE 'ALTRO'
        END                                  AS tipo,
        s.natura_raw,
        s.titolo,
        s.titolo_breve,
        s.data,
        coalesce(s.anno, EXTRACT(year FROM s.data)) AS anno,
        s.stato,
        s.numero_legge,
        s.data_legge,
        s.urn_normattiva,
        CASE WHEN s.natura_raw ILIKE '%conversione%decreto-legge%'
             THEN d.dl_numero END            AS dl_numero,
        CASE WHEN s.natura_raw ILIKE '%conversione%decreto-legge%'
             THEN coalesce(EXTRACT(year FROM d.data_dl), EXTRACT(year FROM s.data))
             END                             AS dl_anno,
        CASE WHEN s.natura_raw ILIKE '%conversione%decreto-legge%'
             THEN d.data_dl END              AS data_dl,
        CASE WHEN s.natura_raw ILIKE '%conversione%decreto-legge%'
             THEN CASE WHEN d.data_dl IS NOT NULL THEN 'titolo' ELSE 'presentazione' END
             END                             AS data_dl_fonte,
        s.n_fasi,
        'senato_ddl'                         AS source
    FROM sen_atto s
    LEFT JOIN sen_dl d USING (atto_id)

    UNION ALL

    SELECT
        c.atto_id,
        c.ramo,
        c.legislatura,
        c.numero_atto,
        c.id_ddl,
        c.atto_num,
        c.atto_uri,
        CASE
            WHEN c.natura_raw IS NULL THEN 'ALTRO'
            WHEN lower(c.natura_raw) = 'progetto di legge' THEN 'DISEGNO DI LEGGE'
            ELSE 'ALTRO'
        END                                  AS tipo,
        c.natura_raw,
        c.titolo,
        c.titolo_breve,
        c.data,
        coalesce(c.anno, EXTRACT(year FROM c.data)) AS anno,
        c.stato,
        c.numero_legge,
        c.data_legge,
        c.urn_normattiva,
        CAST(NULL AS BIGINT)  AS dl_numero,
        CAST(NULL AS INTEGER) AS dl_anno,
        CAST(NULL AS DATE)    AS data_dl,
        CAST(NULL AS VARCHAR) AS data_dl_fonte,
        c.n_fasi,
        'camera_ddl'                         AS source
    FROM cam_atto c
)

SELECT
    atto_id,
    ramo,
    legislatura,
    numero_atto,
    id_ddl,
    atto_num,
    atto_uri,
    tipo,
    natura_raw,
    titolo,
    titolo_breve,
    data,
    CAST(anno AS INTEGER) AS anno,
    stato,
    numero_legge,
    data_legge,
    urn_normattiva,
    dl_numero,
    CAST(dl_anno AS INTEGER) AS dl_anno,
    data_dl,
    data_dl_fonte,
    n_fasi,
    source
FROM atti
ORDER BY atto_id
