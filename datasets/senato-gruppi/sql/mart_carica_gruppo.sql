-- mart_carica_gruppo — distribuzione delle cariche nei gruppi
SELECT
    carica,
    count(*) AS n
FROM clean_input
GROUP BY carica
ORDER BY n DESC
