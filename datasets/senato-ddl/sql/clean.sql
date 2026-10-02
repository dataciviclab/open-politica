-- clean.sql — senato_ddl
--
-- Iter legislativo dei disegni di legge del Senato (Leg13–Leg19).
-- Input: 3 sorgenti SPARQL (q1, q2a, q2b) unite con union_by_name via
-- read.mode: all — ogni sorgente ha un sottoinsieme di colonne (il WAF
-- Senato rifiuta query > ~15 colonne). L'unione produce 3 righe per ddl
-- (una per sorgente) con colonne vuote per quelle non presenti.
-- Qui ricombiniamo con GROUP BY ddl + MAX.
--
-- Filtro: teniamo SOLO gli URI /ddl/N (con metadati); /iterDdl/N sono
-- l'iter (metadati vuoti). Il WAF rifiuta CONTAINS in query → filtro qui.
--
-- Nota: il plugin SPARQL scrive CSV non quotato → read_mode: robust.
--
-- URN (2026-10-02): calcolata DOPO l'aggregazione (natura/data/numero
-- possono stare su sorgenti SPARQL diverse — caso ROW-LEVEL era sbagliato).
-- Placeholder 2100-01-01 → NULL (escluso anche da MAX(data_legge));
-- costituzionale (case-insensitive) + data reale → legge.costituzionale.

SELECT
    id_ddl,
    atto_num,
    ddl_url,
    titolo,
    titolo_breve,
    stato,
    data_presentazione,
    data_stato_ddl,
    natura,
    fase,
    ramo,
    iniziativa,
    descr_iniziativa,
    progressivo_iter,
    numero_fase,
    numero_fase_compatto,
    id_fase,
    legislatura,
    anno,
    presentato_trasmesso,
    numero_legge,
    data_legge,
    relatore,
    classificazione,
    assegnazione,
    testo_presentato,
    testo_approvato,
    testo_unificato,
    stralcio,
    CASE
        WHEN numero_legge IS NOT NULL
         AND data_legge IS NOT NULL
         AND CAST(data_legge AS DATE) <> DATE '2100-01-01'
            THEN CASE
                WHEN LOWER(COALESCE(natura, '')) = 'costituzionale'
                    THEN 'urn:nir:stato:legge.costituzionale:'
                         || CAST(CAST(data_legge AS DATE) AS VARCHAR)
                         || ';' || CAST(numero_legge AS VARCHAR)
                ELSE 'urn:nir:stato:legge:'
                     || CAST(CAST(data_legge AS DATE) AS VARCHAR)
                     || ';' || CAST(numero_legge AS VARCHAR)
            END
        ELSE NULL
    END AS urn_normattiva
FROM (
    SELECT
        -- id numerico del ddl
        MAX(TRY_CAST(
            CASE WHEN idDdl IS NOT NULL
                 THEN regexp_extract(CAST(idDdl AS VARCHAR), '(\d+)', 1)
            END AS BIGINT
        ))                                                            AS id_ddl,
        -- alias esplicito per join cross-repo (atto_num == id_ddl)
        MAX(TRY_CAST(
            CASE WHEN idDdl IS NOT NULL
                 THEN regexp_extract(CAST(idDdl AS VARCHAR), '(\d+)', 1)
            END AS BIGINT
        ))                                                            AS atto_num,
        MAX(normalize_string(ddl))                                    AS ddl_url,
        MAX(normalize_string(titolo))                                 AS titolo,
        MAX(normalize_string(titoloBreve))                            AS titolo_breve,
        MAX(normalize_string(stato))                                  AS stato,
        MAX(TRY_CAST(dataPresentazione AS DATE))                      AS data_presentazione,
        MAX(TRY_CAST(dataStatoDdl AS DATE))                           AS data_stato_ddl,
        MAX(normalize_string(natura))                                 AS natura,
        -- fase: codice atto (C.1774 = Camera, S.782 = Senato); blank node esclusi
        MAX(CASE WHEN fase LIKE 'nodeID://%' OR fase IS NULL THEN NULL
                 ELSE normalize_string(fase)
            END)                                                      AS fase,
        MAX(normalize_string(ramo))                                   AS ramo,
        -- iniziativa: URI → codice finale (es. INIZ-DDL-...)
        MAX(CASE
                WHEN iniziativa LIKE '%/iniziativa/%' THEN
                    substring(iniziativa, strpos(iniziativa, '/iniziativa/') + 12)
                ELSE normalize_string(iniziativa)
            END)                                                      AS iniziativa,
        MAX(normalize_string(descrIniziativa))                        AS descr_iniziativa,
        MAX(TRY_CAST(CAST(progressivoIter AS VARCHAR) AS BIGINT))     AS progressivo_iter,
        MAX(TRY_CAST(CAST(numeroFase AS VARCHAR) AS BIGINT))          AS numero_fase,
        MAX(normalize_string(numeroFaseCompatto))                     AS numero_fase_compatto,
        MAX(normalize_string(idFase))                                 AS id_fase,
        MAX(TRY_CAST(CAST(legislatura AS VARCHAR) AS BIGINT))         AS legislatura,
        -- anno: estratto da data_presentazione, utile per contesto temporale
        MAX(TRY_CAST(strftime(TRY_CAST(dataPresentazione AS DATE), '%Y') AS INTEGER)) AS anno,
        MAX(normalize_string(presentatoTrasmesso))                    AS presentato_trasmesso,
        MAX(TRY_CAST(CAST(numeroLegge AS VARCHAR) AS BIGINT))         AS numero_legge,
        -- Solo date valide: il placeholder 2100-01-01 non deve vincere
        -- su MAX quando lo stesso ddl ha anche una data reale (sorgenti diverse).
        MAX(CASE
                WHEN TRY_CAST(dataLegge AS DATE) IS NOT NULL
                 AND TRY_CAST(dataLegge AS DATE) <> DATE '2100-01-01'
                    THEN TRY_CAST(dataLegge AS DATE)
            END)                                                      AS data_legge,
        MAX(normalize_string(relatore))                               AS relatore,
        MAX(normalize_string(classificazione))                        AS classificazione,
        MAX(normalize_string(assegnazione))                           AS assegnazione,
        MAX(normalize_string(testoPresentato))                        AS testo_presentato,
        MAX(normalize_string(testoApprovato))                         AS testo_approvato,
        MAX(normalize_string(testoUnificato))                         AS testo_unificato,
        MAX(normalize_string(stralcio))                               AS stralcio
    FROM raw_input
    WHERE ddl LIKE '%/ddl/%'
    GROUP BY ddl
    HAVING id_ddl IS NOT NULL
       AND fase IS NOT NULL
) agg
