# mygarmin

## Configurazione

Tutta la configurazione sta in `user/config.yaml`: la cartella dei dati, il
token di login, il fuso orario, l'inizio dello storico, la pausa fra le
richieste a Garmin e le finestre in giorni. Cosa fa ogni chiave e' scritto nei
commenti del file.

Tutte le chiavi sono obbligatorie e non ci sono default nel codice: se il file
manca, se manca una chiave, se ce n'e' una sconosciuta o un valore e' del tipo
sbagliato, il programma si ferma all'avvio con un `ConfigError` che elenca
tutti i problemi insieme. Il file si cerca sempre nella radice del repo,
qualunque sia la cartella da cui si lancia il comando.

## API

Un'API (FastAPI) espone i dati della pagina Day: attivita',
dettaglio, dati e specifica Vega-Lite del grafico, traccia, i fatti del
giorno e il report giornaliero. Si lancia con:

```bash
make api
```

Ascolta solo su `http://127.0.0.1:8000`: non c'e' ancora il login, e sono
dati di salute. La documentazione interattiva e' su
`http://127.0.0.1:8000/docs`, lo schema OpenAPI su `/openapi.json`. Tutto
`GET` tranne tre endpoint: il `PUT` del terreno di un'attivita' a piedi (todo
35), il `PUT` del tipo di una corsa (todo 36) e la `POST` del tasto Refresh
(todo 41), la sola che scarica da Garmin e riscrive un report.

### Il terreno delle attivita' a piedi

Corse, camminate ed escursioni hanno un terreno: `track`, `road`, `gravel`,
`trail` o `mountain`. L'API lo stima dal tipo dell'attivita' e dalla salita
per km (`src/training/interface/terrain.py`; strada quando i dati non
decidono, sterrato mai), e lo si corregge dalla scheda Training della Day in
React. Le correzioni stanno in `activity_terrain.json` nella cartella dati,
accanto a `activity_names.json`: `activities.db` non le contiene, e un
rebuild non le perde.

### Il tipo delle corse

Le corse hanno un tipo: `race`, `intervals`, `long`, `tempo` o `easy`. L'API
lo stima dall'allenamento pianificato salvato nel FIT e dalla durata
(`src/training/interface/run_type.py`): almeno due passi attivi sono ripetute,
un solo passo attivo di almeno 10 minuti e' un tempo, senza allenamento da 100
minuti in su e' una lunga, altrimenti facile. Gara non si stima mai. Lo si
corregge dalla scheda Training della Day in React; le correzioni stanno in
`activity_run_type.json` nella cartella dati, accanto a
`activity_terrain.json`, e un rebuild non le perde. Il report giornaliero lo
usa nella sezione Training (todo 43): e' il metro con cui l'allenatore giudica
la seduta, perche' dice che seduta voleva essere.

### Il tapis roulant e' uno sport, non una corsa

Dal todo 45 una seduta sul nastro ha `sport = treadmill`: si misurano tempo,
battito, potenza e calorie, e **non ha un concetto di distanza**. La distanza
che l'orologio registra la stima dal polso e in salita sbaglia di molto (una
seduta a 15% di pendenza torna con tre chilometri e una media da
passeggiata), quindi resta in `activities.db` ma non la mostra ne' la somma
nessuno: l'API la manda a `null` insieme alla velocita' media, i fatti del
giorno la marcano `distance_unreliable`, e il prompt dell'agente Training ha
l'ordine di non nominare ne' distanza ne' passo. Niente terreno e niente tipo
di corsa, per lo stesso motivo. Lo sport si riconosce dal `sub_sport` del FIT
(lo scrive il profilo dell'orologio) prima che dal tipo di Garmin Connect:
delle 23 sedute dello storico una sola ha un tipo su Connect.

### I file di salute di un giorno

`make update_activity`, `make backfill_health` e `make backfill` scaricano un
file per giorno e per endpoint in `health/`. Un file conta come completo solo
se e' stato salvato dopo la fine del suo giorno: uno salvato durante il
giorno non ha quello che Garmin aggiorna dopo (il VO2max e il carico dopo una
corsa della sera, il body battery piu' basso, lo stress del giorno), e si
riscarica al giro dopo (todo 39). Oggi si riscarica sempre; un giorno rimasto
a meta' piu' vecchio della finestra di `update_activity` (3 giorni) si
sistema con `make backfill_health`.

### Endurance score, hill score e soglia del lattato

Endurance e hill score si scaricano ogni giorno con il resto della salute
(`health/endurance_score/` e `health/hill_score/`); per lo storico, dopo il
primo aggiornamento, `make backfill_health` scarica solo i file che mancano
o che non sono completi (vedi sopra).
La soglia del lattato no: Garmin la da' solo il giorno in cui ne rileva una
nuova, quindi `make update_activity` tiene l'ultima in un file unico,
`health/lactate_threshold_latest.json`. La card Fitness la mostra dal giorno
in cui e' stata rilevata; prima, la frequenza di soglia salvata nei FIT. Il
report giornaliero non legge nessuna delle tre.

### La pagina Day in React

`frontend/` e' l'interfaccia (React, TypeScript, Vite), l'unica dal todo 40:
per ora la sola pagina Day, che chiede i dati all'API; le altre voci della
barra in alto arriveranno. Mostra un giorno alla volta (todo 34): la striscia
della settimana, la seduta suggerita e il verdetto del giorno, una griglia 2x2
con Health e Load sopra, Recovery e Fitness sotto (todo 37), e l'allenamento
con grafico e mappa. **Tutte e quattro hanno la stessa forma**: le misure,
ognuna con la barra della sua fascia e il valore di oggi come tacca, e niente
testo accanto ne' sotto il numero. Qualche misura la fascia non ce l'ha, e
allora e' un numero nudo: la soglia del lattato, il rapporto di carico, la
quota e il caldo a cui sei acclimatato. La fascia pero' non vuol dire la stessa cosa
dappertutto: in Health e Recovery e' la media dei 28 giorni prima piu' e meno
uno scarto tipo (in tinta chiara piu' e meno due), e uscirne e' un segnale; in
Fitness e' la stessa media ma **sopra vuol dire che stai migliorando**; in
Load e' il **bersaglio di Garmin**, non una media tua, e ha un livello solo.
Il giorno sta nell'URL (`?day=2026-10-07`). Ogni card ha il testo della sua
sezione del report giornaliero, l'ora in cui e' stato scritto e un tasto che
la rifa' da sola (todo 44 e 47); i passi della seduta vengono dalla sezione
Next. Per lanciarla servono l'API e Node.js:

```bash
cd frontend && npm ci   # la prima volta
make api                # in un terminale
make frontend           # in un altro, poi http://127.0.0.1:5173
```

In sviluppo Vite passa `/api` e `/icons` all'API, quindi non serve CORS.

Vite ascolta solo su 127.0.0.1. Per aprire la pagina dalle altre macchine
della tailnet, su mutolo si lascia a `tailscale serve` l'indirizzo Tailscale,
una volta sola (la configurazione resta anche dopo il riavvio):

```bash
sudo tailscale set --operator=$USER                            # una volta, per non rifare sudo
tailscale serve --bg --http=5173 http://127.0.0.1:5173         # poi http://mutolo:5173
```

Da li' in poi basta `make api` e `make frontend` su mutolo. L'API resta su
127.0.0.1: dalla tailnet passa solo la pagina. Con `tailscale serve status`
si vede la configurazione, con `tailscale serve reset` si spegne.

I tipi delle risposte vengono dall'OpenAPI: dopo un cambio ai modelli
dell'API, con l'API accesa, `make frontend_types` rigenera
`frontend/src/api/schema.ts` (che non si modifica a mano).

Il tasto **Refresh** nell'intestazione (todo 41) aggiorna i dati e rifa' il
report del giorno mostrato. Dal todo 44 il report non lo scrive un agente
solo: ogni sezione ha il suo (`01_health`, `02_load`, `03_recovery`,
`04_fitness`, `05_training`, e poi `06_next` e `07_summary`, che leggono
quello che hanno concluso gli altri), e ognuno scrive il suo file in
`summary/01.daily/<giorno>/`. L'API li lancia **uno alla volta** con
`claude -p` (il comando `claude` deve essere nel `PATH` di `make api`), dopo
aver scaricato i dati e preparato i fatti una volta sola: circa due minuti in
tutto. Le regole che gli agenti condividono stanno in
`.claude/agents/_style.md`.

Ogni card ha anche **un tasto suo**, che rifa' solo quella sezione: una
sessione invece di sette quando si vuole ritoccare un testo. Una sezione che
fallisce tiene il testo che aveva e le altre si riscrivono lo stesso; il
tasto di quella sezione lo segnala.

Lo stesso lavoro si fa da terminale, senza l'API:

```bash
make daily_report                   # oggi, tutte le sezioni
make daily_report DAY=2026-10-07    # un giorno a scelta
make daily_report SECTION=health    # solo una sezione
```

Il login a Garmin non si chiede mai dal tasto: con il token scaduto il
report si scrive sui dati locali **e la pagina lo dice**, e il login si rifa'
da terminale con `make update_activity`. I report scritti prima del todo 44
stanno ancora nel file unico `summary/01.daily/<giorno>.md` e si continuano a
leggere da li'.

### I due giri dei timer

Dal todo 47 il report si scrive da solo due volte al giorno, e i due giri non
sono uguali:

| | ore | sezioni |
|---|---|---|
| mattina | 10:00 | health, recovery, load, fitness, next, summary_morning |
| sera | 22:00 | load, fitness, training, next, summary_evening |

Health e Recovery solo la mattina, perche' sono le misure della notte appena
finita e alle 22 racconterebbero la stessa notte; Training solo la sera,
perche' alle 10 non c'e' ancora niente da commentare.

**Il verdetto del giorno e' in due pezzi** (todo 49), scritti dallo stesso
agente nei due giri: il **sole** la mattina, la **luna** la sera, uno sopra
l'altro nel riquadro Summary. La mattina si vede solo il sole, perche' la
luna non esiste ancora. La luna legge il sole e chiude il cerchio — "il
mattino diceva di tenerla facile, e l'hai tenuta facile" — senza ripeterlo.

Gli agenti sanno **che giro e'**: la mattina Next propone la seduta per oggi
e il Summary giudica la giornata che comincia, la sera Next guarda a domani
e il Summary dice com'e' andata. Il momento si ricava dall'orologio
(`EVENING_FROM_HOUR` in `api/sections.py`), quindi vale anche per il tasto
della pagina, che pero' continua a rifare **tutte** le sezioni: il momento
decide come parla il testo, l'insieme decide chi gira.

Siccome ogni sezione porta la sua ora, le card ne mostrano una sotto il
testo: dopo il giro della sera le ore sono diverse, ed e' giusto che si veda.

I due giri sono righe di **cron**, in `deploy/crontab`:

```bash
make install_cron            # le mette nel tuo crontab, ripetibile
make uninstall_cron          # le toglie
crontab -l | grep mygarmin   # cosa c'e' adesso
tail -f ~/.local/state/mygarmin-report.log   # com'e' andata
```

L'installazione toglie le righe che ha messo l'ultima volta (le riconosce dal
marcatore `# mygarmin` in fondo) e rimette queste: il resto del crontab non
si tocca. `uv` va scritto per intero perche' cron da' un `PATH` scarno
(`/usr/bin:/bin`); `make` e `claude`, che servono dopo, stanno li'.

Prima erano due timer di systemd (todo 47), con il vantaggio di recuperare un
giro saltato a macchina spenta. Su questa macchina, accesa sempre e mai
sospesa, quel vantaggio non valeva il prezzo: i timer utente girano solo
finche' sei collegato, a meno di `loginctl enable-linger`. **Cron non ha
quel problema** — in cambio non recupera i giri saltati, e l'output va nel
file qui sopra invece che nel journal.

Un lavoro alla volta vale anche fra processi diversi, con un lock su file in
`<dati>/.refresh.lock`: se un giro parte mentre premi Refresh, il secondo se
ne va senza fare niente.
