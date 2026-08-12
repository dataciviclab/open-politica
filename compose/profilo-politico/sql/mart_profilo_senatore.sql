-- mart_profilo — scheda viva dei parlamentari (Camera + Senato, XIX leg.)
-- Una riga per parlamentare, con ramo (camera/senato), partecipazione,
-- direzione di voto, coerenza con l'esito (solo Senato) e affidabilità
-- al proprio gruppo. Ordinato per affidabilità crescente (i più divergenti
-- dal gruppo in cima).
SELECT *
FROM clean_input
ORDER BY pct_col_gruppo ASC NULLS LAST, n_voti DESC
