---
status: todo
---

# Health in SQLite: una tabella `health_daily` derivata dai JSON

Oggi i dati di salute stanno in `DATA_DIR/health/<endpoint>/<YYYY-MM-DD>.json`,
un file per endpoint e per giorno, e `interface/health.py` li legge in un
DataFrame. I todo 07 (VO2max del giorno), 11 (training load) e 14 (piano contro
fatto) devono mettere la salute accanto alle attivita', e un backfill completo
(circa 640 giorni x 9 endpoint) vuol dire circa 5.800 file aperti a freddo.

**Scelta**: una tabella `health_daily` dentro `activities.db`, costruita dai
JSON come `activities` e' costruita dai `.fit`. I JSON restano la fonte: il
downloader (`garmin/health.py`) non cambia e la tabella si ricostruisce
sempre. Scartata l'alternativa "tutto in SQLite, niente file": il DB
diventerebbe l'unica copia, `rebuild()` cancella il file intero, e il backup
sarebbe un unico binario che cambia a ogni giro.

**Tutti e nove gli endpoint** entrano nella tabella, ma solo con i valori
giornalieri. Le serie minuto per minuto (stress 3,3 MB, respiration 2,2 MB, il
sonno) restano nei JSON: in SQLite non servono a nessuna pagina.

## Dati, verificato (2026-08-01 -> 2026-10-03)

| colonne | endpoint | campo nel JSON |
|---|---|---|
| `readiness` | training_readiness | `score` del risveglio (`_readiness_score`, com'e') |
| `body_battery_low`, `body_battery_high` | stats | `bodyBatteryLowestValue`, `bodyBatteryHighestValue` |
| `hrv_last_night`, `hrv_weekly_avg`, `hrv_status` | hrv | `hrvSummary.lastNightAvg`, `.weeklyAvg`, `.status` |
| `resting_hr` | resting_heart_rate | `_resting_hr`, com'e' |
| `sleep_hours`, `sleep_score` | sleep | `dailySleepDTO.sleepTimeSeconds / 3600`, `.sleepScores.overall.value` |
| `stress_avg`, `stress_max` | stress | `avgStressLevel`, `maxStressLevel` |
| `resp_sleep_avg`, `resp_waking_avg`, `resp_low`, `resp_high` | respiration | `avgSleepRespirationValue`, `avgWakingRespirationValue`, `lowestRespirationValue`, `highestRespirationValue` |
| `spo2_avg`, `spo2_low`, `spo2_sleep_avg` | spo2 | `averageSpO2`, `lowestSpO2`, `avgSleepSpO2` |
| `vo2max`, `vo2max_date` | training_status | `mostRecentVO2Max.generic.vo2MaxPreciseValue`, `.calendarDate` |
| `training_status`, `training_status_phrase` | training_status | `mostRecentTrainingStatus.latestTrainingStatusData.<device>.trainingStatus`, `.trainingStatusFeedbackPhrase` |
| `load_acute`, `load_chronic`, `acwr`, `acwr_status` | training_status | `<stessa voce>.acuteTrainingLoadDTO.dailyTrainingLoadAcute`, `.dailyTrainingLoadChronic`, `.dailyAcuteChronicWorkloadRatio`, `.acwrStatus` |
| `load_aerobic_low`, `load_aerobic_high`, `load_anaerobic`, `load_balance_phrase` | training_status | `mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap.<device>.monthlyLoadAerobicLow`, `.monthlyLoadAerobicHigh`, `.monthlyLoadAnaerobic`, `.trainingBalanceFeedbackPhrase` |

Le trappole, viste sui file veri:

- **spo2 e' tutto `null`**: l'orologio non la misura. Le colonne ci sono ma
  restano vuote; se un giorno la si attiva, si riempiono senza toccare niente.
- **VO2max e' "il piu' recente", non quello del giorno.** Il file del
  2026-09-17 porta ancora il valore del 09-16, e cosi' fino al 09-20; prima
  del 09-11 non c'e' proprio. E il valore di un giorno puo' comparire solo nel
  file del giorno dopo: il 40.2 del 09-14 sta nel file del 09-15, non in quello
  del 09-14 (che riporta il 09-13). Quindi si salvano valore **e** data
  (`vo2max_date`), e "il VO2max del giorno D" sono le righe con
  `vo2max_date = D`. Tenerlo solo quando la data coincide col giorno del file
  perderebbe il 09-14; ripeterlo su ogni riga senza data farebbe sembrare un
  plateau cinque giorni con un solo valore.
- **Training status e load balance invece sono del giorno**: in tutti i file
  il loro `calendarDate` coincide col nome del file. Il controllo
  `calendarDate == day` resta comunque, per sicurezza: se non coincide, NULL.
- **Chiavi per ID dell'orologio** (`"3600579909"`): si prende la voce con
  `primaryTrainingDevice: true`, non la prima. Con un secondo orologio le voci
  sarebbero due.
- `weeklyTrainingLoad`, `loadTunnelMin`/`Max`, `loadLevelTrend` sono `null`:
  restano fuori.
- `trainingStatus` e' un intero (7 il 10-02, con frase `PRODUCTIVE_3`): si
  salva il valore grezzo, la traduzione in parole la fa chi lo mostra.

## Work

- Nuovo modulo `interface/health_db.py`, separato da `db.py` perche' le due
  cache restino indipendenti; riusa `db._connect` / `_db_path`.
- Tabella (accanto a `_SCHEMA`): `day TEXT PRIMARY KEY`, poi una colonna per
  ogni riga della tabella qui sopra (`REAL` per i numeri, `TEXT` per
  `hrv_status`, `vo2max_date`, `acwr_status` e le `*_phrase`), poi
  `source_mtime REAL NOT NULL` (mtime massimo dei nove JSON del giorno) e
  `parsed_at TEXT NOT NULL`. `WITHOUT ROWID`. NULL vuol dire "non lo
  sappiamo", mai zero: lo stesso contratto di `_dig()`.
- `health.py`:
  - `COLUMNS` cresce con le colonne nuove, nello stesso ordine della tabella;
  - `_USED_ENDPOINTS` diventa tutti gli endpoint di `DAILY_ENDPOINTS`;
  - nuove funzioni di estrazione accanto a `_readiness_score` / `_resting_hr`:
    `_primary_entry(device_map)` (la voce con `primaryTrainingDevice`),
    `_vo2max(payload)` (valore e data), `_training_status(payload, day)` e
    `_load_balance(payload, day)` (con il controllo sulla data);
  - `_day_row()` legge i nove file e riempie tutte le colonne;
  - va riscritto il paragrafo della docstring che dice che gli altri quattro
    endpoint "non vengono nemmeno aperti", e quello "Niente SQLite": SQLite e'
    una cache derivata, la fonte restano i JSON.
- `HEALTH_LOGIC_VERSION = "1"` in `schema_meta`, chiave
  `health_logic_version`, separata da `logic_version` dei FIT: un cambio al
  parsing della salute fa `DELETE FROM health_daily` e riempie di nuovo, senza
  rileggere i FIT. Un `rebuild()` dei FIT cancella comunque tutto il file, e
  va bene: il primo `sync_health()` dopo riempie la tabella dai JSON.
- `sync_health(data_dir)`:
  1. versione assente o diversa: svuota la tabella;
  2. per ogni giorno di `available_days()`, mtime massimo dei nove file; si
     rilegge il giorno solo se manca o se l'mtime e' piu' nuovo. Serve perche'
     `export_daily_health(..., force_dates={today})` riscrive i file di oggi a
     ogni giro: una riga messa in cache una volta per giorno resterebbe
     vecchia;
  3. upsert con `_day_row()`.
- `load_health_db(data_dir) -> DataFrame`: `sync_health()`, poi
  `SELECT ... ORDER BY day`, e la stessa forma che `load_health()` restituisce
  oggi: indice `DatetimeIndex` di nome `day`, `reindex` sul calendario
  completo, DataFrame vuoto con le colonne giuste se non c'e' niente.
- `load_health()` diventa un involucro sottile di `load_health_db()`, con nome
  e docstring invariati, cosi' `data.load_health_metrics` e
  `app_pages/recovery.py` non cambiano: la pagina Recovery continua a usare
  solo le sue colonne.
- Docstring di `db.py`: dire che `health_daily` sta nello stesso file ma si
  costruisce dai JSON.
- `todo/10_recovery_page.md` (riga ~84, "i dati di salute non passano da
  SQLite"): una riga che rimanda a questo todo.

## Vincoli

- Non toccare il downloader ne' la struttura dei file su disco.
- `garmin/fitness_status.py::_load_cached_health` continua a leggere i JSON
  grezzi: l'agente fitness-status vuole i payload interi, non le colonne.
- Ogni campo passa da `_dig()` / `_number()`, come oggi.
- Commenti in italiano senza accenti.

## Rischi

- Il `rebuild()` dei FIT cancella anche `health_daily`: costa un giro di
  lettura dei JSON, non dati persi.
- Aprire anche stress e respiration aggiunge circa 5,5 MB di JSON al primo
  sync completo (le serie minuto per minuto si leggono per buttarle). Succede
  una volta, poi si va per mtime; ma sul backfill completo va misurato.
- Le frasi e gli interi di training status sono scelte di Garmin, e possono
  cambiare: per questo si salvano grezzi.
- L'mtime dipende dal sync di `~/adrive`: se il sync riscrive i file senza
  cambiarli, si rilegge qualche giorno in piu'. Costa poco e non sbaglia.

## Verifica

1. Equivalenza sulle nove colonne della pagina Recovery: il vecchio
   `load_health()` (da git) e il nuovo sugli stessi dati,
   `pd.testing.assert_frame_equal` (oggi 64 giorni).
2. Valori noti, dai file:
   - 2026-10-02: `load_acute` 493, `load_chronic` 392, `acwr` 1.2,
     `acwr_status` OPTIMAL, `training_status` 7, `stress_avg` 25,
     `stress_max` 87, `resp_sleep_avg` 13;
   - VO2max: `vo2max_date` 2026-09-14 con 40.2 compare (dal file del 09-15);
     prima del 09-11 `vo2max` e' NULL;
   - spo2: tutte NULL.
3. Secondo giro: nessun giorno riletto.
4. `touch` su `stats/<oggi>.json`, poi sync: si rilegge solo quel giorno.
5. Cambiare `HEALTH_LOGIC_VERSION`: la tabella si riempie di nuovo, le
   attivita' no (stesso numero di righe e stesso `parsed_at` in `activities`).
6. Cancellare `activities.db`: l'app ricostruisce entrambe le tabelle.
7. `streamlit run`, pagina Recovery: grafici identici a prima.
