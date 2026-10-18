---
status: todo
---

# Endurance score, hill score e soglia del lattato

La card Fitness della Day in React (todo 37) prende tre misure di Garmin che
oggi non si scaricano: **endurance score**, **hill score** e la **soglia del
lattato** della corsa (frequenza e passo).

Si scaricano con la salute di ogni giorno, si leggono in `health_daily` e
l'API le passa alla Day. Streamlit e i report non cambiano.

Da fare dopo il todo 37: questo todo riempie la sua card Fitness.

## Decisioni

Prese con Andrea il 2026-10-18:

- **Tre endpoint giornalieri in piu'** in
  `src/training/garmin/health.py`, `DAILY_ENDPOINTS`, con un file per
  giorno come gli altri nove: `health/endurance_score/<giorno>.json`,
  `health/hill_score/<giorno>.json`,
  `health/lactate_threshold/<giorno>.json`. Le chiamate sono di
  `garminconnect` 0.3.13, gia' dipendenza: `get_endurance_score(d)`,
  `get_hill_score(d)`, `get_lactate_threshold(latest=False, start_date=d,
  end_date=d)`. Un file per giorno tiene il ripristino di
  `export_daily_health` (salta i file gia' su disco) e il refresh degli
  ultimi giorni di `update_activity` senza codice nuovo.
- **Lo storico lo scarica Andrea**, dopo il merge, con `make
  backfill_health`. I giorni gia' scaricati hanno gia' i nove file vecchi,
  quindi chiede solo i tre nuovi: dal 2025-01-01 sono circa 660 giorni,
  cioe' circa 2.000 chiamate.
- **I report non cambiano.** `garmin/fitness_status.py` legge tutti i
  `DAILY_ENDPOINTS`: deve continuare a leggere solo i nove di prima, con una
  tupla esplicita, altrimenti l'input dell'agente del report cambia.
- **La soglia del lattato** in Fitness e' quella di Garmin (frequenza, passo
  in min/km, data in cui e' stata rilevata); senza un valore di Garmin si
  torna alla frequenza di soglia del FIT, come nel todo 37, con la sua data.
  Si mostra la data e non la variazione in 28 giorni: Garmin la aggiorna
  solo quando ne rileva una nuova.
- **Endurance e hill score**: il valore, il livello di Garmin (es.
  "Trained") se la risposta lo ha, e la variazione in 28 giorni come il
  VO2max.

## Work

### Prima di scrivere il parsing

- Il formato delle tre risposte non e' noto. Questo todo autorizza a
  chiamare i tre endpoint, e solo loro, per **due giorni**: il giorno prima
  di oggi e il 2025-01-15. Si scrivono in una cartella temporanea, non nella
  cartella dati. Da li' si decidono i campi; nei commenti del parser va un
  esempio ridotto della forma.

### Python

- `src/training/garmin/health.py`: i tre endpoint in `DAILY_ENDPOINTS`;
  il commento che parla di nove file dice dodici.
- `src/training/garmin/fitness_status.py`: la tupla dei nove endpoint di
  prima.
- `src/training/interface/health.py`: le colonne nuove in `COLUMNS` (e in
  `TEXT_COLUMNS` quelle di testo): `endurance_score`, `endurance_level`,
  `hill_score`, `hill_level`, `lt_heart_rate`, `lt_speed_kmh`, `lt_date`. I
  nomi esatti possono cambiare dopo aver visto le risposte, l'idea no. NULL
  vuol dire "non lo sappiamo", come `_dig()`. Le docstring che dicono "nove
  file" si aggiornano.
- `src/training/interface/health_db.py`: `HEALTH_LOGIC_VERSION` da "1" a
  "2", con la riga di storia: `health_daily` si rifa' dai JSON al primo
  accesso (secondi, non i minuti del rebuild dei FIT).
- `src/training/interface/daily_data.py`: `fitness_on(health, day)` (todo
  37) aggiunge `endurance`, `hill` e `lactate_threshold`.

### API

- `models.py`: i campi nuovi in `Fitness`, con descrizioni.
- `make frontend_types` rigenera `frontend/src/api/schema.ts`.

### Frontend

- `components/FitnessCard.tsx`: VO2max, Endurance score, Hill score,
  Lactate threshold (frequenza e passo, con la data; o la frequenza di
  soglia del FIT se Garmin non ce l'ha). "–" per un valore che manca.

### Docs

- `README.md`: le tre misure nella sezione della salute scaricata e nella
  card Fitness; `make backfill_health` per lo storico.

## Vincoli

- Nessuna dipendenza nuova.
- Solo i tre endpoint, solo i due giorni di prova, mai nella cartella dati:
  `make update_activity`, `make backfill_health` e `make backfill` li lancia
  Andrea.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Il frontend non fa conti.

## Rischi

- **Risposte vuote o mancanti** nei giorni prima che l'orologio calcolasse
  questi punteggi: devono dare NULL, non errori, e la card "–".
- **Range invece che giorno**: se un endpoint risponde con piu' giorni anche
  chiedendone uno, si tiene solo quello chiesto.
- **Hill score** cambia poco con corse quasi tutte in piano: e' atteso.
- **Durata dell'aggiornamento**: ogni `update_activity` fa tre chiamate in
  piu' per giorno rinfrescato (tre giorni): una decina di secondi.

## Verifica

1. `uv run python -c "import training; from training.interface import health, health_db, daily_data"`.
2. Sui due giorni di prova, in una copia temporanea della cartella `health`
   con i tre file nuovi: `_day_row` legge i valori del giorno recente e da'
   NULL su quello del 2025 se Garmin non aveva il dato.
3. `HEALTH_LOGIC_VERSION` 2: `sync_health()` sulla copia rifa' la tabella
   senza errori.
4. `make daily_data DAY=<giorno di prova>` da' lo stesso JSON di prima del
   todo (salvarlo prima di cominciare). `build_fitness_status` legge ancora
   nove endpoint.
5. `TestClient`: `GET /api/daily/<giorno di prova>` ha `fitness.endurance`,
   `fitness.hill` e `fitness.lactate_threshold`.
6. `cd frontend && npm run build`; `npm run gen:api` e
   `git diff --exit-code frontend/src/api/schema.ts`.
7. Nel browser, sulla copia: la card Fitness con le quattro misure sul
   giorno recente, "–" dove manca. Screenshot nel report finale.
8. La cartella dati vera non ha cartelle `endurance_score`, `hill_score` o
   `lactate_threshold`; tutti i server avviati si fermano.
