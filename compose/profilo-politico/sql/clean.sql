-- clean.sql — profilo_politico
--
-- Scheda viva del senatore (XIX leg.), assemblata dai clean locali di:
--   senato_votazioni  → voti individuali (FAVOREVOLE/CONTRARIO/ASTENUTO)
--   senato_anagrafica → nome/cognome
--   ponte_persona     → persona_id Camera (identità unica)
--   membri_governo    → ruoli di governo (via persona_id)
--
-- Metriche:
--   partecipazione : n_voti espressi su n votazioni
--   coerenza       : % di voti in linea con l'esito della votazione
--                    (FAVOREVOLE su approvata, CONTRARIO su respinta).
--                    NOTA: il Senato vota soprattutto su emendamenti
--                    dell'opposizione respinti → CONTRARIO = votare col
--                    governo. Non confondere con ribellione.

WITH

voti AS (
    SELECT
        senatore_id,
        count(*)                                                              AS n_voti,
        count(*) FILTER (WHERE voto = 'FAVOREVOLE')                           AS n_favorevoli,
        count(*) FILTER (WHERE voto = 'CONTRARIO')                            AS n_contrari,
        count(*) FILTER (WHERE voto = 'ASTENUTO')                             AS n_astenuti,
        count(*) FILTER (
            WHERE (esito = 'approvato' AND voto = 'FAVOREVOLE')
               OR (esito = 'respinto'   AND voto = 'CONTRARIO')
        )                                                                     AS n_coerenti
    FROM read_parquet('out/data/clean/senato_votazioni/2026/senato_votazioni_2026_clean.parquet')
    GROUP BY senatore_id
),

anagrafica AS (
    SELECT DISTINCT senatore_id, nome, cognome
    FROM read_parquet('out/data/clean/senato_anagrafica/2026/senato_anagrafica_2026_clean.parquet')
),

ponte AS (
    SELECT senatore_id, persona_id
    FROM read_parquet('out/data/clean/ponte_persona/2026/ponte_persona_2026_clean.parquet')
    WHERE tipo_match = '1to1'
),

governo AS (
    SELECT persona_id, count(*) AS n_cariche_governo
    FROM read_parquet('out/data/clean/membri_governo/2026/membri_governo_2026_clean.parquet')
    WHERE end_date IS NULL
    GROUP BY persona_id
)

SELECT
    a.senatore_id,
    a.nome,
    a.cognome,
    p.persona_id,
    v.n_voti,
    v.n_favorevoli,
    v.n_contrari,
    v.n_astenuti,
    round(100.0 * v.n_coerenti / NULLIF(v.n_voti, 0), 1)                      AS pct_coerente,
    COALESCE(g.n_cariche_governo, 0)                                          AS n_cariche_governo,
    COALESCE(g.n_cariche_governo, 0) > 0                                      AS in_governo
FROM anagrafica a
JOIN voti v ON a.senatore_id = v.senatore_id
LEFT JOIN ponte p ON a.senatore_id = p.senatore_id
LEFT JOIN governo g ON p.persona_id = g.persona_id
