-- mart_atto_corpus.sql — ogni atto con la sua dimensione documentale
--
-- Il testo (famiglie, peso, articoli) agganciato all'iter legislativo.
-- Il caso d'uso chiave: quanto pesa davvero un atto rispetto a quanto
-- viene "contato" nell'iter.

SELECT
    atto_num,
    fase,
    stato,
    natura,
    data_presentazione,
    numero_legge,
    famiglie,
    tipologie,
    n_documenti,
    testo_totale,
    articoli_totali
FROM clean_input
