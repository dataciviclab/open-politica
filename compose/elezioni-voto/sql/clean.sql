-- Clean: elezioni_voto — UNION ALL normalizzato dei 3 dataset elettorali
-- Legge i clean parquet locali via support pattern (glob DuckDB multi-anno).
--
-- Schema unificato:
--   data_elezione, tipo_elezione, regione, provincia, comune,
--   elettori, votanti, schede_bianche, affluenza_pct (calcolata),
--   lista, voti_lista, candidato, voti_candidato,
--   turno, seggi_lista, circoscrizione

WITH

-- ── 1. Elezioni Comunali ──────────────────────────────────────────
comunali AS (
    SELECT
        data_elezione,
        'comunali' AS tipo_elezione,
        regione,
        provincia,
        comune,
        NULL AS circoscrizione,
        elettori,
        votanti,
        schede_bianche,
        ROUND(CAST(votanti AS DOUBLE) / NULLIF(CAST(elettori AS DOUBLE), 0) * 100, 2) AS affluenza_pct,
        lista,
        voti_lista,
        candidato,
        voti_candidato,
        turno,
        seggi_lista
    -- external multi-anno: {support.*.clean} = lista URL SQL (no quote)
    FROM read_parquet({support.elezioni_comunali.clean}, union_by_name=true)
),

-- ── 2. Elezioni Europee ───────────────────────────────────────────
europee AS (
    SELECT
        data_elezione,
        'europee' AS tipo_elezione,
        regione,
        provincia,
        comune,
        circoscrizione,
        elettori,
        votanti,
        schede_bianche,
        ROUND(CAST(votanti AS DOUBLE) / NULLIF(CAST(elettori AS DOUBLE), 0) * 100, 2) AS affluenza_pct,
        lista,
        voti_lista,
        NULL AS candidato,
        NULL AS voti_candidato,
        NULL AS turno,
        NULL AS seggi_lista
    FROM read_parquet({support.elezioni_europee.clean}, union_by_name=true)
),

-- ── 3. Elezioni Regionali ─────────────────────────────────────────
regionali AS (
    SELECT
        data_elezione,
        'regionali' AS tipo_elezione,
        regione,
        provincia,
        comune,
        circoscrizione,
        elettori,
        votanti,
        schede_bianche,
        ROUND(CAST(votanti AS DOUBLE) / NULLIF(CAST(elettori AS DOUBLE), 0) * 100, 2) AS affluenza_pct,
        lista,
        voti_lista,
        candidato,
        voti_candidato,
        NULL AS turno,
        NULL AS seggi_lista
    FROM read_parquet({support.elezioni_regionali.clean}, union_by_name=true)
)

-- ── Final: UNION ALL ──────────────────────────────────────────────
SELECT * FROM comunali
UNION ALL BY NAME
SELECT * FROM europee
UNION ALL BY NAME
SELECT * FROM regionali
