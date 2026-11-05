-- clean.sql — senato_emendamenti_lod
--
-- Registro ufficiale emendamenti del Senato (Leg13–19) da dati.senato.it.
-- Una riga per emendamento (URI unico). PK: emend_uri_id.
--
-- `atto_num` = id in http://dati.senato.it/ddl/N (via oggetto → relativoA).
-- Un oggetto può relativoA più ddl (atti abbinati/unificati): il grano resta
-- l'emendamento → `atto_num` è il MIN (rappresentativo) e `n_atti` dice quanti
-- ddl sono collegati (0 = nessuno). È NULL dove la fonte non collega l'oggetto
-- a un ddl (sparso nelle legislature vecchie: Leg19 ~97%, Leg13 ~20%).
--
-- Chiave di join con senato-akn/senato_emendamenti:
--   (legislatura, atto_num, emend_id, ramo).

WITH base AS (
    SELECT
        CAST(regexp_extract(CAST(e AS VARCHAR), '(\d+)$', 1) AS BIGINT)      AS emend_uri_id,
        normalize_string(num)                                                AS emend_id,
        normalize_string(tipo)                                               AS tipo,
        TRY_CAST(flag AS INTEGER)                                            AS flag_commissione,
        CASE WHEN TRY_CAST(flag AS INTEGER) = 1 THEN 'commissione'
             ELSE 'aula' END                                                 AS ramo,
        TRY_CAST(regexp_extract(CAST(ddl AS VARCHAR), '(\d+)$', 1) AS BIGINT) AS atto_num,
        TRY_CAST(regexp_extract(CAST(og AS VARCHAR), '(\d+)$', 1) AS BIGINT)  AS oggetto_id,
        normalize_string(url)                                                AS url_testo,
        normalize_string(urlxml)                                             AS url_testo_xml,
        {year}                                                               AS legislatura
    FROM raw_input
    WHERE e IS NOT NULL
      AND num IS NOT NULL
)
SELECT
    emend_uri_id,
    any_value(emend_id)          AS emend_id,
    any_value(emend_id)          AS numero,
    any_value(tipo)              AS tipo,
    any_value(flag_commissione)  AS flag_commissione,
    any_value(ramo)              AS ramo,
    MIN(atto_num)                AS atto_num,
    count(DISTINCT atto_num)     AS n_atti,
    any_value(oggetto_id)        AS oggetto_id,
    any_value(url_testo)         AS url_testo,
    any_value(url_testo_xml)     AS url_testo_xml,
    any_value(legislatura)       AS legislatura
FROM base
GROUP BY emend_uri_id
