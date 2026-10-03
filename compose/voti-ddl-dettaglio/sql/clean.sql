-- clean.sql — voti_ddl_dettaglio
--
-- Join disagregato leggero: raw_input = oggetto (GCS), support = voti/ddl/anag.
-- ddl_id = osr:idDdl (contratto senato-ddl). Dedup su (votazione_id, senatore_id).
-- external: {support.*.clean} è lista SQL di URL (no quote) — pattern #58.

WITH

og AS (
    SELECT
        votazione_id,
        oggetto_id,
        ddl_id,
        esito AS esito_votazione,
        tipo_votazione,
        legislatura
    FROM raw_input
    WHERE ddl_id IS NOT NULL
),

voti AS (
    SELECT
        votazione_id,
        senatore_id,
        voto,
        data
    FROM read_parquet({support.senato_votazioni.clean})
),

ddl AS (
    -- Aggregatori deterministici (stile decreti-legge #58): senato_ddl ha
    -- più fasi per id_ddl; ANY_VALUE sarebbe non riproducibile su stato/urn.
    SELECT
        id_ddl AS ddl_id,
        arg_max(titolo, coalesce(data_legge, data_presentazione, DATE '1900-01-01')) AS titolo,
        arg_max(stato, coalesce(data_legge, data_presentazione, DATE '1900-01-01')) AS stato,
        max(numero_legge) AS numero_legge,
        arg_max(urn_normattiva, coalesce(data_legge, data_presentazione, DATE '1900-01-01')) AS urn_normattiva,
        min(data_presentazione) AS data_presentazione,
        max(data_legge) AS data_legge
    FROM read_parquet({support.senato_ddl.clean})
    WHERE id_ddl IS NOT NULL
    GROUP BY id_ddl
),

anag AS (
    SELECT DISTINCT senatore_id, nome, cognome
    FROM read_parquet({support.senato_anagrafica.clean})
),

dettaglio AS (
    SELECT
        v.votazione_id,
        v.senatore_id,
        a.nome,
        a.cognome,
        v.voto,
        v.data,
        o.ddl_id,
        o.oggetto_id,
        o.esito_votazione,
        o.tipo_votazione,
        o.legislatura,
        d.titolo AS ddl_titolo,
        d.stato AS ddl_stato,
        d.numero_legge,
        d.urn_normattiva
    FROM voti v
    JOIN og o ON o.votazione_id = v.votazione_id
    LEFT JOIN ddl d ON d.ddl_id = o.ddl_id
    LEFT JOIN anag a ON a.senatore_id = v.senatore_id
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY votazione_id, senatore_id
            ORDER BY data DESC NULLS LAST, ddl_id
        ) AS _rn
    FROM dettaglio
)

SELECT
    votazione_id,
    senatore_id,
    nome,
    cognome,
    voto,
    data,
    ddl_id,
    oggetto_id,
    esito_votazione,
    tipo_votazione,
    legislatura,
    ddl_titolo,
    ddl_stato,
    numero_legge,
    urn_normattiva
FROM dedup
WHERE _rn = 1
