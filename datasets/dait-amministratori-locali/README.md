# dait-amministratori-locali

Anagrafe degli Amministratori Locali e Regionali (DAIT) — snapshot corrente, tre livelli territoriali (comune, provincia, regione).

**Fonte**: Ministero dell'Interno — Dipartimento per gli Affari Interni e Territoriali
- **URL**: https://dait.interno.gov.it/elezioni/open-data/amministratori-locali-e-regionali-in-carica
- **Download diretto**: `ammcom.csv` (comuni, ~30 MB), `ammprov.csv` (province), `ammreg.csv` (regioni)

## Domanda

*Chi sono gli amministratori locali italiani? Quali profili demografici (età, genere, titolo di studio, professione) hanno sindaci, assessori e consiglieri? Come cambia la composizione della classe politica locale tra territori e livelli di governo?*

Sotto-domande esplorative:
- Quante donne sono elette? La presenza femminile varia per carica?
- Qual è l'età media di sindaci, assessori, consiglieri?
- Ci sono differenze territoriali (Nord/Sud) nella composizione?
- Come si confrontano i profili tra livello comunale, provinciale e regionale?

## Dataset

- **Fonte**: `ammcom.csv` + `ammprov.csv` + `ammreg.csv` (DAIT) — uniti con `inject_column: livello_ente`
- **Granularità**: 1 riga = 1 amministratore in 1 carica in 1 ente
- **Periodo**: snapshot corrente (2026)
- **Righe**: 127.805 (125.953 comuni + 986 province + 866 regioni)
- **Colonne (22)**: anno, livello_ente (comune/provincia/regione), codice_regione, codice_provincia, codice_comune, codice_dait_completo, denominazione_ente, sigla_provincia, popolazione_censita, cognome, nome, sesso, data_nascita, luogo_nascita, descrizione_carica, incarico, data_elezione, data_entrata_in_carica, data_elezione_max_carica, lista_appartenenza, titolo_studio, professione

Note sullo schema unificato:
- `livello_ente` distingue i tre livelli; le colonne territoriali non esistenti a un dato livello sono NULL
- `denominazione_ente` unifica comune/provincia/regione (prima era `denominazione_comune`)
- `codice_dait_completo` e `popolazione_censita` valorizzati solo per `livello_ente = 'comune'`
- `data_elezione_max_carica` presente solo per `livello_ente = 'provincia'`

## Mart

| Mart | Descrizione |
|---|---|
| `mart_profilo_carica` | Conteggi, età media, % femmine/maschi per carica (solo comuni) |
| `mart_profilo_demografico` | Distribuzione sesso × classe di età per carica (solo comuni) |
| `mart_territorio` | Composizione per regione × carica (solo comuni) |
| `mart_profilo_livello` | Confronto profilo tra comuni, province e regioni (tutti i livelli) |

Le prime 3 mart sono filtrate su `livello_ente = 'comune'` per preservare le metriche storiche. `mart_profilo_livello` include tutti e 3 i livelli — utile per confrontare composizione e profilo della classe dirigente tra livelli di governo. I dati grezzi multi-livello sono nel clean layer per analisi ad hoc.

## Esecuzione

```bash
cd open-politica
toolkit run -c datasets/dait-amministratori-locali/dataset.yml
```

## Issue di riferimento

- Intake: [#349](https://github.com/dataciviclab/dataset-incubator/issues/349)
