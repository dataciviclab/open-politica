-- mart_dettaglio — ogni decreto-legge con esito
SELECT
    dl_numero,
    dl_anno,
    data_presentazione,
    data_conversione,
    esito,
    giorni_conversione,
    titolo
FROM clean_input
ORDER BY data_presentazione DESC
