-- clean.sql — ponte_persona
-- Ponte persona_id (Camera) ↔ senatore_id (Senato), prodotto da
-- scripts/build_ponte_persona.py via match su cognome+nome normalizzati.
SELECT
    senatore_id,
    persona_id,
    normalize_string(tipo_match) AS tipo_match
FROM raw_input
