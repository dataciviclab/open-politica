-- mart_profilo_senatore — profilo di voto dei senatori (XIX leg.)
-- Ranking per coerenza con l'esito (proxy di allineamento al governo)
-- e per partecipazione. Pass-through del clean con ordinamento utile.
SELECT *
FROM clean_input
ORDER BY pct_coerente ASC, n_voti DESC
