---
status: todo
---

# API di sola lettura (FastAPI) per la pagina Day

Primo passo del passaggio da Streamlit a un'app multiutente con piu'
sviluppatori (vedi "Contesto"). Oggi i dati arrivano alle pagine solo dentro
Streamlit: chi vuole scrivere un'altra interfaccia non ha niente a cui
chiedere "le attivita' di questa settimana" o "il grafico di questa corsa".

Qui si aggiunge un pacchetto `training.api`: un'app FastAPI che espone, in
sola lettura, tutto quello che serve alla pagina **Day**. Non si tocca
l'aspetto di nessuna pagina Streamlit, e non c'e' ancora nessun frontend
nuovo: e' lo strato su cui il frontend React si appoggera'.

I calcoli ci sono gia' e quasi tutti non dipendono da Streamlit (`db.py`,
`run_chart.py`, `daily_data.py`, `grade.py`, `health_db.py`). Restano dentro
moduli Streamlit due pezzi che l'API deve usare: la lettura delle zone
cardiache (`activity_detail._zone_settings`, copiata in
`daily_data._zones`) e la lettura del file di report
(`report_view.show_report`). Vanno portati fuori.

## Contesto: dove si va

Deciso con Andrea il 2026-10-08:

- il progetto diventa **multiutente** e con **piu' sviluppatori**;
- **backend FastAPI** sopra il pacchetto `training`, **frontend React**
  (TypeScript, Vite) in `frontend/`, nello stesso repo;
- il contratto fra i due e' l'**OpenAPI** che FastAPI genera: da li' si
  generano i tipi TypeScript, quindi le risposte hanno modelli dichiarati;
- **dati per utente**: una cartella dati per utente, con il suo
  `activities.db`. Niente Postgres per ora;
- i grafici restano in **Altair** e arrivano al browser come specifica
  Vega-Lite: non si riscrivono;
- **Streamlit resta acceso** finche' le pagine non sono migrate.

L'ordine dei lavori, un todo per passo (da scrivere quando il precedente e'
chiuso):

1. questo todo: l'API della Day;
2. suite di test e un piccolo dataset sintetico nel repo, per far girare
   l'app senza i dati di Andrea;
3. login e dati per utente (oggi `user/config.yaml` e' uno solo e si legge
   all'import);
4. la pagina Day in React, dal mockup;
5. API e pagine di Week, Month e Recovery (`period_page.py` va diviso in
   calcoli e disegno).

Restano da decidere prima di aprire ad altri: la lingua dei commenti
(italiano o inglese), la licenza, la guida per chi contribuisce.

## Decisioni

- **Sola lettura**: solo `GET`. Niente download da Garmin, niente scrittura
  di report.
- **Nessun login in questo todo**: per questo il server ascolta solo su
  `127.0.0.1`. Sono dati di salute, non vanno esposti in rete senza login.
- **Il punto in cui entrera' l'utente c'e' gia'**: ogni endpoint riceve un
  `UserContext` (cartella dati e cartella dei report) da una dipendenza
  FastAPI. Oggi la dipendenza rende sempre i valori di Andrea; con il login
  cambiera' solo lei.
- **Nomi dei campi uguali alle colonne** di `activities` e `records`
  (`total_distance_km`, `avg_heart_rate`, ...): chi legge l'API e il
  database non deve tradurre.
- **Orari locali senza fuso**, come nel database: `2026-10-07T12:28:00`.
- **Un valore che manca e' `null`**, mai `NaN` e mai `0`.
- **Il JSON del giorno resta com'e'**: `/api/daily/{day}` rende quello che
  rende `build_daily_data`, senza un modello dichiarato campo per campo. E'
  grande e ancora in movimento: tiparlo e' un lavoro a parte.
- **Il grafico in due forme**: i dati (`bins`, bande, pause), per chi lo
  vuole ridisegnare, e la specifica Vega-Lite gia' pronta, per chi lo vuole
  solo mostrare.

## Work

- **Dipendenze** (via `uv add`): `fastapi`, `uvicorn`, e `altair` scritto
  esplicitamente (oggi arriva solo perche' lo porta Streamlit, e l'API lo
  usa). Nel gruppo `dev`: `httpx`, che serve al `TestClient` della verifica.

- **`run_chart.py`**: funzione pubblica `zone_settings(activity) ->
  tuple[list[int] | None, int | None]`, i tetti di Z1-Z4 (da
  `hr_zone_bounds`, che nel database e' testo JSON) e la soglia. La usano
  `activity_detail.py` (al posto di `_zone_settings`) e `daily_data.py` (al
  posto di `_zones`): le due copie spariscono.

- **`interface/report_text.py`** (nuovo, senza Streamlit):
  `parse_report(path) -> list[tuple[str | None, str]]`, le sezioni di un
  report come (titolo, testo). E' la parte di `report_view.show_report` che
  legge il file: toglie le righe di intestazione (`_HEADER_PREFIXES`, che si
  sposta qui) e divide sulle righe `## `. Il testo prima della prima sezione
  ha titolo `None`. `report_view.show_report` la usa e tiene solo il
  disegno.

- **`src/training/api/`** (nuovo pacchetto):
  - `context.py`: `UserContext` (dataclass con `data_dir` e `summary_dir`)
    e la dipendenza `get_user_context()`. Oggi rende `config.DATA_DIR` e
    `<radice del repo>/summary`. La radice del repo si ricava dal file, come
    fa `config.CONFIG_PATH`: l'API non deve dipendere dalla cartella da cui
    si lancia (le pagine Streamlit usano `Path("summary/...")` relativo).
  - `cache.py`: le attivita' di una cartella dati, tenute 60 secondi.
    `list_activities()` chiama `sync()`, che scandisce la cartella di export:
    e' la stessa ragione di `interface/data.py`, che pero' usa la cache di
    Streamlit. Chiave la cartella dati, un lock attorno al caricamento
    (FastAPI serve gli endpoint sincroni su piu' thread), e si rende una
    copia del DataFrame.
  - `models.py`: i modelli pydantic delle risposte (sotto).
  - `app.py`: l'app (`app = FastAPI(title="Training API", ...)`) e gli
    endpoint, tutti sotto `/api`.

- **Endpoint**:
  - `GET /api/activities?start=YYYY-MM-DD&end=YYYY-MM-DD&sport=...` ->
    lista di `Activity`, dalla piu' recente. `end` di default oggi, `start`
    di default 27 giorni prima di `end`; `sport` ripetibile. Estremi
    compresi, sul giorno di `start_time`. `start` dopo `end`: 422.
    `Activity`: `activity_id`, `sport`, `sub_sport`, `start_time`,
    `activity_name`, `total_distance_km`, `total_time_min`,
    `total_ascent_m`, `total_descent_m`, `avg_speed_kmh`,
    `equiv_speed_kmh`, `avg_heart_rate`, `max_heart_rate`,
    `total_calories`, `vo2max`, `aerobic_te`, `anaerobic_te`. Non si
    espongono `path` e `parsed_at`.
  - `GET /api/activities/{activity_id}` -> `ActivityDetail`: i campi di
    `Activity` piu' `hr_zone_bounds`, `threshold_hr` e `effect_seconds`
    (`low_aerobic_s`, `high_aerobic_s`, `anaerobic_s`, da
    `run_chart.effects`), che e' `null` quando `has_effects` e' falso o
    mancano i battiti. Attivita' sconosciuta: 404.
  - `GET /api/activities/{activity_id}/chart` -> `ChartData`: `bins` (le
    righe di `run_chart.bins`: `start`, `end`, `minute`, `hr`, `speed`,
    `equiv`, `slope_pct`, `slope_deg`), `zone_bands` (le righe di
    `run_chart.zone_bands`: `start`, `end`, `zone`, `hr`; lista vuota senza
    zone), `pauses` (`start`, `end`, da `run_chart.pauses`),
    `hr_zone_bounds`, `threshold_hr`. Senza record: liste vuote, non 404.
  - `GET /api/activities/{activity_id}/chart/vega?theme=light|dark` -> la
    specifica Vega-Lite di `run_analysis_chart(...)` (`.to_dict()`), o 404
    se la funzione rende `None`.
  - `GET /api/activities/{activity_id}/route?max_points=2000` -> `Route`:
    `points`, lista di `[lat, lon]` dai record con posizione, in ordine. Se
    sono piu' di `max_points` se ne prende uno ogni N, tenendo sempre il
    primo e l'ultimo. Senza posizione: lista vuota.
  - `GET /api/daily/{day}` -> `build_daily_data(day, data_dir)`. Giorno nel
    futuro: 422, come rifiuta la CLI.
  - `GET /api/reports/daily/{day}` -> `Report`: `day` e `sections`, lista
    di `{title, body}` da `parse_report` sul file
    `<summary_dir>/01.daily/<day>.md`. Senza file: 404. Solo il file con il
    nome esatto del giorno, come nella pagina Day.

- **`Makefile`**: target `api`:
  `uv run uvicorn training.api.app:app --host 127.0.0.1 --port 8000 --reload`.

- **`README.md`**: una sezione "API" breve: come si lancia, dove sta la
  documentazione (`/docs`), che e' in sola lettura e solo locale.

## Vincoli

- Dipendenze nuove: solo quelle elencate sopra.
- `import training.api.app` non deve importare Streamlit.
- Nessuna chiamata a Garmin. Nessuna scrittura in `summary/` o nella
  cartella dati, a parte l'aggiornamento di `activities.db` che
  `list_activities()` fa gia' oggi.
- Le pagine Streamlit si vedono e si comportano come prima.
- Commenti in italiano senza accenti. Titoli, descrizioni e nomi
  nell'OpenAPI in inglese: sono l'interfaccia per chi scrive il frontend.
- Niente CORS, niente login, niente endpoint di scrittura: arrivano con i
  todo successivi.

## Rischi

- **`NaN` nel JSON**: pandas usa `NaN` per i valori mancanti, e in JSON non
  esiste. Ogni valore passa da una conversione a `None` prima di entrare in
  un modello (in `db.py` c'e' gia' `_clean`), e anche gli interi con buchi
  (`avg_heart_rate`) arrivano da pandas come float: nel modello sono
  `int | None`.
- **La configurazione si legge all'import**: `training.garmin.config` si
  ferma se manca `user/config.yaml`. Per l'API e' un problema solo quando ci
  saranno piu' utenti: resta com'e', e lo risolve il todo del login.
- **`sync()` a ogni richiesta** senza la cache renderebbe lenta ogni
  chiamata, e due richieste insieme farebbero due scansioni: da qui cache e
  lock.
- **Attivita' lunghe**: un'escursione di sei ore ha oltre 20.000 punti di
  traccia. `max_points` c'e' per questo; `bins` e' gia' a 30 secondi.
- **Altair non e' pensato per un server**: `run_analysis_chart` disattiva
  un limite globale (`alt.data_transformers.disable_max_rows()` sta in
  `activity_detail.py`, non in `run_chart.py`). Se `to_dict()` si lamenta
  del numero di righe, la chiamata va portata in `run_chart.py`.

## Verifica

Non esiste una suite di test (arriva con il prossimo todo). Si verifica con
il `TestClient` di FastAPI sui dati locali, senza lanciare
`make update_activity`.

1. Import: `uv run python -c "import training.api.app"`, e
   `uv run python -c "import sys, training.api.app; assert 'streamlit' not in sys.modules"`.
2. `GET /openapi.json`: 200, con tutti i percorsi elencati in "Work".
3. `GET /api/activities?start=2026-10-01&end=2026-10-07`: le stesse
   attivita' di `list_activities()` filtrate su quei giorni, dalla piu'
   recente. C'e' la corsa "Canegrate - Rip_3x5" del 07/10/2026 alle 12:28:
   6,84 km, 46 minuti, FC media 136 e massima 159, Training Effect 3,5 e
   0,4. Nessun `NaN` nel testo della risposta.
4. `GET /api/activities/<id di quella corsa>`: `effect_seconds` vale 31,4,
   14,3 e 0,5 minuti (i valori del todo 31).
5. `.../chart`: tante righe in `bins` quante ne rende
   `run_chart.bins(records)`, e le stesse bande di `run_chart.zone_bands`.
   `.../chart/vega`: un dizionario con `$schema` di Vega-Lite e `vconcat`.
6. `.../route`: al massimo 2000 punti; con `max_points=50` al massimo 50, e
   primo e ultimo punto sono quelli dei record.
7. `GET /api/daily/2026-10-07`: uguale a
   `build_daily_data(date(2026, 10, 7))` passato per `json.dumps` e
   `json.loads`. Un giorno futuro: 422.
8. `GET /api/reports/daily/2026-10-07`: cinque sezioni, `Training`,
   `Recovery`, `Health`, `Load`, `Next`. Un giorno senza file: 404.
9. Un `activity_id` che non esiste: 404 su tutti e quattro i suoi endpoint.
10. Streamlit: `uv run streamlit run src/training/interface/app.py
    --server.headless true` parte senza traceback; la pagina Day mostra
    ancora il report del giorno e la scheda con i minuti per effetto.
11. `make api` in background: `curl -s
    "http://127.0.0.1:8000/api/activities?start=2026-10-01&end=2026-10-07"`
    risponde. Poi si ferma il server.
