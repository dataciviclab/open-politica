# senato_interventi — chi parla in aula (Senato, XIX leg.)

Il senatore che prende la parola in aula/commissione: la dimensione "attività".

## Dati
- Fonte: dati.senato.it — `osr:Intervento` (graph composizione/19), 36.168
- Una riga per intervento (URI), con `senatore_id`, `data`, `oggetto`
- La data è della seduta (`osr:dataSeduta`)

## Numeri
- Per anno: ~9-10k (2023-2026), 2022 parziale (971), ~195 parlanti/anno
- Top: Calandrini 1.598, Balboni 1.077, Tosato 895

## Note tecniche
- `dataSeduta` è in un graph diverso da `composizione/19` → il pattern va
  messo FUORI dal GRAPH (altrimenti la data resta NULL)
- `FILTER(isIRI(?int))` esclude gli interventi bnode (commissione)
- Dedup su intervento_id

## Rebuild
make run-senato-interventi
