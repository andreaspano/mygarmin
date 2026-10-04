---
status: done
---

# Config: `user/config.yaml`, obbligatorio e senza default

Oggi la configurazione e' scritta nel codice, sparsa in tre file
(`garmin/config.py`, `garmin/health.py`, `interface/fit.py`), e in un punto e'
gia' incoerente: `garmin-export-all` scarica la salute da `START_DATE`
(2015-01-01), `make backfill_health` da `HEALTH_BACKFILL_START` (2025-01-01).
Due date d'inizio per la stessa cosa.

**Regole decise**:

- tutta la configurazione sta in `user/config.yaml`, committato (come
  `user/profile.yaml`);
- **nessun default nel codice**: se il file manca, o manca una chiave, il
  sistema si ferma con un errore;
- **nessuna variabile d'ambiente**, nemmeno per `data_dir`: il file e' l'unica
  fonte.

**Da fare dopo il merge del todo 16**: tocca anche lui `garmin/health.py`.

## Il file

```yaml
# Configurazione di mygarmin. Tutte le chiavi sono obbligatorie: non ci sono
# default nel codice, una chiave mancante ferma il programma.

# Cartella dei dati (FIT, health/, activities.db). Usata dal download,
# dall'interfaccia e dallo stato di forma.
data_dir: ~/adrive/data/garmin-export

# Token di login di Garmin Connect (evita di reinserire la password).
token_store: ~/token

# Fuso orario in cui mostrare gli orari. Cambiarlo richiede di alzare
# LOGIC_VERSION in interface/db.py: la cache salva gli orari gia' convertiti.
local_tz: Europe/Rome

# Primo giorno dello storico delle metriche di salute, per garmin-export-all e
# per make backfill_health.
history_start: 2025-01-01

# Pausa in secondi fra una richiesta a Garmin e l'altra. Se arrivano errori
# "too many requests", aumentarla.
request_delay: 0.3

# Giorni di salute riscaricati a ogni update (compreso oggi).
health_refresh_days: 3

# Giorni (compreso oggi) della finestra dello stato di forma.
fitness_status_window_days: 14
```

I commenti vengono da quelli di oggi in `config.py`: si spostano nel YAML,
perche' e' li' che si cambiano i valori.

## Work

- `user/config.yaml` come sopra.
- `garmin/config.py` diventa il lettore del file, e resta l'unico punto da
  cui il resto del codice importa: i nomi esportati restano gli stessi
  (`DATA_DIR`, `TOKEN_STORE`, `REQUEST_DELAY`, `FITNESS_STATUS_WINDOW_DAYS`,
  `OUTPUT_DIR`), cosi' gli import altrove non cambiano. Si aggiungono
  `LOCAL_TZ`, `HISTORY_START`, `HEALTH_REFRESH_DAYS`.
  - Il path del file e' relativo alla **radice del repo**
    (`Path(__file__).resolve().parents[3] / "user" / "config.yaml"`), non
    alla cartella corrente: deve funzionare da qualunque cartella si lanci.
  - Lettura e validazione **all'import**, tutte insieme. Un solo errore
    (`ConfigError`, sottoclasse di `RuntimeError`) che elenca in un messaggio
    tutto quello che non va: file mancante, chiavi mancanti, chiavi
    sconosciute (un refuso come `data_dirr` va segnalato per nome), tipi
    sbagliati. Il messaggio dice il path del file.
  - Tipi: `data_dir`, `token_store` stringhe, poi `expanduser()`;
    `local_tz` deve essere un fuso valido per `ZoneInfo`; `history_start`
    una data (YAML la legge gia' come `date`) non nel futuro;
    `request_delay` numero >= 0; `health_refresh_days` e
    `fitness_status_window_days` interi >= 1. I `bool` non valgono come numeri
    (come in `health._number`).
- Spostamenti:
  - `START_DATE` e `HEALTH_BACKFILL_START` diventano `HISTORY_START`;
    `garmin/cli.py` e `garmin/health.py::backfill_health` usano quella;
  - `HEALTH_REFRESH_DAYS` esce da `garmin/health.py` e arriva da `config`;
  - `LOCAL_TZ` esce da `interface/fit.py` e arriva da `config` (`fit.py` lo
    importa, `db.py` continua a prenderlo da `fit`).
- `END_DATE = date.today()` non e' configurazione: resta calcolata, in
  `cli.py` dove serve.
- La docstring di `config.py` va riscritta: ora spiega dove sta il file e che
  non ci sono default.
- `README.md`: una sezione breve sul file.

## Vincoli

- Nessuna dipendenza nuova: `pyyaml` c'e' gia'.
- Le costanti che non sono configurazione restano nel codice: schema e
  `LOGIC_VERSION`, costanti FIT, `DAILY_ENDPOINTS`, `GARMIN_TYPE_TO_SPORT`,
  colori e larghezze dei grafici, `ACTIVITIES_TTL_SECONDS`, i nomi dei file.
- Non toccare `user/profile.yaml` ne' la pagina Profile.
- Commenti in italiano senza accenti.

## Rischi

- **Cambio di comportamento voluto**: `garmin-export-all` scarichera' la
  salute dal 2025-01-01 e non piu' dal 2015-01-01. E' la data di
  `make backfill_health`, e quella da cui partono le attivita' (gennaio
  2025): prima non ci sono allenamenti a cui affiancare la salute. Nota: i
  JSON di salute su disco oggi partono dal 2026-08-01 (64 giorni), perche' il
  backfill dal 2025 non e' mai stato lanciato fino in fondo; questo todo non
  lo lancia.
- Ogni clone e ogni worktree trova il file perche' e' committato. Per un
  sandbox (come il todo 16) basta cambiare `data_dir` nel `config.yaml` del
  worktree: quella modifica **non va mergiata**.
- Un errore all'import ferma anche Streamlit: e' quello che si vuole, ma la
  pagina mostra il traceback. Il messaggio deve essere leggibile da solo.

## Verifica

1. Con il file com'e': `uv run python -c "from training.garmin import config;
   print(config.DATA_DIR, config.HISTORY_START, config.LOCAL_TZ)"` stampa i
   valori di oggi.
2. Su una copia del file (non quello vero), uno per volta, ognuno deve dare
   `ConfigError` con un messaggio chiaro:
   - file assente;
   - una chiave tolta;
   - due chiavi tolte (devono comparire tutte e due nello stesso messaggio);
   - una chiave in piu' (`data_dirr`);
   - `local_tz: Europa/Roma`, `request_delay: -1`, `health_refresh_days: true`,
     `history_start: domani`.
   Per farlo senza toccare `user/config.yaml`, la lettura va in una funzione
   `load_config(path)`; il modulo la chiama con il path del repo.
3. Da un'altra cartella (`cd /tmp && uv run --project <repo> python -c ...`):
   il file si trova lo stesso.
4. `grep` di `START_DATE`, `HEALTH_BACKFILL_START`, `ZoneInfo("Europe/Rome")`:
   nessun risultato fuori da `config.py`.
5. `streamlit run`: l'app parte e le pagine sono identiche.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_17'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Il revert riporta le costanti nel codice e
toglie `user/config.yaml`; dati e cache non cambiano.

Dopo il revert, rifare il merge di `todo_17` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
