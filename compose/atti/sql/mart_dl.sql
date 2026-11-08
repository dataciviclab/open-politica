-- mart_dl.sql — decreti-legge con esito di conversione (una riga per DL)
--
-- Grain: (dl_numero, dl_anno). I numeri DL ripartono ogni anno: la chiave è
-- la coppia, non il numero.
--
-- Replica la semantica di `compose/decreti-legge` sull'identità di
-- `mart_atti` (un solo punto di verità per numero/anno/data del decreto).
--
-- Esito: la fonte scrive lo stato in più varianti
--   convertito  → numero_legge valorizzato (su qualunque riga dell'iter)
--   decaduto    → "D-L decaduto" **o** "decreto legge decaduto"
--   restituito  → "restit. al Governo" **o** "restituito al Governo per ..."
--   in_esame    → nessuna delle precedenti
-- La vecchia versione confrontava per uguaglianza esatta e perdeva le
-- varianti lunghe (105 DL "decreto legge decaduto" + 16 "restituito al
-- Governo per essere ripresentato"): qui il match è per pattern.
SELECT
    dl_numero,
    dl_anno,
    max(data_dl)                                          AS data_dl,
    max(data_dl_fonte)                                    AS data_dl_fonte,
    min(data)                                             AS data_presentazione,
    max(data_legge)                                       AS data_conversione,
    CASE
        WHEN bool_or(numero_legge IS NOT NULL)            THEN 'convertito'
        WHEN bool_or(lower(stato) LIKE '%decadut%')       THEN 'decaduto'
        WHEN bool_or(lower(stato) LIKE '%restit%')        THEN 'restituito'
        ELSE 'in_esame'
    END                                                   AS esito,
    date_diff('day', min(data), max(data_legge))          AS giorni_conversione,
    arg_max(titolo, coalesce(data_legge, data))           AS titolo,
    -- atto rappresentativo: ramo Senato, poi iter più recente (stessa regola
    -- della vecchia `decreti_legge`: l'edge grafo punta a un solo atto)
    arg_max(
        atto_id,
        (CASE WHEN ramo = 'senato' THEN 1 ELSE 0 END) * 1000000000000
        + epoch(coalesce(data_legge, data, DATE '1900-01-01'))
    )                                                     AS atto_id,
    count(*)                                              AS n_atti,
    max(numero_legge)                                     AS numero_legge,
    max(urn_normattiva)                                   AS urn_legge
FROM mart_atti
WHERE dl_numero IS NOT NULL AND dl_anno IS NOT NULL
GROUP BY 1, 2
ORDER BY dl_anno, dl_numero
