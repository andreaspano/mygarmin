---
status: to commit
---

# Recovery: una pagina con i dati di recupero

L'app mostra solo le attivita' (Day, Week, Month). I dati di salute che dicono
come il corpo sta reggendo il carico (HRV, frequenza a riposo, sonno, training
readiness, body battery) esistono gia' su disco, ma li legge solo il report di
forma (`training.garmin.fitness_status`). Nell'app non si vedono.

Qui si aggiunge una pagina **Recovery** con l'andamento giornaliero di quei
valori. Deve far vedere a colpo d'occhio episodi come quello del 19-21
settembre 2026: giro in bici e corsa in salita uno dopo l'altro, readiness a 28
e body battery a 5 il 21, rientro in due giorni.

## Dati, verificato

Stanno in `DATA_DIR/health/<endpoint>/<YYYY-MM-DD>.json`, un file per giorno e
per endpoint (vedi `garmin/health.py`, `DAILY_ENDPOINTS`). I campi da usare,
controllati sul 2026-09-21:

| grandezza | file | campo |
|---|---|---|
| HRV notturno | `hrv` | `hrvSummary.lastNightAvg` (45) |
| HRV media 7 gg | `hrv` | `hrvSummary.weeklyAvg` (47) |
| stato HRV | `hrv` | `hrvSummary.status` ("BALANCED") |
| FC a riposo | `resting_heart_rate` | `allMetrics.metricsMap.WELLNESS_RESTING_HEART_RATE[0].value` (53.0) |
| ore di sonno | `sleep` | `dailySleepDTO.sleepTimeSeconds` (26040) |
| punteggio sonno | `sleep` | `dailySleepDTO.sleepScores.overall.value` (53) |
| readiness | `training_readiness` | **lista**, vedi sotto (28) |
| body battery | `stats` | `bodyBatteryHighestValue` / `bodyBatteryLowestValue` (47 / 5) |

`training_readiness` e' una lista con piu' misure al giorno: il 21 ce ne sono
due, 28 al risveglio (`inputContext == "AFTER_WAKEUP_RESET"`) e 26 dopo
l'allenamento (`"AFTER_POST_EXERCISE_RESET"`). Si prende **quella del
risveglio**: e' il numero che dice come si parte la mattina, ed e' uno solo per
giorno. Se manca, si prende la prima della giornata.

**Oggi su disco c'e' solo un mese** (dal 2026-08-26 al 2026-09-26, 32 giorni):
i file li scarica solo `fitness_status`, che guarda gli ultimi 14 giorni. Le
attivita' partono invece da gennaio 2025. La pagina deve funzionare con quello
che c'e', e questo todo aggiunge il modo per scaricare lo storico (vedi Work),
**senza lanciarlo**.

## Work

- Un modulo `interface/health.py` con una funzione pura
  `load_health(data_dir) -> DataFrame`: una riga per giorno, una colonna per
  ogni grandezza della tabella sopra, `NaN` dove il file o il campo manca. Come
  per le attivita', il decoratore `st.cache_data` va su una funzione sottile in
  `data.py` e non sul loader (vedi il commento in cima a `data.py`: la CLI non
  deve portarsi dietro Streamlit).
- Ogni campo va letto in modo difensivo: i JSON di Garmin cambiano forma, e un
  giorno senza orologio al polso ha `null` al posto dei dizionari. Un campo che
  manca da' `NaN`, non un'eccezione.
- Una pagina `app_pages/recovery.py`, voce **Recovery** nella navigazione di
  `app.py` dopo Month, icona `:material/favorite:`.
- In cima, una fila di `st.metric` con i valori dell'ultimo giorno: readiness,
  HRV (con la media 7 gg come delta), FC a riposo, sonno (ore e punteggio). Il
  delta e' rispetto al giorno prima.
- Sotto, un grafico per grandezza, tutti con lo stesso asse x (giorni) e uno
  sopra l'altro: readiness, body battery (fascia fra minimo e massimo), HRV
  (punti notturni piu' linea della media 7 gg), FC a riposo, sonno (barre delle
  ore colorate dal punteggio).
- **Giorni di allenamento**: sotto ogni grafico, o come segni sull'asse x, i
  giorni con attivita', con il carico del giorno (minuti totali). Senza questo
  la pagina non spiega perche' un valore scende.
- Il periodo si sceglie con `filters.date_range()` e le scorciatoie, come nelle
  altre pagine. Il default e' **4 settimane**.
- Scaricare lo storico: una funzione `backfill_health()` in `training.garmin`
  che chiama `export_daily_health()` dalla prima attivita' (2025-01-01) a oggi,
  e un target `make backfill_health`. `export_daily_health` salta gia' i giorni
  presenti su disco e si puo' interrompere e rilanciare.
- Tenere aggiornati i dati: `update_activity` scarica solo le attivita'. Deve
  scaricare anche le metriche degli ultimi 3 giorni, riscaricando sempre quelle
  di oggi (`force_dates={today}`, come fa `build_fitness_status`).

## Vincoli

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Unita' come nel resto dell'app (vedi il commento in cima a `period_page.py`):
  nel titolo dell'asse, mai nella cella.
- Non toccare `period_page.py`, `db.py`, `fit.py`: i dati di salute non passano
  da SQLite. Con un file per giorno e poche centinaia di giorni, leggere i JSON
  e metterli in cache basta.
  (Superato dal todo 16, `16_health_db.md`: ora i JSON finiscono in una tabella
  `health_daily` dentro `activities.db`, una cache derivata da loro.)

## Rischi

- Lo storico completo sono circa 640 giorni x 9 endpoint, cioe' circa 5.800
  chiamate con 0.3 s di pausa: mezz'ora abbondante, e Garmin puo' rispondere
  "too many requests". Per questo il backfill e' un comando a parte, non parte
  da solo con `update_activity`.
- Leggere 9 JSON per giorno per 640 giorni sono circa 5.800 file aperti: con
  `st.cache_data` si fa una volta, ma va misurato. Se e' lento, si legge solo il
  periodo scelto.
- `sleep/*.json` pesa (dati minuto per minuto): leggerne solo `dailySleepDTO`
  non evita di caricare il file intero. Anche questo va misurato.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Con i dati di oggi (dal 26 agosto al 26 settembre 2026) il 21 settembre ha
   readiness 28, body battery minimo 5, HRV 45 (media 47), FC a riposo 53,
   sonno 7h14 con punteggio 53.
2. Le metriche in cima seguono l'ultimo giorno **del periodo scelto**, non
   quello di oggi: mettendo "To" al 21 settembre 2026 la riga si legge
   "Latest day with data: 21 Sep 2026" e mostra readiness 28 (-45), HRV 45 ms
   (-2 sulla media 7 gg), FC a riposo 53 bpm (+1), sonno 7h14 (-1.3 h),
   punteggio 53 (-29). I delta sono rispetto al 20 settembre, tranne quello
   dell'HRV che e' sulla sua media a 7 giorni.

   Ancorata a un giorno fisso e non "all'ultimo giorno" apposta: i file di
   salute si allungano a ogni `update_activity`, e una verifica sull'ultimo
   giorno scadrebbe da sola ogni volta. I numeri sono quelli della misura del
   risveglio, come dice il Work.
3. Il 19 e il 20 settembre risultano giorni di allenamento (bici 50 km, corsa
   al Mont Bre).
4. Un periodo scelto prima del 26 agosto 2026 mostra un messaggio ("No health
   data in this period"), non grafici vuoti ne' eccezioni.
5. Un giorno con un file mancante o con `null` lascia un buco nella linea, non
   uno zero.
6. Nessuna eccezione: `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity`, `make backfill_activity_names` ne' il
nuovo `make backfill_health`: chiamano l'API Garmin e scrivono nell'albero dati.

## Esito: implementato (atodo, 2026-09-27)

Tutto il Work, e tutte e sei le verifiche passano. La 2 e' stata riscritta:
vedi la decisione qui sotto, presa con l'opzione (a) il 2026-09-27.

**Expected-result change**, verifica 2 (risolto): "le metriche in cima mostrano
il 26 settembre: readiness 71, FC a riposo 49, sonno circa 6.5 h con punteggio
79" -> mostravano **il 27 settembre: readiness 79, FC a riposo 47, sonno 9h35
con punteggio 82**. Erano due cose diverse:

- **Il giorno.** Quando il todo e' stato scritto i file di salute su disco
  arrivavano al **22 settembre**, non al 26 (l'ho controllato sulle date di
  modifica). Dal 23 al 27 li ha scaricati `training-fitness-status`, lanciato
  il 27 settembre. La pagina mostra l'ultimo giorno con almeno una misura, come
  chiede il Work, e quell'ultimo giorno ora e' il 27. La verifica invecchia da
  sola a ogni `update_activity`: se serve un riscontro stabile conviene
  riscriverla sul 21 settembre, che e' gia' la verifica 1 e non si muove.
- **Il numero della readiness.** Anche guardando il 26 settembre, il valore non
  sarebbe 71 ma **74**. Quel giorno Garmin ha registrato tre misure: 74 al
  risveglio (`AFTER_WAKEUP_RESET`, 05:59), 75 da un aggiornamento in corsa
  (`UPDATE_REALTIME_VARIABLES`, 07:23) e 71 dopo l'allenamento
  (`AFTER_POST_EXERCISE_RESET`, 17:14). Il 71 della verifica e' la misura dopo
  l'allenamento, cioe' proprio quella che il Work dice di **non** prendere
  ("Si prende quella del risveglio"). Sul 21 settembre il todo applica la
  regola giusta (28 al risveglio, non 26 dopo l'allenamento), quindi sembra una
  svista solo qui. E' lo stesso inciampo del todo 08.

**Deciso il 2026-09-27 con l'opzione (a)**: verifica 2 riscritta sopra con i
numeri del risveglio e ancorata al 21 settembre, mettendo "To" a quel giorno
invece di guardare l'ultimo giorno scaricato. Cosi' controlla anche una cosa in
piu' della versione vecchia, cioe' che le metriche seguano il periodo scelto e
non la data di oggi. Misurata dopo la riscrittura: 28 (-45), 45 ms (-2 sulla
media), 53 bpm (+1), 7h14 (-1.3 h), 53 (-29). Le altre due opzioni erano (b)
tenere l'ultimo giorno e riscrivere i numeri a ogni giro, e (c) mostrare
l'ultima misura invece di quella del risveglio, contro il Work.

Le altre cinque verifiche, per riferimento:

1. **Passa.** Il 21 settembre: readiness 28, body battery minimo 5, HRV 45
   (media 47), FC a riposo 53, sonno 7h14 (26.040 s) con punteggio 53.
3. **Passa.** Il 19 settembre risulta giorno di allenamento con 229 minuti
   (bici, 50,4 km) e il 20 con 114 (corsa, 7,9 km): sono le due barre piu' alte
   della riga in fondo, proprio sotto il crollo della readiness del 21.
4. **Passa.** Dal 1 giugno al 1 luglio 2026 compare "No health data in this
   period.", nessun grafico e nessuna eccezione.
5. **Passa.** Dal 1 all'8 settembre 2026 mancano HRV, sonno, body battery e FC
   a riposo (i JSON hanno `null`): le linee si spezzano e riprendono dopo, senza
   punti a fondo scala. Ci e' voluto un tentativo: forzare `invalid=None` in
   Vega-Lite vuol dire "mostrali lo stesso", e quei sette giorni finivano
   appoggiati sul minimo dell'asse (un battito a riposo di 45 e un HRV di 40 mai
   misurati). Il comportamento di default delle linee
   (`break-paths-filter-invalid-values`) e' invece esattamente il buco chiesto
   qui.
6. **Passa.** `AppTest` su tutte e cinque le pagine: nessuna eccezione. Nel
   browser a 1440px la pagina non scorre in orizzontale e i sei pannelli stanno
   nel contenitore (930px su 1074 disponibili).
