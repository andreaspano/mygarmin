---
status: done
---

# Week: coerenza dei nomi e costo dei rerun

Rifiniture della pagina Week dopo il riordino (todo 02) e i grafici adattivi
(todo 03). Qui non si sposta niente: si rende coerente quello che si legge e si
smette di rifare lavoro inutile a ogni interazione.

Work:

- **Un nome per grandezza.** Il dislivello oggi si chiama in quattro modi:
  `D+` (titolo grafico, L480), `D+ (m)` (intestazione tabella), `Elevation`
  (metrica scheda, L563), `Elevation gain (m)` (`activity_table.py:54`).
  "Activities" indica tre cose diverse: una metrica (L559), un sottotitolo
  (L571) e un'intestazione di colonna. Scegliere una convenzione e applicarla
  su tutta la pagina.
- **Un posto per le unita'.** Oggi sono tre convenzioni in una pagina sola:
  nell'intestazione in tabella ("Distance (km)"), nel valore nelle schede
  ("12.3 km"), nell'asse nei grafici ("km"). Decidere quale vale dove e essere
  conseguenti — non serve che sia la stessa ovunque, serve che sia una regola.
- **Nomi degli sport.** `cross_country_skiing` nelle tabelle e nel multiselect
  di Activities, `cross country skiing` nelle checkbox (L415) e nel titolo
  delle schede (L557), il grezzo nel dettaglio (`activity_detail.py:95`). Mai
  capitalizzati, benche' `profile.py:25` stabilisca gia' una convenzione con
  `CAPITALIZE_KEYS`. Uniformare, riusando quella convenzione.
- **Controllo di selezione sport** (L405-419). Tre problemi distinti:
  - le chiavi (`plot_sport_{sport}`, `plot_sport_total`) sono globali e non
    legate al periodo, a differenza della tabella (`weekly_{period_key}`) e dei
    grafici (`charts_{period_key}`): se uno sport esce dal range il suo widget
    non viene disegnato, Streamlit ne scarta lo stato e al rientro torna
    silenziosamente acceso;
  - "Total" sembra uno sport come gli altri ma e' un'altra cosa (una serie, non
    un filtro) ed e' un **controllo morto** quando lo sport selezionato e' uno
    solo, perche' la serie Total non viene proprio creata (L131, L295): si
    clicca e non succede niente, senza spiegazione;
  - che quel filtro valga **solo per i grafici** e non per le tabelle e' scritto
    unicamente in un commento del sorgente (L408).
  Portare la fila di checkbox a `st.pills` in multi-selezione (o allinearla al
  `st.multiselect` che `activities.py:32-37` usa per lo stesso concetto),
  separare "Total" come toggle a se', legare le chiavi al periodo e dire
  nell'interfaccia cosa filtra.
- **Costo dei rerun.** `_activities()` (L66-67) chiama `list_activities()`, che
  a sua volta chiama `sync()` (`db.py:279-289`): scansione della directory di
  export, apertura SQLite, parsing FIT dei file nuovi. Succede a **ogni** rerun,
  cioe' a ogni spunta di casella e a ogni click di riga. In tutto il repo
  `@st.cache_data` compare una volta sola (`activity_table.py:59`, su
  `sport_icons`). Metterla dove serve, con un `ttl` sensato, ricordando la
  regola: si mette in cache il caricamento dei dati, non i filtri che ci
  girano sopra.
- **Chiavi di sessione non qualificate**: `_prev_chart_week`,
  `_prev_table_week`, `_week_source` (L510-512) non hanno il suffisso del
  periodo. Cambiando intervallo i widget si azzerano ma la memoria no, quindi
  il primo giro dopo il cambio confronta contro settimane del periodo
  precedente.
- **Pulizia**:
  - `from pathlib import Path` inutilizzato in `activities.py` e in
    `activity_detail.py` (in `week.py` e' gia' stato tolto);
  - `summary_area` (L402) non contiene la tabella di riepilogo ma le schede per
    sport: nome fuorviante per chiunque riordini la pagina;
  - `page_title="Activities"` in `app.py:9` vale per tutte e tre le pagine: la
    scheda del browser dice "Activities" anche stando su Week o Profile;
  - il separatore nei sottotitoli e' un trattino ASCII in `week.py` (L542,
    L571) e un trattino lungo in `activity_detail.py:95`.

Vincoli:

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Rinominare le etichette non deve cambiare i dati ne' le chiavi dei
  `column_config`: una chiave sbagliata viene ignorata in silenzio e la colonna
  esce grezza (gia' successo come rischio nel todo 01).
- La cache non deve impedire di vedere attivita' nuove: se il `ttl` e' lungo,
  serve un modo di forzare l'aggiornamento, oppure il `ttl` va corto.

Rischi:

- Cambiare il widget di selezione sport cambia anche lo stato in sessione: le
  vecchie chiavi `plot_sport_*` restano orfane nelle sessioni aperte.
- Mettere in cache `list_activities` cambia quando l'app vede i file nuovi: e'
  un comportamento visibile, non solo una prestazione. Se il compromesso non e'
  ovvio, chiedere invece di deciderlo da soli.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. Percorrere la pagina dall'alto in basso e controllare che ogni grandezza
   abbia un nome solo e le unita' seguano la regola scelta. Stessa cosa sulla
   pagina Activities, che condivide le tabelle.
2. Cambiare periodo in modo che uno sport esca e rientri: la sua selezione non
   deve riaccendersi da sola.
3. Con un solo sport selezionato: "Total" non deve essere un controllo che non
   fa niente senza dirlo.
4. Misurare il tempo di risposta di un click di riga prima e dopo la cache.
5. Toccare un file nuovo nell'albero di export e verificare che l'app lo veda
   entro il `ttl` scelto.
6. Nessuna eccezione: `AppTest` sulla pagina piu' un giro nel browser, e un
   controllo che le tre pagine si aprano ancora.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

## Esito: implementato

Convenzioni scelte e applicate:

- **Un nome per grandezza.** Il dislivello e' "Elevation gain" ovunque (era
  `D+`, `D+ (m)`, `Elevation`, `Elevation gain (m)`). La durata e' "Duration"
  ovunque (era `Time` nella pagina Week e `Duration` nella tabella condivisa e
  nel dettaglio: sulla stessa pagina si leggevano tutti e due). "Activities"
  resta il conteggio (colonna e metrica); l'elenco si chiama "Activity list",
  cosi' le tre occorrenze non dicono piu' tre cose diverse.
- **Un posto per le unita'** (la regola sta scritta in testa a `week.py`):
  nell'intestazione in tabella, nel valore nelle schede, nel titolo dell'asse
  nei grafici. L'unica eccezione dichiarata sono le durate "08:28", che
  portano il formato con se'. Correzione trovata applicandola: `Avg HR` nella
  tabella condivisa non aveva unita', ora e' `Avg HR (bpm)`.
- **Nomi degli sport**: un solo `sport_label()` in `activity_table.py`, che
  riusa la convenzione di `profile.py` (iniziale maiuscola). Passa di li'
  tutto: colonne `sport`/`sub_sport`, pills, schede, legenda dei grafici,
  sottotitolo del dettaglio, opzioni del multiselect di Activities. I dati
  restano con le chiavi, si cambia solo quello che si legge.
- **Trattini**: quello lungo separa le frasi nei sottotitoli (come faceva gia'
  `activity_detail.py`), quello medio gli intervalli di data. `activity_report.py`
  non e' stato toccato: scrive nei report, e cambiarlo cambierebbe file gia'
  prodotti.

Controllo di selezione sport:

- `st.pills` in multi-selezione al posto della fila di checkbox, "Total"
  separato come toggle, e una didascalia che dice cosa filtra ("Charts only").
- Il toggle "Total" si **disabilita** con un solo sport, con un `help` che
  spiega perche': non e' piu' un controllo che si clicca senza effetto.
- **Le chiavi per periodo da sole non bastavano**, ed e' la scoperta del giro:
  Streamlit scarta lo stato dei widget che un giro non ha disegnato, quindi
  legando la chiave al periodo il problema si spostava soltanto (tutta la fila
  si riaccendeva a ogni cambio di intervallo). Quello che l'utente spegne si
  ricorda in `_week_sports_off`, che non appartiene a nessun widget e quindi
  nessuno ripulisce. Stesso trattamento per il toggle del totale.

Costo dei rerun:

- `data.load_activities()` (nuovo modulo) mette `@st.cache_data(ttl=60)`
  davanti a `list_activities`. Il decoratore sta li' e non su `list_activities`
  perche' quella la usa anche `training-activity-reports`, che gira fuori da
  Streamlit.
- ttl corto invece di un pulsante di aggiornamento, come consentito dal
  vincolo. Misurato: su albero gia' sincronizzato il risparmio e' modesto
  (3ms -> 0.3ms a rerun, perche' i 125 file sono gia' in SQLite); dove conta
  davvero e' quando c'e' da fare il parsing FIT, che su quattro file misurava
  2.8s.

Chiavi di sessione: `_prev_chart_week`, `_prev_chart_weeks`, `_prev_table_week`
e `_week_source` portano ora il suffisso del periodo.

Pulizia: tolti i due `from pathlib import Path` inutilizzati; `page_title` e'
"Training" invece di "Activities". `summary_area` non esisteva piu': il todo 02
l'aveva gia' rinominato in `table_area`, che contiene davvero la tabella dei
totali.
