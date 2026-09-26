---
status: todo
---

# Records: record personali e migliori prestazioni

L'app dice cosa hai fatto giorno per giorno, ma non quali sono le tue
prestazioni migliori. Qui si aggiunge una pagina **Records** con i tempi
migliori sulle distanze classiche, ricavati dai file FIT. Per ogni record si
vede quando e' stato fatto e con quale attivita'.

## Dati, verificato

- `records` in `activities.db` ha `distance_km` e `ts_epoch` secondo per
  secondo per **129 attivita'**, fra cui le 32 corse (da aprile 2025 a
  settembre 2026).
- `activities` ha gia' distanza, durata e dislivello totali per attivita': i
  record "dell'attivita' intera" (la piu' lunga, quella con piu' dislivello)
  vengono da li' senza calcoli.

## Work

- **Migliori prestazioni di corsa** su 1 km, 5 km, 10 km e mezza maratona:
  - per ogni corsa, il tratto piu' veloce di quella lunghezza dentro
    l'attivita', non solo le corse lunghe esattamente quanto la distanza;
  - due indici che scorrono su `distance_km`: per ogni punto di partenza, il
    primo punto che copre la distanza;
  - la durata del tratto e' la differenza di `ts_epoch`, **pause comprese**,
    come fa Garmin.
- Il calcolo e' costoso: va fatto **una volta per attivita'**, in `sync()`,
  con i risultati in una tabella nuova `best_efforts (activity_id, distance_km,
  seconds, start_ts)`. Serve un salto di `logic_version` in `db.py`, con il suo
  commento come per le versioni 3 e 4, cosi' le attivita' gia' in cache vengono
  ricalcolate.
- La pagina `app_pages/records.py`, voce **Records** nella navigazione, icona
  `:material/trophy:`:
  - **Running**: una tabella con distanza, tempo migliore, passo, data e nome
    dell'attivita'. Il click sulla riga apre l'attivita' nella pagina Day, come
    fanno le tabelle delle attivita' nella Week;
  - **Per sport**: attivita' piu' lunga (km), piu' lunga (tempo), con piu'
    dislivello;
  - per le distanze di corsa, un grafico della migliore prestazione di ogni
    mese nel tempo, cosi' si vede se il tempo migliora.
- Le distanze che nessuna corsa copre (oggi forse la mezza maratona) non
  compaiono. Niente righe vuote.

## Vincoli

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Passo in `mm:ss /km`, tempi in `h:mm:ss`: le durate portano il proprio
  formato (vedi il commento in cima a `period_page.py`).
- Non toccare le pagine esistenti, tranne la voce di navigazione in `app.py`.

## Rischi

- `distance_km` dal GPS ha salti: un buco di segnale puo' produrre un "1 km in
  2 minuti". Scartare i tratti con un passo sotto i 2:30 /km, e scriverlo nel
  commento.
- Il salto di `logic_version` fa rileggere tutti i file FIT al primo avvio:
  qualche minuto, una volta sola. Scriverlo nel commento del salto.
- Per la bici le distanze classiche servono meno: meglio la potenza migliore
  su 5 e 20 minuti, ma solo se `power` c'e'. Va controllato quante attivita' ce
  l'hanno, e se sono poche la bici resta fuori da questo todo.

## Verifica

1. Il miglior 5 km non e' piu' lento del miglior 5 km trovato a mano con una
   query sulla corsa piu' veloce di almeno 5 km.
2. Nessun record ha un passo sotto i 2:30 /km.
3. Il migliore 1 km e' piu' veloce, al km, del migliore 5 km, e questo del
   migliore 10 km.
4. Il click su un record apre la sua attivita' nella pagina Day.
5. Dopo il salto di versione, `sync()` ricostruisce una volta sola; al secondo
   avvio non rilegge niente.
6. `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
