---
status: done
---

# I dati fuori dal repo: una cartella sola, con un puntatore

Il confine fra codice e dati non era stato deciso, era successo:

- `data_dir` teneva FIT, `health/`, i quattro JSON e `activities.db` **tutti
  piatti nella stessa cartella**;
- `summary/` era in `.gitignore`, ma **tredici report vecchi e un piano
  settimanale erano tracciati lo stesso**, committati prima che l'ignore
  esistesse;
- `user/config.yaml`, `user/profile.yaml` e `user/avatar.jpg` erano tracciati
  **e spinti su GitHub**;
- `plan/` era tracciato;
- `export/garmin_export_all.py` si riscriveva i due percorsi a mano e la
  configurazione non la leggeva affatto.

Qui i dati vanno tutti sotto `~/adrive/data/training`, in sette cartelle, e
nel repo resta un **puntatore** che dice dov'e'. Nel repo restano codice,
icone, todo, documentazione e il puntatore.

## Le scelte

- **`db/` e' la settima cartella**: `activities.db` sta nella radice dei dati.
- **`plan/` esce dal repo** con tutto il resto: una regola sola.
- **Il puntatore e' YAML**, come il resto della configurazione.
- **`json/` tiene il nome**, correzioni e cache insieme.

## L'uovo e la gallina

`user/config.yaml` si trovava risalendo da `__file__` alla radice del repo. Se
`user/` va nella cartella dati, **la cosa che dice dove sono i dati non puo'
stare nella cartella dati**. Da cui `data.yaml`, nella radice del repo, con
una chiave sola:

```yaml
data_root: ~/adrive/data/training
```

Si legge per primo, e da li' `CONFIG_PATH = DATA_ROOT / "user" / "config.yaml"`.
Resta **tracciato**: un file obbligatorio e non versionato romperebbe un clone
pulito, e il `~` lo rende valido su ogni macchina dello stesso utente.

`data_dir` sparisce da `config.yaml` — la radice adesso e' il puntatore — e
quindi anche da `_FIELDS`, che le chiavi sconosciute sono un errore fatale.

**La radice non si crea.** Ovunque nel codice un `mkdir(parents=True)` su un
percorso storto costruisce un albero vuoto invece di fermarsi, ed e' il modo
di accorgersi di un refuso tre giorni dopo guardando dei report che non
arrivano. Il puntatore pretende che la cartella esista.

## La disposizione

```
~/adrive/data/training/
  fit/       *_ACTIVITY.fit
  health/    <endpoint>/<giorno>.json          (era gia' cosi')
  json/      activity_names, activity_types, activity_terrain, activity_run_type
  db/        activities.db
  user/      config.yaml, profile.yaml, avatar.jpg
  summary/   01.daily … 05.plan
  plan/      i blocchi scritti a mano
```

## Work

- `data.yaml` nuovo; `config.py` lo legge con `load_data_root`, espone la
  radice e le sette cartelle, e `data_dir` sparisce da `_FIELDS` e dal file.
- I punti che costruiscono un percorso dentro la radice: i FIT in `fit/`
  (`fit.py`, `activities.py` in lettura, nel glob degli id e nei due
  `extractall`), i quattro JSON in `json/`, il database in `db/`. `health/`
  non si tocca.
- Chi scrive crea la sua cartella: `save_json_map`, i due salvataggi di nomi e
  tipi, e `_connect` per `db/`.
- `context.py`: `SUMMARY_DIR` e `PLAN_DIR` dalla radice dei dati. `ICONS_DIR`
  resta sul repo.
- `refresh.py`: il permesso di scrittura degli agenti diventa assoluto.
- `app.py`: la cartella del giorno dal registro (`DAILY.folder`) invece della
  stringa `"01.daily"`, come fa gia' il gemello settimanale.
- `export/garmin_export_all.py`: radice e token dalla configurazione.
- `.gitignore` e `git rm --cached` su `summary/`, `user/`, `plan/`.
- `tools/migrate_data.sh`: il trasloco, con il giro a vuoto di partenza.

## Rischi

- **Il permesso degli agenti e' l'unico guasto silenzioso.** Non da' un errore
  di percorso: da' sezioni che «non hanno scritto». Va provato lanciando un
  agente vero.
- **`~/adrive` e' sincronizzata e ha gia' dato conflitti.** In `garmin-export`
  ci sono `activities.db.conflict1` (199 MB) e `.conflict2` (42 MB), piu' le
  copie di `activity_names.json` e `activity_types.json`. Portandoci dentro
  `summary/`, che **due timer riscrivono ogni giorno alle 10 e alle 22** (todo
  47), i conflitti arriveranno anche li'. Non e' un motivo per non farlo, e' un
  motivo per **escludere `db/` dalla sincronizzazione**: `activities.db` e' una
  cache ricostruibile dai FIT (`LOGIC_VERSION`), e sincronizzare 205 MB di
  cache e' il peggiore dei mondi.
- **La storia su GitHub non si pulisce con questo lavoro.**
  `user/profile.yaml` (id Garmin, email, data di nascita, altezza, peso),
  `user/config.yaml` e i report giornalieri **sono in `origin/main`**.
  Toglierli adesso li toglie dai commit futuri; per toglierli dalla storia
  serve `git filter-repo` e un push forzato, che e' un lavoro a parte.

## Verifica

1. Il puntatore: senza `data.yaml`, con la chiave storta, o con una cartella
   che non esiste, il programma si ferma dicendo quale dei tre.
2. `make api` risponde 200 su tutte le rotte, icone comprese.
3. Le pagine, in Firefox headless: Day/Report, Day/Training, Day/Trend,
   Week/Snap, Week/Plan, Plan.
4. **Un agente scrive davvero** nella cartella nuova.
5. I comandi da terminale leggono FIT, salute e database dai posti nuovi.
6. Niente resta indietro: nessun `REPO_ROOT` che punti a dati.

## Come e' andata

Fatto come scritto, e **il rischio numero uno si e' avverato**: il primo
agente lanciato dopo il trasloco ha risposto `failed  05_training finished
without writing training.md`. Esattamente il guasto muto previsto. Ma la
causa non era quella prevista.

### Il doppio slash

Il piano diceva: il glob del permesso e' relativo, va reso assoluto. Reso
assoluto — `Edit(/home/andrea/adrive/.../summary/01.daily/**)` — **non
bastava**. Riprodotto a mano, l'agente risponde:

> The write needs your approval — the permission prompt for
> `/home/andrea/adrive/.../2026-10-26/_probe.md` wasn't granted, so nothing
> was written.

Cioe': la regola non corrispondeva, l'agente chiedeva un permesso
interattivo, e girando senza terminale finiva dicendo di non aver scritto.
Provato anche `--add-dir` sulla cartella: stesso esito.

**Nelle regole di permesso un percorso che comincia con `/` si intende
relativo alla cartella del progetto.** Per dire "assoluto" se ne mettono
**due**. La regola giusta e'
`Edit(//home/andrea/adrive/data/training/summary/01.daily/**)`, e con quella
l'agente scrive al primo colpo. Il precedente era sotto gli occhi:
`.claude/settings.local.json` ha gia' un `Read(//opt/**)`.

Con uno slash la regola diventa `<repo>/home/andrea/...`, un percorso che non
esiste e che quindi non corrisponde a niente. Non e' un errore, e' una regola
che non si applica mai: da cui il silenzio.

### Cosa e' stato verificato

- **Il puntatore.** Prima che la cartella esistesse, l'import si fermava con
  `ConfigError: data.yaml: la cartella dei dati non esiste:
  /home/andrea/adrive/data/training`. E' il comportamento voluto.
- **Il trasloco**, a vuoto e poi davvero: 983 FIT in `fit/`, 4 JSON in
  `json/`, il database in `db/`, le 12 cartelle di `health/`, e `summary/`,
  `plan/`, `user/` dal repo. Nel repo restano solo codice, icone, todo,
  documentazione e `data.yaml`.
- **L'API**: 200 su `/docs`, `/api/sports`, `/api/activities`,
  `/api/daily/2026-10-27`, `/api/reports/daily/2026-10-27`,
  `/api/daily/2026-10-27/plan`, `/api/plans`, `/api/weekly/2026-10-26/plan` e
  `/icons/running.png`.
- **Le sei pagine** in Firefox headless — Day/Report, Day/Training,
  Day/Trend, Week/Snap, Week/Plan, Plan — tutte senza avvisi, con le icone
  servite.
- **L'agente scrive**, che era il punto: rifatta la sezione Training del 26
  ottobre, `done`, file scritto nella cartella nuova. E il testo usa il piano
  (todo 64): «Rest was what the plan asked for on this first Monday of the
  block (...) let tomorrow's easy 5 km be genuinely easy».
- **I comandi da terminale**: `training-daily-data --day 2026-10-27` rende il
  JSON, `training-fitness-status` legge e aggiorna la salute nella cartella
  nuova. Controllati dopo: nessuno dei JSON di `health/` e' illeggibile.
- Nessun `REPO_ROOT` punta piu' a dati: restano il puntatore, le icone e il
  `cwd` dei sottoprocessi.

### Cosa resta nella cartella vecchia

`~/adrive/data/garmin-export` non si cancella da sola, e lo script non la
tocca. Dentro restano i file di conflitto della sincronizzazione
(`activities.db.conflict1` e `2`, `activity_names.json.conflict1` e `2`,
`activity_types.json.conflict1` e `2`), due `.gpx`, un `.claude` e il vecchio
`.refresh.lock`. **Vanno guardati prima di cancellare**: in particolare
`activity_names.json.conflict1` ha 971 nomi di attivita' contro i 15 del file
vivo che e' stato traslocato. E' una cache (`make backfill_activity_names` la
rifa'), ma e' il segno che la sincronizzazione ha gia' mangiato un file in
quella cartella.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_65'$" --format=%H -1)
```

**Il revert del codice non riporta indietro i file.** I dati restano dove il
trasloco li ha messi, e il codice vecchio li cercherebbe nella disposizione di
prima. Per tornare davvero indietro servono anche i `mv` al contrario: i FIT e
i JSON dalla radice, il database dalla sua cartella, e `summary/`, `plan/`,
`user/` di nuovo nel repo.
