-- Clean: dait_amministratori_locali
-- Fonte: ammcom.csv + ammprov.csv + ammreg.csv (DAIT — Ministero dell'Interno)
-- Skip 2 righe di metadati gestito in dataset.yml (clean.read.skip: 2)
-- Encoding UTF-8, delim ; — union_by_name unisce i 3 CSV (colonne mancanti → NULL)
-- livello_ente iniettato da inject_column in dataset.yml
-- Date in formato DD/MM/YYYY — parsate da DuckDB via clean.read.dateformat
--
-- Colonna "lista_appartenenza/collegamento" rinominata in SQL
-- denominazione_{comune,provincia,regione} unificata in denominazione_ente
-- popolazione_censita e codice_dait_completo valorizzati solo per livello comune
-- data_elezione_max_carica presente solo per livello provincia
--
-- Codici territoriali (codice_regione/provincia/comune) mantenuti come VARCHAR
-- per preservare il leading zero. DAIT usa un proprio sistema di codifica
-- comunale (codice_comune a 4 cifre, non 3 come ISTAT): la concatenazione
-- regione(2)+provincia(3)+comune(4) genera codice_dait_completo (9 caratteri).
-- Non e' un codice ISTAT — serve una mappatura verificata per join con dataset
-- ISTAT o BDAP.

SELECT
    {year}::INTEGER                                       AS anno,
    livello_ente                                          AS livello_ente,
    NULLIF(codice_regione, '')                            AS codice_regione,
    NULLIF(codice_provincia, '')                          AS codice_provincia,
    NULLIF(codice_comune, '')                             AS codice_comune,
    -- codice_dait_completo ha senso solo a livello comune (9 cifre)
    CASE WHEN livello_ente = 'comune'
         THEN NULLIF(codice_regione || codice_provincia || codice_comune, '')
    END                                                   AS codice_dait_completo,
    -- denominazione unificata: comune > provincia > regione
    COALESCE(
        NULLIF(denominazione_comune, ''),
        NULLIF(denominazione_provincia, ''),
        NULLIF(denominazione_regione, '')
    )                                                     AS denominazione_ente,
    NULLIF(sigla_provincia, '')                           AS sigla_provincia,
    -- popolazione censita disponibile solo a livello comune
    -- (auto-detect la tipizza BIGINT; vuoti → NULL nativo)
    CASE WHEN livello_ente = 'comune'
         THEN popolazione_censita_alla_data_elezione::INTEGER
    END                                                   AS popolazione_censita,
    cognome                                               AS cognome,
    nome                                                  AS nome,
    sesso                                                 AS sesso,
    data_nascita                                          AS data_nascita,
    luogo_nascita                                         AS luogo_nascita,
    descrizione_carica                                    AS descrizione_carica,
    NULLIF(incarico, '')                                  AS incarico,
    data_elezione                                         AS data_elezione,
    data_entrata_in_carica                                AS data_entrata_in_carica,
    -- solo livello provincia
    data_elezione_max_carica                              AS data_elezione_max_carica,
    NULLIF("lista_appartenenza/collegamento", '')         AS lista_appartenenza,
    NULLIF(titolo_studio, '')                             AS titolo_studio,
    NULLIF(professione, '')                               AS professione
FROM raw_input
