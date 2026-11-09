-- mart_persone.sql — dimensione persona pubblicata
--
-- Nessuna trasformazione: il clean è già lo schema canonico. Ordinamento
-- fisico per `persona_key` per il row-group pruning dei lookup per persona.
SELECT
    persona_key,
    ramo,
    sistema,
    legislatura,
    persona_id,
    senatore_id,
    deputato_uri,
    nome,
    cognome,
    nome_completo,
    gender,
    data_nascita,
    luogo_nascita,
    fonte,
    n_fonti,
    ponte
FROM clean_input
ORDER BY persona_key, ramo, legislatura
