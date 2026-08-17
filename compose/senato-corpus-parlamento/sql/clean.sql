-- clean.sql — senato_corpus_parlamento
--
-- Join del corpus Akoma Ntoso (un documento per riga, da senato-akn) con
-- l'iter legislativo (senato_ddl, support). Chiave: atto_num ↔ ddl_url
-- (http://dati.senato.it/ddl/<atto_num>).
--
-- Il corpus viene aggregato per atto (tipologie, famiglie, peso testo,
-- articoli); senato_ddl ha più righe per atto (una per fase dell'iter) →
-- si prende la fase più recente e l'esito migliore (numero_legge se c'è).
-- L'intensità emendativa (senato_emendamenti, seconda source raw) si aggancia
-- su fase (S.NNN) — la metrica F3 "quanto un atto è stato emendato".

WITH doc AS (
    SELECT * FROM raw_input
),
emend AS (
    SELECT fase, n_emend, testo_totale, n_aula, n_commissione
    FROM read_parquet('{support.senato_emendamenti.path}')
),
atto AS (
    SELECT
        atto_num,
        string_agg(DISTINCT tipologia, ',')                    AS tipologie,
        string_agg(DISTINCT split_part(famiglia, ';', 1), ',') AS famiglie,
        count(*)                                               AS n_documenti,
        sum(text_len)                                          AS testo_totale,
        sum(articles_count)                                    AS articoli_totali,
        min(work_date)                                         AS data_primo_documento
    FROM doc
    WHERE atto_num IS NOT NULL
    GROUP BY atto_num
),
iter AS (
    SELECT * FROM read_parquet('{support.senato_ddl.clean}')
),
iter_agg AS (
    SELECT
        ddl_url,
        arg_max(fase, coalesce(data_stato_ddl, '1900-01-01'))                  AS fase,
        arg_max(stato, coalesce(data_stato_ddl, '1900-01-01'))                 AS stato,
        arg_max(natura, coalesce(data_stato_ddl, '1900-01-01'))                AS natura,
        arg_max(data_presentazione, coalesce(data_stato_ddl, '1900-01-01'))    AS data_presentazione,
        max(numero_legge)                                                      AS numero_legge,
        max(data_legge)                                                        AS data_legge
    FROM iter
    GROUP BY ddl_url
)
SELECT
    a.atto_num,
    a.tipologie,
    a.famiglie,
    a.n_documenti,
    a.testo_totale,
    a.articoli_totali,
    a.data_primo_documento,
    i.fase,
    i.stato,
    i.natura,
    i.data_presentazione,
    i.numero_legge,
    i.data_legge,
    i.ddl_url,
    e.n_emend,
    e.testo_totale             AS testo_emendamenti,
    e.n_aula,
    e.n_commissione
FROM atto a
LEFT JOIN iter_agg i
  ON i.ddl_url = 'http://dati.senato.it/ddl/' || CAST(a.atto_num AS VARCHAR)
LEFT JOIN emend e
  ON e.fase = i.fase
