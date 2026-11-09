-- mart_atti.sql — dimensione atto pubblicata
--
-- Nessuna trasformazione: il clean è già lo schema canonico. L'ordinamento
-- fisico per atto_id serve al row-group pruning dei consumer (lookup per
-- atto_id salta la maggior parte del file), come nei mart di legal-graph.
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
    anno,
    stato,
    numero_legge,
    data_legge,
    urn_normattiva,
    dl_numero,
    dl_anno,
    data_dl,
    data_dl_fonte,
    n_fasi,
    source
FROM clean_input
ORDER BY atto_id
