---
status: todo
---

# Week e Month: tempo per zona di frequenza cardiaca

Fino a settembre 2026 quasi tutte le corse sono state facili (FC media
127-135). Il piano dalla settimana del 28 settembre aggiunge una seduta veloce a
settimana, e la domanda diventa: la base resta facile per circa l'80%? Oggi
l'app mostra solo FC media e massima per attivita', che non bastano a
rispondere.

Qui si aggiunge alle pagine Week e Month il tempo passato in ciascuna delle
cinque zone di frequenza.

## Dati, verificato

- La FC secondo per secondo sta nella tabella `records` di `activities.db`
  (`heart_rate`, `ts_epoch`). Ce l'hanno **92 attivita' su 129**: le altre sono
  state registrate senza fascia o senza sensore, e per quelle non si puo' dire
  niente.
- **Le zone non sono salvate da nessuna parte.** `user/profile.yaml` non ha la
  FC massima. E il massimo osservato non e' affidabile: 205 in bici (quasi
  certamente un errore del sensore), 168 di corsa, 170 nello sci di fondo.

## Decisioni da prendere prima di partire

- **Da dove vengono le zone.** Proposta: una sezione `heart_rate` in
  `user/profile.yaml` con `max` e i quattro limiti fra le zone in bpm, scritti a
  mano copiandoli da Garmin Connect. Alternativa: leggerle da Garmin, se
  `garminconnect` espone le zone dell'utente. Va verificato, e sarebbe comunque
  un comando a parte che scrive nel file, non una chiamata all'avvio dell'app.
  In nessun caso si ricavano dal massimo osservato.

## Work

- Una funzione che, per ogni attivita', calcola i secondi in ogni zona:
  - ogni punto vale la differenza di `ts_epoch` con il punto seguente;
  - un intervallo **oltre 10 s** e' una pausa e non conta;
  - i punti con `heart_rate` nullo non contano.
- Il calcolo si fa in SQL (`CASE` sui limiti, `SUM` raggruppato per attivita')
  invece di caricare in pandas tutti i `records`, e si mette in cache in
  `data.py` come `load_activities()`. Non si salva in `db.py`: dipende dalle
  zone, che possono cambiare.
- In `period_page.py`, una sezione richiudibile **Heart rate zones** dopo le
  righe dei grafici, con lo stesso meccanismo delle altre (chiave propria,
  stato iniziale scritto nella chiave e non passato con `expanded=`,
  `on_change="rerun"`). Contiene:
  - barre impilate per periodo (settimana o mese), ore per zona, Z1 in basso;
  - la quota di Z1+Z2 sul totale del periodo scelto, come `st.metric`.
- Segue le pills degli sport come i volumi: si puo' guardare solo la corsa.
- Colori delle zone: una scala che va dal freddo al caldo, da Z1 a Z5. Le zone
  non sono sport e non usano `_SPORT_COLORS`.
- Le attivita' senza FC non spariscono in silenzio: nel tooltip, "n activities
  without heart rate".

## Vincoli

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Non toccare le righe di grafici che esistono, `CHART_ROWS`, ne' la larghezza
  fissa (`CHARTS_TOTAL_WIDTH`).
- Se `profile.yaml` non ha le zone, la sezione mostra un messaggio che spiega
  cosa aggiungere, e il resto della pagina funziona.

## Rischi

- `records` e' grande: il `GROUP BY` su tutte le attivita' va misurato. Se e'
  lento, conviene un indice o limitarsi alle attivita' del periodo.
- Le fasce da polso sbagliano nei primi minuti e sugli sforzi brevi: il
  risultato e' indicativo, e non va presentato con decimali.

## Verifica

1. Con le zone inserite, la somma dei minuti di un'attivita' e' uguale alla sua
   durata meno le pause, con una tolleranza del 2%.
2. La corsa lenta del 26 settembre 2026 (5.35 km, FC media 128) e' quasi tutta
   in Z1-Z2.
3. La corsa al Mont Bre del 20 settembre 2026 (FC max 168) ha tempo in Z4-Z5.
4. Spegnere la bici nelle pills cambia le barre.
5. Senza zone nel profilo: un messaggio, nessuna eccezione.
6. `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
