-- clean.sql — senato_votazioni
--
-- Voti individuali dei Senatori (XIX legislatura), estratti via SPARQL da
-- dati.senato.it con scripts/extract_senato_votazioni.py. Una riga =
-- voto di un senatore su una votazione (FAVOREVOLE / CONTRARIO / ASTENUTO),
-- arricchita dai metadati della votazione (seduta, data, esito, conteggi).

SELECT
  votazione,                                  -- URI univoco RDF (chiave join)
  regexp_extract(votazione, '(\d+-\d+-\d+)$', 1) AS votazione_id,  -- codice es. 19-229-4
  senatore_id,                                -- id locale Senato (da /senatore/N)
  normalize_string(voto)                      AS voto,
  TRY_CAST(data AS DATE)                      AS data,
  TRY_CAST(legislatura AS INTEGER)            AS legislatura,
  normalize_string(esito)                     AS esito,
  normalize_string(tipo_votazione)            AS tipo_votazione,
  seduta,
  n_favorevoli,
  n_contrari,
  n_astenuti,
  n_votanti,
  n_presenti,
  n_maggioranza,
  n_congedo_missione
FROM raw_input
