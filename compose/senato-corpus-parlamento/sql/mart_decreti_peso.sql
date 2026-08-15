-- mart_decreti_peso.sql — i decreti-legge per peso documentale
--
-- Il finding di senato-akn applicato all'iter: la decretazione d'urgenza
-- occupa una quota di testo sproporzionata rispetto al numero di atti.
-- Qui: per ogni DDL di conversione, esito dell'iter + peso del testo.

SELECT
    atto_num,
    fase,
    stato,
    esito,
    testo_totale,
    articoli_totali,
    n_documenti,
    famiglie
FROM (
    SELECT
        atto_num,
        fase,
        stato,
        natura,
        testo_totale,
        articoli_totali,
        n_documenti,
        famiglie,
        CASE
            WHEN numero_legge IS NOT NULL THEN 'convertito'
            WHEN stato = 'D-L decaduto' THEN 'decaduto'
            WHEN stato = 'restit. al Governo' THEN 'restituito'
            ELSE 'in_esame'
        END AS esito,
        row_number() OVER (
            PARTITION BY atto_num
            ORDER BY CASE
                WHEN numero_legge IS NOT NULL THEN 0
                WHEN stato = 'D-L decaduto' THEN 1
                WHEN stato = 'restit. al Governo' THEN 2
                ELSE 3
            END
        ) AS rn
    FROM clean_input
    WHERE natura = 'di conversione di decreto-legge'
)
WHERE rn = 1
