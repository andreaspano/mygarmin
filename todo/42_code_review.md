---
status: done
---

# Revisione di tutto il codice

Il repo porta il suo progetto nei commenti e nel `README.md`: chi legge il
codice si fida di quello che c'e' scritto sopra. Il 2026-10-19, in
`frontend/vite.config.ts`, il commento diceva che su mutolo Vite ascoltava
sull'indirizzo Tailscale: non lo ha mai fatto, ascolta solo su 127.0.0.1, e
dalla tailnet ci arriva `tailscale serve`. Il codice era giusto, il commento
mentiva. Questo todo e' una passata su tutto il repo per due cose: i commenti
e i documenti che non dicono il vero, e il codice che si puo' accorciare o
non ripetere.

Non e' una caccia ai bug: la correttezza e l'integrita' dei dati restano
fuori (scelta di Andrea), e questo fa si' che nessuna correzione cambi il
comportamento.

## Decisioni

Prese con Andrea il 2026-10-19:

- **Tutto il repo**: `src/training` (circa 5.000 righe in 31 file),
  `frontend/src` (circa 3.200 righe in 20 file), piu' `Makefile` e
  `README.md`.
- **Due dimensioni sole**: (1) commenti, docstring e `README.md` che
  contraddicono il codice; (2) riuso e semplificazione. Niente caccia ai bug
  di correttezza, niente revisione dell'integrita' dei dati.
- **Si corregge quello che si trova**, sul ramo `todo_42`.
- **Il commit lo fa Andrea.** Il lavoro resta non committato, e in `main`
  non si unisce niente.

### Cosa cambia rispetto a `/atodo`

Il todo e' la specifica e vince sul protocollo della skill. Di `/atodo`
restano il ramo `todo_42`, le regole di autonomia, "mai riparare da soli per
far tornare verde" e la scala delle verifiche. Il commit e il merge non erano
previsti qui (li doveva fare Andrea), ma il 2026-10-19 li ha chiesti a fine
revisione: il lavoro e' quindi committato sul ramo e unito in `main` come in
un todo normale, con la sezione `## Revert` in fondo.

## Work

### 1. I commenti e i documenti che mentono

Per ogni modulo si legge il commento (o la docstring) contro il codice che
descrive. Quando non vanno d'accordo **si corregge il testo, non il
codice**: il codice funziona, ed e' quello che gira.

Da guardare, nell'ordine:

- `src/training/api/`: `app.py`, `refresh.py`, `models.py`, `context.py` e la
  cache della salute. La cache e' il codice piu' nuovo e meno riletto
  (commit `b89338b`, "cache health for a minute, read it once per daily
  request"): il commento dice per quanto vale e quando si butta, e va
  verificato contro quello che fa davvero.
- `src/training/garmin/`: `cli.py`, `auth.py`, `health.py`, `activities.py`,
  `misc.py`, `client.py`, `config.py`. Qui i commenti spiegano i tempi delle
  chiamate a Garmin e cosa si riprende dopo un Ctrl+C: si controlla che i
  numeri e le condizioni citate siano ancora quelli del codice.
- `src/training/interface/`.
- `frontend/src/`: `api/client.ts` e i `components/`.
- `Makefile`: il commento sopra ogni target dice cosa fa e cosa serve prima.
  Si confronta con la ricetta.
- `README.md`: ogni sezione contro il codice di adesso. La pagina Day, l'API,
  il tasto Refresh e la parte della tailnet sono le piu' esposte, perche' il
  codice si e' mosso di recente.

Un commento solo stringato, o che dice poco, non e' un rilievo: si tocca
solo quello che e' **falso** o che e' rimasto indietro.

### 2. Riuso e semplificazione

- logica duplicata in due o piu' punti;
- codice che rifa' a mano qualcosa che nel repo c'e' gia': nel rilievo si
  scrive **il nome della funzione o del modulo esistente** da usare;
- strade piu' lunghe del necessario, a comportamento uguale.

L'intervento e' il piu' piccolo che toglie il difetto. Non si riscrive
codice che funziona per gusto.

### 3. Il comportamento non si tocca

Qualunque modifica cambierebbe quello che il codice produce - un numero
diverso in un report, un'altra cosa a schermo, una risposta dell'API
diversa - **esce dallo scopo**: va nei rilievi come consiglio, non corretta.
E' la regola "expected-result change" di `/atodo`, applicata prima invece
che dopo.

## Findings

Da riempire durante la revisione, raggruppati per file, cosi' Andrea puo'
committare o buttare un rilievo alla volta. Una riga per rilievo:

```
<file>:<riga> - <cosa non andava> - <cosa si e' fatto>
```

oppure, per quello che non si corregge:

```
<file>:<riga> - <cosa non andava> - non corretto: <perche'>
```

### Corretti: commenti e documenti che mentivano

- `src/training/api/cache.py:22` - diceva "lo stesso minuto di
  `interface/data.py`", un modulo cancellato con la Streamlit (commit
  `fc696d0`, todo 40) - il
  commento tiene il minuto e il perche', senza il rimando morto.
- `src/training/api/cache.py:60` - la docstring di `invalidate` citava solo la
  scrittura del terreno (todo 35), ma la chiamano anche il tipo di corsa (todo
  36) e la fine di un Refresh (todo 41) - elencati tutti e tre.
- `src/training/garmin/activities.py:189` - "la pagina Recovery le legge da
  li'": quella pagina era della Streamlit e non esiste piu' - ora dice le card
  Recovery e Health della Day.
- `src/training/garmin/fitness_status.py:24` - la tupla era presentata come
  "gli endpoint che legge il report", e si diceva che allargarla cambierebbe
  "l'input dell'agente del report": dal todo 31 l'agente prende i fatti da
  `make daily_data` e non passa piu' da qui (il todo 31 lo dice:
  "l'agente non li usa piu'") - riscritto, la tupla resta com'era.
- `src/training/interface/health.py:43` - "le prime nove sono quelle della
  pagina Recovery" - come sopra, sono quelle delle card Recovery e Health.
- `src/training/interface/health.py:363` - la velocita' della soglia del
  lattato era detta "in decimi di m/s", ma il codice moltiplica per 36 (il
  numero di Garmin e' un decimo del valore in m/s, non il contrario) - via il
  nome d'unita' sbagliato, resta il conto.
- `src/training/interface/sports.py:16` - l'icona del riposo era data "nella
  tabella della Day (righe vuote, todo 30)", che era la tabella della
  Streamlit - ora la striscia della settimana e i "Rest day" della scheda
  Training, che sono i due posti che la usano davvero.
- `src/training/interface/sports.py:26` - citava la regola di `profile.py`
  (`CAPITALIZE_KEYS`), cancellato con la Streamlit - via il riferimento.
- `src/training/interface/db.py:10` - "both call sync() first" per
  `list_activities()` e `load_activity_records()`: la seconda non chiama
  `sync()` - ora dice come stanno le cose (la seconda si aspetta che la prima
  abbia gia' sincronizzato, che e' l'ordine che usano API e report).
- `src/training/interface/db.py:299` - "Solo da questa data in poi" veniva
  dopo aver citato l'11/09/2026, mentre `THRESHOLD_FALLBACK_FROM` e' il
  2026-08-01: si leggeva il taglio sbagliato - ora rimanda alla costante.
- `frontend/src/format.ts:54` - "La Streamlit lo usa per le durate" - il
  motivo di `roundHalfEven` e' leggere le durate come i report, che passano
  dal `round` di Python.
- `frontend/src/components/RunChart.tsx:10` - "(nella Streamlit li mette il
  tema di Streamlit)" - via.
- `frontend/src/components/RunChart.tsx:53` - "la tabella non deve
  aspettarla": nella Day non c'e' nessuna tabella - "il resto della pagina".
- `frontend/src/components/RouteMap.tsx:1` - "come oggi `st.map` carica le sue
  da Carto" - via il paragone con la Streamlit.
- `Makefile:18` - "circa 3.300 chiamate" per un anno di salute: erano nove
  endpoint al giorno, dal todo 38 sono undici - circa 4.000 (365 x 11 = 4.015;
  365 x 9 = 3.285, da cui veniva il numero vecchio). La stima di 30-45 minuti
  resta: non si puo' misurare senza chiamare Garmin.
- `README.md:29` - "Tutto `GET` ... tranne due `PUT`": dal todo 41 c'e' anche
  la `POST` del tasto Refresh, l'unica che scarica da Garmin e riscrive un
  report - corretto, e la riga sotto (il Refresh) lo diceva gia'.
- `README.md:71` - "(vedi sotto)" mandava a una spiegazione che sta nella
  sezione sopra - "(vedi sopra)".

### Corretti: riuso e semplificazione

- `src/training/interface/daily_data.py:33` - `LOAD_METRICS` era una copia
  identica (verificata) di quella di `weekly_data`, da cui questo modulo
  importa gia' `WEEKDAYS`, `_mean` e `_value` - via la copia.
- `src/training/interface/daily_data.py:33` - `_load_on` era riga per riga
  `weekly_data._load` - via, si importa `_load`.
- `src/training/interface/fit.py:48` - la scrittura atomica del JSON (file
  temporaneo, `os.replace`, pulizia) stava uguale in `terrain.py` e
  `run_type.py` - `save_json_map`, accanto a `_load_json_map` che quei due
  moduli usano gia' da qui; i lock restano uno per file, dove erano.
- `frontend/src/api/client.ts:34` - `isAbort` stava in `DayPage` e in
  `TrainingCard`, e in `RunChart` scritto a mano - esportata da `client.ts`,
  accanto a `ApiError`.
- `frontend/src/components/Stat.tsx:11` - `Metric` (TrainingCard) era `Stat`
  con il tooltip - `Stat` prende `help` e `Metric` non c'e' piu'; senza
  `help` il markup di `Stat` non cambia.
- `frontend/src/components/LoadCard.tsx:87` - `LoadCard` e `TrainingCard`
  riscrivevano a mano il `block-head` di `CardHead` - usano `CardHead`.
- `frontend/src/components/TrainingCard.tsx:121` - `TerrainPicker` e
  `RunTypePicker` erano lo stesso componente due volte (la docstring del
  secondo diceva "come `TerrainPicker`") - un solo `OverridePicker`.

### Non corretti: cambierebbero il comportamento, o sono scelte di Andrea

- `src/training/api/refresh.py:29` - **rilievo sbagliato, ritirato il
  2026-10-19.** Avevo scritto che `ALLOWED_TOOLS` non copre quello che
  l'agente fa: che `Edit(summary/01.daily/**)` non permette le Write
  dell'agente, e che `Bash(make update_activity)` non riconosce il `cd <repo>
  && make ...` che l'agente scrive. La documentazione di Claude Code dice il
  contrario su tutti e due i punti, e le regole come stanno sono giuste:
  - i permessi sui file si controllano **solo** con regole `Edit(path)` e
    `Read(path)`: "If you write a path rule for `Write` ... Claude Code
    accepts the rule but never consults it ... Use `Edit(docs/**)` in place of
    `Write(docs/**)`". `Edit(summary/01.daily/**)` e' quindi il modo giusto di
    permettere le Write dell'agente in quella cartella; una regola
    `Write(...)` verrebbe ignorata. Il path e' relativo alla cartella di
    lavoro, che e' `repo_root` (`cwd` di `subprocess.run`), cioe' proprio il
    file che l'agente scrive.
  - i comandi composti vengono spezzati: "A rule must match each subcommand
    independently", e "a `cd` into a path inside your working directory ... is
    also read-only", quindi il `cd <repo>` non chiede niente e resta da
    coprire solo `make update_activity`, che la regola prende alla lettera.
  - `Bash(make -s daily_data:*)` e' una regola valida: "The `:*` suffix is an
    equivalent way to write a trailing wildcard", riconosciuta a fine riga
    come qui.
  Provato sul `claude` vero il 2026-10-19 alle 22:23, per la prima volta: la
  POST rende 202 `running`, un secondo clic non lancia un altro lavoro, un
  giorno futuro da' 422, e in 54 secondi lo stato arriva a `done`. Nel
  frattempo l'agente ha fatto `make update_activity` (12 file di salute,
  `activities.db`, i nomi e i tipi delle attivita') e ha riscritto
  `summary/01.daily/2026-10-19.md` con la Write: nessun permesso negato.
  Se un giorno fallisse, la cosa utile e' `--permission-prompts none`: in
  `-p` senza nessuno che risponda, un permesso che manca verrebbe negato
  subito invece di aspettare i 15 minuti del timeout.
- `src/training/interface/daily_data.py:104` - `_hrv_baseline(day)` e'
  chiamata senza `data_dir`, quindi legge sempre dal `DATA_DIR` globale anche
  quando `build_daily_data` ne riceve un altro (l'API passa `ctx.data_dir`).
  Oggi i due coincidono, ma `api/context.py` esiste proprio perche' un giorno
  non coincidano. Non corretto: correttezza.
- `src/training/garmin/activities.py:17` - `_ACTIVITY_ID_RE`,
  `_NAMES_FILENAME`, `_TYPES_FILENAME`, i loader di nomi e tipi e
  `_existing_activity_ids` ci sono anche in `interface/fit.py`
  (`load_activity_names`, `load_activity_types`, `_load_json_map`,
  `list_activity_files`, `activity_id_from_path`): `garmin/` scrive quei file
  e `interface/` li legge, ognuno con il suo codice. Non corretto: metterli in
  un posto solo vuol dire far dipendere `garmin/` da `interface/` (oggi la
  dipendenza va nell'altro verso) o aprire un modulo nuovo - e' una scelta di
  struttura, non una ripulitura.
- `src/training/garmin/activities.py:159` e `:238` - il ciclo "scarica,
  estrai, stampa, dormi" e' lo stesso in `download_activities_between` e in
  `update_activity`, messaggi compresi. Non corretto: sta sulla strada di
  rete, che la verifica non puo' percorrere (`make update_activity` e i
  backfill non si lanciano), quindi un'estrazione resterebbe non provata.
- `src/training/garmin/__init__.py:17` - il messaggio dice `pip install
  garminconnect`, ma il progetto si gestisce con uv (`uv.lock`, `uv run`,
  `pyproject.toml`). Non corretto: e' un testo a schermo.
- `src/training/interface/activity_report.py:13` - `OUT_DIR =
  Path("summary/00.activity")` e' relativo, quindi `make activity_reports`
  scrive nel posto giusto solo dalla radice del repo; `api/context.py` per la
  stessa cosa parte da `REPO_ROOT`, "perche' l'API non deve dipendere dalla
  cartella da cui si lancia". Non corretto: cambierebbe dove finiscono i file.
- `src/training/interface/activity_report.py:66` - la pendenza e' ricalcolata
  a mano (quota diviso distanza, campione per campione, clip a +-30) mentre
  `grade.slope_pct` fa lo stesso lavoro meglio (finestra di 30 m, quota
  lisciata). Non corretto: i numeri dei report cambierebbero.
- `src/training/interface/activity_report.py:119` -
  `load_activity_comments` non ha nessun chiamante in tutto il repo (la
  leggeva la Streamlit). Non corretto: la pagina Activities e' fra quelle che
  arriveranno (`TopBar`), ed e' esattamente quello che le servirebbe:
  cancellarla e' una scelta di Andrea.
- `src/training/interface/db.py:211` - `_insert_activity` scrive a mano i 23
  nomi di colonna tre volte (colonne, parametri, `DO UPDATE SET`), mentre
  `_insert_records` la sua SQL la genera da una tupla. Non corretto: sta sulla
  strada di scrittura di `activities.db` e qui non si puo' provare (un
  `rebuild()` cancella il database).
- `src/training/interface/daily_data.py:218` - `_vo2max_change` e
  `_latest_with_change` fanno lo stesso lavoro; la prima aggiunge solo la
  soglia di 0.5. Non corretto: unirle sposterebbe il confronto sul valore
  arrotondato e cambierebbe i casi al limite (una differenza di 0.45 diventa
  0.5 e passerebbe).
- `src/training/api/app.py:43` - `_clean` e' importata privata da `db.py`;
  stessa cosa per `_mean`/`_value` (da `weekly_data`) e `_day_paths`/`_dig`/
  `_primary_entry`/`_read_json` (da `health`). Non corretto: renderle
  pubbliche e' un rinominare diffuso, piu' gusto che difetto.

### Fuori dalla revisione

- `export/` e `.claude/` non sono fra le cartelle elencate nel todo
  (`src/training`, `frontend/src`, `Makefile`, `README.md`): non sono state
  riviste. `.claude/agents/fitness-status.md` e' stato letto, ma solo come
  prova per il rilievo su `ALLOWED_TOOLS`.
- `frontend/src/api/schema.ts` e' generato: non guardato, non toccato.
- La prova nel browser non si e' potuta fare: su questa macchina
  `chromium-browser` e' solo lo stub dello snap e non c'e' nessun browser
  installato (e l'estensione di Chrome non e' collegata). Al suo posto, i tre
  componenti rifatti sono stati resi con `react-dom/server` nelle due
  versioni, vecchia e nuova, e il markup e' identico (vedi "Verifica" nel
  rapporto). La pagina vera la guarda Andrea.

## Vincoli

- Il comportamento non cambia.
- Nessuna dipendenza nuova.
- Non si toccano gli altri file di `todo/`, ne' il loro `status`.
- Non si scrive in `summary/` ne' nell'albero dei dati.
- `frontend/src/api/schema.ts` non si modifica a mano: lo genera
  `make frontend_types`.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Riscrivere invece di correggere**: una passata di qualita' su 8.200
  righe senza test suite puo' scivolare nel rifare codice che gia' va. Il
  mandato e' la modifica minima.
- **Il ramo resta sporco**: finche' Andrea non committa, `git status` su
  `todo_42` mostra le modifiche, e `/atodo` su un altro todo si rifiuta di
  partire (precondizione 3). E' voluto.

## Verifica

1. `uv run python -c "import training"`, piu' un import di ogni modulo
   toccato (es. `uv run python -c "from training.api import app, refresh"`).
2. `cd frontend && npm run typecheck` e `npm run build`: nessun errore.
3. Se si e' toccato un modello dell'API, con l'API accesa
   `make frontend_types` deve lasciare `frontend/src/api/schema.ts`
   invariato.
4. `git diff` riletto contro l'elenco dei Findings: ogni pezzo di diff
   corrisponde a un rilievo, e ogni rilievo corretto a un pezzo di diff.
5. Mai `make update_activity`, `make backfill_health`, `make backfill` ne'
   `make backfill_activity_names`: vanno in rete e scrivono nei dati.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_42'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. La revisione ha toccato commenti, documenti
e codice a comportamento uguale: niente dati, niente report, niente database.

Dopo il revert, rifare il merge di `todo_42` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
