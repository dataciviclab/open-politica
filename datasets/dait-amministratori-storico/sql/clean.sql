-- Clean: dait_amministratori_storico
-- Fonte: preprocess.py → storico_amministratori.csv (serie 1986–2025)
-- Il preprocess ha già unificato le due ere schema e prodotto header
-- snake_case; qui si fa solo tipizzazione e normalizzazione valori.
--
-- Date in formato DD/MM/YYYY — parsate da DuckDB via clean.read.dateformat
-- Codici territoriali mantenuti come VARCHAR (leading zero).
-- codice_dait_completo = regione(2)||provincia(3)||comune(4) — non ISTAT.

SELECT
    anno_snapshot::INTEGER                                 AS anno_snapshot,
    NULLIF(codice_regione, '')                             AS codice_regione,
    NULLIF(descrizione_regione, '')                        AS descrizione_regione,
    NULLIF(codice_provincia, '')                           AS codice_provincia,
    NULLIF(descrizione_provincia, '')                      AS descrizione_provincia,
    NULLIF(codice_comune, '')                              AS codice_comune,
    NULLIF(descrizione_comune, '')                         AS descrizione_comune,
    NULLIF(codice_regione || codice_provincia || codice_comune, '')
                                                            AS codice_dait_completo,
    NULLIF(sigla_provincia, '')                            AS sigla_provincia,
    NULLIF(istat_codice_comune, '')                        AS istat_codice_comune,
    -- Auto-detect DuckDB tipizza i numerici (BIGINT) e le date (DATE);
    -- i vuoti diventano NULL nativamente — non serve NULLIF su stringhe.
    popolazione_censita::INTEGER                          AS popolazione_censita,
    NULLIF(maggioritario_proporzionale, '')                AS maggioritario_proporzionale,
    NULLIF(descrizione_tempo_gestione, '')                 AS descrizione_tempo_gestione,
    data_elezione                                          AS data_elezione,
    data_ballottaggio                                      AS data_ballottaggio,
    consiglieri_spettanti::INTEGER                         AS consiglieri_spettanti,
    consiglieri_eletti::INTEGER                            AS consiglieri_eletti,
    assessori_assegnati::INTEGER                           AS assessori_assegnati,
    NULLIF(cognome, '')                                    AS cognome,
    NULLIF(nome, '')                                       AS nome,
    NULLIF(sesso, '')                                      AS sesso,
    data_nascita                                           AS data_nascita,
    NULLIF(sede_nascita, '')                               AS sede_nascita,
    livello_carica::INTEGER                                AS livello_carica,
    NULLIF(descrizione_carica, '')                         AS descrizione_carica,
    data_inizio_carica                                     AS data_inizio_carica,
    data_cessazione                                        AS data_cessazione,
    NULLIF(incarico, '')                                   AS incarico,
    data_inizio_incarico                                   AS data_inizio_incarico,
    data_fine_incarico                                     AS data_fine_incarico,
    NULLIF(funzione, '')                                   AS funzione,
    data_inizio_funzione                                   AS data_inizio_funzione,
    data_fine_funzione                                     AS data_fine_funzione,
    NULLIF(lista_appartenenza, '')                         AS lista_appartenenza,
    NULLIF(titolo_studio, '')                              AS titolo_studio,
    NULLIF(professione, '')                                AS professione
FROM raw_input
