-- mart_intensita_emendativa.sql — il dossier per atto con l'intensità emendativa
--
-- Unisce il corpus+iter (clean_input, che ha fase) con l'intensità
-- emendativa per atto (dalla source senato_emendamenti, agganciata su fase
-- nel clean). La metrica: quanti emendamenti ha ricevuto ogni atto, quanto
-- testo di emendamenti, e come si distribuisce tra Aula e Commissione.

SELECT
    atto_num,
    fase,
    stato,
    natura,
    data_presentazione,
    numero_legge,
    famiglie,
    testo_totale             AS testo_ddl,
    articoli_totali,
    n_emend,
    testo_emendamenti,
    n_aula,
    n_commissione
FROM clean_input
