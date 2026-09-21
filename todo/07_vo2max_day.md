---
status: to commit
---

# VO2max: leggerlo dai file FIT e mostrarlo nella pagina Day

La stima del VO2max che fa l'orologio **c'e' gia' nei file FIT**, ma nessuno la
legge: `fit.py` guarda solo i messaggi `session` e `record`, e la tabella
`activities` della cache SQLite non ha una colonna per lei. Oggi il VO2max
compare solo nei report di `fitness-status`, che lo chiedono all'API Garmin
(rete, e solo come intero). Leggendolo dai file si ha tutto lo storico, in
locale, con un decimale in piu'.

Qui lo si legge, lo si mette in cache e lo si mostra nella pagina **Day**
(tabella delle attivita' e scheda di dettaglio). L'andamento nel tempo sulla
pagina Week e' il todo 08, che parte da quello che questo lascia pronto.

## Cosa c'e' nei file, verificato

Ogni attivita' porta un messaggio non documentato, il **numero 140** (lo scrive
il motore Firstbeat dell'orologio). Il **campo 7** e' il VO2max come intero
scalato:

```
VO2max = raw * 3.5 / 65536          es. 753282 -> 40.2 ml/kg/min
```

La formula e' stata controllata contro i valori che l'API Garmin ha dato a
`fitness-status` (`vO2MaxValue`, in `summary/01.daily/2026-09-14.md`):

| data | dal file FIT | dall'API |
|---|---|---|
| 1 set | 40.0 | 40 |
| 2 set | 40.0 | 40 |
| 4 set | 39.5 | 39 |
| 6 set | 39.4 | 39 |
| 11 set | 39.4 | 39 |
| 13 set | 40.1 | 40 |

Combaciano: il file tiene un decimale, l'API sembra troncare all'intero.

Scansione di tutti i 125 file (settembre 2026): **78** portano un valore, dal
3 gennaio 2025 al 16 settembre 2026, fra 36.6 e 44.6. Per sport: running 21 su
22, cross_country_skiing 19 su 19, cycling 26 su 43, hiking 7 su 36, walking 3
su 3, training 2 su 2. L'unica corsa senza valore e' quella del 20 settembre
(sub_sport `navigate`, +866 m): li' il campo vale 0, cioe' "nessuna stima".

**Attenzione a cosa significa il valore.** Non e' sempre una stima fatta *su
quella* attivita': lo portano anche sci e camminate, e il 14 settembre corsa e
camminata dello stesso giorno hanno tutte e due 40.0 esatto. La lettura piu'
ragionevole e' che il campo 7 sia il VO2max corrente dell'orologio alla fine
dell'attivita': le corse che si qualificano lo aggiornano, tutto il resto lo
trascina. E' una deduzione dai dati, il messaggio non e' documentato. Per un
andamento nel tempo va benissimo; come "stima di questa uscita" vale solo per
le corse.

Work:

- **`fit.py`**: in `load_activity_summary()` leggere anche il messaggio 140 e
  aggiungere `vo2max` al dizionario. Si legge dallo stesso oggetto `FitFile` gia'
  aperto per `session` (`fit.get_messages(140)`, campo con `def_num == 7`):
  fitparse il file lo ha gia' letto tutto, quindi non costa un secondo parsing.
  `raw` a 0 o assente -> `None`. Per prudenza, `None` anche fuori da un
  intervallo plausibile (10-100): il campo non e' documentato, e un numero
  assurdo in tabella e' peggio di una cella vuota.
- **`db.py`**: colonna `vo2max REAL` in `activities` (`_SCHEMA`,
  `_insert_activity`). I 125 file gia' in cache vanno riletti una volta: e' il
  caso per cui esiste `LOGIC_VERSION`. Portarla da "2" a "3" e lasciare che
  `sync()` faccia il `rebuild()` da solo al primo avvio (lo fa gia' quando la
  versione salvata non combacia). Non scrivere una migrazione a parte e non
  toccare `activities.db` a mano.
- **Tabella delle attivita'** (`activity_table.py`): una colonna `vo2max` in
  `ACTIVITY_COLUMNS` e in `ACTIVITY_COLUMN_CONFIG`, dopo `Elevation gain (m)`.
  Intestazione `VO2max (ml/kg/min)`, un decimale, allineata a destra come le
  altre, cella vuota dove il valore manca. Con un `help` che dica cos'e'
  davvero il numero: la stima dell'orologio alla fine dell'attivita', che le
  corse aggiornano e le altre attivita' si portano dietro. La tabella e'
  condivisa: la colonna compare anche nell'elenco "Activity list" della pagina
  Week, ed e' giusto cosi', le due tabelle devono leggersi come una sola.
- **Scheda di dettaglio** (`activity_detail.py`, la riga di metriche a L95-106):
  una quinta metrica `VO2max`, con il valore a un decimale e l'unita' nel
  valore (`40.2 ml/kg/min`), `-` quando manca. Le colonne passano da quattro a
  cinque.
- **Le regole del todo 04 valgono anche qui**: un nome solo, `VO2max`; unita'
  nell'intestazione in tabella, nel valore nelle schede.

Fuori da questo todo: l'andamento nel tempo (todo 08) e qualunque stima
calcolata da noi (estrapolazione FC-velocita'). Qui si mostra solo il numero
dell'orologio.

Vincoli:

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Nessuna dipendenza nuova: fitparse c'e' gia' e il messaggio 140 lo legge.
- Rinominare o aggiungere etichette non deve toccare le chiavi dei
  `column_config`: la chiave e' il nome della colonna del DataFrame, `vo2max`, e
  una chiave sbagliata viene ignorata in silenzio.
- `training-activity-reports` usa `list_activities()` fuori da Streamlit: deve
  continuare a girare, colonna nuova compresa.
- La cache `load_activities()` (ttl 60s) resta com'e'.

Rischi:

- **Il primo avvio dopo la modifica rifa' tutta la cache**: 125 file a ~1s
  l'uno, due o tre minuti in cui la pagina sembra ferma. Succede una volta.
  Scriverlo nel report, perche' Andrea non pensi a un blocco.
- Il messaggio 140 non e' documentato: un aggiornamento del firmware potrebbe
  spostare il campo. Per questo l'intervallo plausibile, e per questo il
  commento in `fit.py` deve dire da dove viene la formula e contro cosa e' stata
  controllata.
- `rebuild()` cancella e ricrea `activities.db`, che sta nell'albero dei dati:
  e' la pipeline che lo fa, non una scrittura a mano, ma va lasciato fare a lei.
- La tabella e' gia' larga: una colonna in piu' la allunga ancora, e a finestre
  strette scorre al suo interno. Controllare che non spinga fuori pagina niente.
- Cinque metriche nella scheda invece di quattro: controllare a 1280px che i
  valori non vadano a capo o si taglino.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. **La decodifica**: dopo il rebuild, `vo2max` vale 40.2 per l'attivita'
   24386941712 (16 set 2026), 40.0 per la 24360293923 (14 set) e `NULL` per la
   24429927755 (20 set, la corsa `navigate`).
2. **La copertura**: 78 attivita' su 125 con un valore, 21 corse su 22.
3. Il rebuild parte da solo al primo `list_activities()` e **una volta sola**:
   al secondo avvio la cache non viene rifatta.
4. Pagina Day: la colonna `VO2max (ml/kg/min)` c'e', con 40.2 sulla corsa del
   16 settembre e la cella vuota su quella del 20; il `help` compare passando
   sull'intestazione.
5. Scheda di dettaglio: la corsa del 16 settembre mostra `40.2 ml/kg/min`,
   quella del 20 mostra `-`.
6. Pagina Week: l'elenco "Activity list" ha la stessa colonna.
7. `make activity_reports` gira senza errori e senza scrivere report nuovi.
8. Nessuna eccezione: `AppTest` sulle tre pagine piu' un giro nel browser, a
   1440 e a 1280px.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

## Esito: implementato

Il VO2max dell'orologio si legge dai file FIT (`fit._vo2max()`, messaggio 140,
campo 7), sta in cache (`activities.vo2max`) e si vede nella pagina Day: colonna
`VO2max (ml/kg/min)` in tabella e quinta metrica nella scheda di dettaglio.

Verificato:

- **Decodifica**: 40.2 per la 24386941712 (16 set), 40.0 per la 24360293923
  (14 set), `NULL` per la 24429927755 (20 set, `navigate`). Controllata prima
  sui file, poi di nuovo nella cache dopo il rebuild.
- **Copertura**: 78 attivita' su 125 con un valore, 21 corse su 22, fra 36.6 e
  44.6: gli stessi numeri della scansione fatta a mano.
- **Rebuild**: partito da solo al primo `list_activities()` (versione "2" ->
  "3"), **134 secondi**, una volta sola: la seconda chiamata ha impiegato 5ms e
  la versione salvata e' rimasta "3". La tabella `records` e' stata rifatta
  anche lei (557.172 righe).
- **Pagina Day**: l'intestazione `VO2max (ml/kg/min)` compare scorrendo la
  tabella a destra; la scheda della corsa del 16 settembre mostra
  `40.2 ml/kg/min`, quella del 20 mostra `-`. A 1440 e a 1280px le cinque
  metriche stanno su una riga, senza andare a capo ne' tagliarsi.
- **Pagina Week**: l'elenco "Activity list" ha la stessa colonna.
- `make activity_reports` gira e non scrive report nuovi; nessuna eccezione con
  `AppTest` sulle tre pagine ne' nel browser; log del server pulito.

Da sapere:

- **La colonna e' l'ultima, e a 1440px non si vede senza scorrere la tabella**:
  le colonne sommano ~1.500px e il contenitore ne ha 980. Era gia' cosi' per
  `Elevation gain (m)`. Il todo la voleva dopo quella, ed e' li'; se deve stare
  in vista va spostata piu' a sinistra o vanno strette le altre.
- Il `help` sull'intestazione non e' stato provato passandoci sopra col mouse
  (la tabella e' disegnata su canvas): e' un parametro standard di
  `column_config`, lo stesso testo sta anche sulla metrica della scheda.
- **Finche' questo ramo non e' unito a `main`, far girare l'app dal codice di
  `main` rifa' la cache all'indietro** (versione "3" -> "2", altri due minuti),
  e tornando qui la rifa' di nuovo in avanti. Dopo il merge non succede piu'.
