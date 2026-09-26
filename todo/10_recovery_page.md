---
status: todo
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
2. Le metriche in cima mostrano il 26 settembre: readiness 71, FC a riposo 49,
   sonno circa 6.5 h con punteggio 79.
3. Il 19 e il 20 settembre risultano giorni di allenamento (bici 50 km, corsa
   al Mont Bre).
4. Un periodo scelto prima del 26 agosto 2026 mostra un messaggio ("No health
   data in this period"), non grafici vuoti ne' eccezioni.
5. Un giorno con un file mancante o con `null` lascia un buco nella linea, non
   uno zero.
6. Nessuna eccezione: `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity`, `make backfill_activity_names` ne' il
nuovo `make backfill_health`: chiamano l'API Garmin e scrivono nell'albero dati.
