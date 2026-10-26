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
giorno e il report giornaliero, piu' i piani di allenamento di `plan/`. Si
lancia con:

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

`frontend/` e' l'interfaccia (React, TypeScript, Vite), l'unica dal todo 40.
La barra in alto ha **due menu su due righe** (todo 55): sopra il periodo —
la **Day** e la **Week** — sotto che cosa se ne guarda, **Report** o
**Trend**. Sono due assi, non una fila sola: Activities non e' un periodo e
sta a destra, staccata e ancora grigia. Accanto a lei, a destra per lo stesso
motivo, c'e' **Plan**: un piano guarda avanti a una gara, non indietro a un
giorno. Month e Year si aggiungeranno quando esisteranno, non prima.

L'URL dice i due assi: `?period=` e `?view=`, piu' i parametri della pagina
(`?day=2026-10-07` per la Day, `?monday=2026-10-19` per la Week, `?days=90`
per l'ampiezza del Trend). Cambiando vista **il periodo resta**: da
Day/Report si clicca Trend e si resta sul giorno che si stava guardando. La
forma vecchia `?page=week` continua a valere, e senza niente si apre
Day/Report. Niente router di libreria: `URLSearchParams` e
`history.pushState` (`src/navigation.ts`).

Il **Trend** della Day (todo 55) disegna quello che il Report racconta: le
misure giorno per giorno nei cinque pannelli delle card, in una finestra che
si sceglie col cursore fra 5 e 365 giorni (28 di partenza, la stessa di
`BASELINE_LONG`). Un grafico **per misura** e non per pannello — dentro un
pannello le unita' non sono le stesse, e su un asse solo la linea bassa
verrebbe piatta — con la fascia di `_band` come sfondo, che si muove insieme
alla finestra. Sotto `MIN_BAND_DAYS` giorni misurati la fascia non c'e', e
la pagina lo dice; i giorni senza misura spezzano la linea invece di farle
attraversare il buco.

**Anche le tre intensita' del carico hanno la fascia di `_band`**, la stessa
che mostra la card Load: dove quel carico sta di solito, non il bersaglio di
Garmin. La domanda e' la stessa in tutta la pagina — questa misura e' nella
sua norma? — e il bersaglio rispondeva a un'altra, dove Garmin vorrebbe che
fosse. Il rapporto acuto/cronico, sempre come la card, di fascia non ne ha.

**Il mouse sul grafico accende una barra verticale grigia** sul giorno piu'
vicino, alta quanto il riquadro, e il tooltip dice quel giorno e il suo
valore. Il giorno lo sceglie una tassellatura sulla x (`nearest` nella
specifica), quindi si prende tutta la colonna: a 365 giorni, dove la linea
e' spessa due pixel e i pallini non ci sono, centrare il punto sarebbe un
gioco di mira.

**Un clic apre il Report di quel giorno** — lo stesso che la barra sta
indicando: il clic non guarda il segno colpito ma chiede alla scala che
giorno sia la sua x, **arrotondando al piu' vicino** come fa la barra. Il
tasto indietro torna al Trend, con la finestra di prima.

La **Week** mostra una settimana ISO (lunedi-domenica) con il suo titolo —
`Week 43 · October 2026`, dove il mese e' quello del **giovedi**, la regola
ISO per le settimane a cavallo — un selettore di otto settimane (numero,
lunedi e domenica), le quattro card, e le sedute con il grafico del lavoro
per sport. Un clic su una seduta apre la Day di quel giorno, e **ogni card
porta il testo della sua sezione del report settimanale** (todo 53), con
l'ora e il tasto per rifarla, come nella Day.

Le fasce della Week **non sono quelle della Day**: qui il valore della
settimana si confronta con le **12 settimane precedenti** (todo 52), e ne
bastano sei misurate. Attorno a una media settimanale una fascia a 28 giorni
non direbbe niente: sette giorni oscillano molto meno di uno, e il valore
cadrebbe quasi sempre dentro. Health e Recovery sono medie dei sette giorni,
Fitness lo stato di fine settimana — la forma e' uno stato, non una cosa da
mediare.

**Nella Week ogni numero e' della settimana** (todo 54), bande comprese. La
card Load lo e' diventata per ultima: mostrava i tre carichi per effetto di
Garmin, che sono finestre di **28 giorni**, e due settimane vicine ne
condividono tre quarti — si somigliavano per forza. Adesso mostra il carico
dei sette giorni (`load_acute`, che letto alla domenica e' esattamente
lunedi-domenica) e il **tempo passato nelle tre fasce di sforzo**, contato
dalla frequenza cardiaca di ogni seduta con i confini di **quella** seduta:
una soglia alzata a settembre non riscrive i minuti di agosto. I minuti
stanno in tre colonne di `activities`, calcolate dai record a ogni `sync()`
e rifacibili con `make backfill_zones`: ricalcolarli a ogni richiesta
costerebbe un decimo di secondo per settimana.

Il carico e i minuti non raccontano sempre la stessa settimana, ed e'
voluto: le sedute senza fascia cardiaca stanno nel carico (Garmin le stima)
e non nei minuti. Quante sono lo dice `zones.sessions_without_hr`, e la card
lo scrive quando capita. Il carico cronico e il rapporto fra i due restano
nella Day, dove il mese e' il contesto giusto per un giorno.

La **Day** mostra un giorno alla volta (todo 34): la striscia della settimana,
la seduta suggerita e il verdetto del giorno, una griglia 2x2 con Health e
Load sopra, Recovery e Fitness sotto (todo 37), e l'allenamento con grafico e
mappa. **Tutte e quattro le card hanno la stessa forma**: le misure, ognuna
con la barra della sua fascia e il valore di oggi come tacca, e niente testo
accanto ne' sotto il numero. Qualche misura la fascia non ce l'ha, e allora e'
un numero nudo: la soglia del lattato, il rapporto di carico, la quota e il
caldo a cui sei acclimatato. La fascia pero' non vuol dire la stessa cosa
dappertutto: in Health e Recovery e' la media dei 28 giorni prima piu' e meno
uno scarto tipo (in tinta chiara piu' e meno due), e uscirne e' un segnale; in
Fitness e' la stessa media ma **sopra vuol dire che stai migliorando**; in
Load e' di nuovo la stessa media, e dice quanto di quel tipo di lavoro stai
portando rispetto al solito.
Ogni card ha il testo della sua sezione del report giornaliero, l'ora in cui
e' stato scritto e un tasto che la rifa' da sola (todo 44 e 47); i passi della
seduta vengono dalla sezione Next.

Per lanciarla servono l'API e Node.js:

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

### I piani di allenamento

In `plan/` stanno i piani scritti a mano: un file Markdown per piano, e la
pagina **Plan** li mostra tutti, la gara piu' vicina per prima. Nessun elenco
nel codice — un file nuovo nella cartella si vede ricaricando la pagina — e
nessun agente: questi li scrive una persona, mentre `summary/` lo riscrivono
gli agenti. Per questo `plan/` sta nel repo e `summary/` no.

Davanti al testo c'e' un front matter YAML, nello spirito del todo 14 ma per
un blocco intero invece che per una settimana: le chiavi dicono la gara, non
le sedute.

```yaml
---
race: 2027-02-28
race_name: mezza maratona (da scegliere)
distance_km: 21.097
target_time: "2:20:00"
target_pace_min_km: "6:38"
target_speed_kmh: 9.04
block_start: 2026-10-26
block_weeks: 18
peak_weekly_km: 46
---
```

Da quelle chiavi la pagina ricava i riquadri in cima (la gara, quanti giorni
mancano, il bersaglio, il ritmo, la velocita', la settimana piu' pesante);
tutto il resto e' il testo. **Il front matter non e' obbligatorio**: un file
che non ce l'ha si vede comunque, col solo testo e i riquadri vuoti. Un piano
invisibile perche' gli manca una chiave sarebbe peggio di un piano senza
numeri. I bersagli con i due punti vanno fra apici, se no YAML li legge come
minuti.

Il titolo non sta nel front matter: e' il primo `# ...` del testo, che la
pagina si prende per la sua intestazione e toglie dal corpo. Senza titolo
resta il nome del file.

Due endpoint, entrambi in sola lettura: `GET /api/plans` da' l'elenco senza i
testi, quello che serve al selettore, e `GET /api/plans/<slug>` un piano col
suo Markdown. Lo `slug` e' il nome del file senza `.md` (`?plan=` nell'URL), e
si cerca fra i file trovati invece di essere attaccato a un percorso: non puo'
uscire da `plan/`.

Il Markdown dei piani ha **titoli e tabelle**, che i report non hanno — un
piano e' quasi tutto tabelle, le settimane e i ritmi — e `src/markdown.tsx` li
converte come il resto, senza una libreria in piu'. Le tabelle larghe scorrono
da sole dentro il loro riquadro: scorre la tabella, non la pagina.

### Il piano dentro i report

I piani di `plan/` sono il blocco; le sedute giorno per giorno stanno in
`summary/05.plan/`, un file per settimana col nome del lunedi', col front
matter del todo 14 e la tabella dei sette giorni. Il formato e' documentato in
`summary/05.plan/README.md`.

**Next li legge.** Quando esiste il file della settimana per cui sta
prescrivendo, l'orchestratore (`_week_plan` in `api/refresh.py`) lo nomina nel
prompt, e per l'agente la seduta prevista e' il punto di partenza: la
prescrive com'e' se le sezioni sono d'accordo, la cambia se non lo sono — e
allora **deve dire cosa ha cambiato e perche'**. Una settimana che si discosta
dal piano in silenzio e' un piano che nessuno segue.

La data che conta non e' quella del report: **il Next della sera parla di
domani**, e quello della settimana della settimana che comincia il giorno dopo
(`_next_subject`). La domenica sera la riga da leggere sta quindi nel file
della settimana successiva, non in quello del report. Le altre sezioni il
piano non lo vedono: raccontano com'e' andata, e quello che era previsto non
cambia i loro numeri.

Nessun file, nessuna frase nel prompt: i giorni fuori da un blocco si
scrivono come prima, dalle sole sezioni.

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

### Il report della settimana

Dal todo 53 anche la settimana ha il suo report, otto sezioni come il giorno,
in `summary/02.weekly/<lunedi>/`. Lo scrivono sette agenti — `w1_health` ...
`w7_summary` — che sono **altri** da quelli del giorno: i prompt del giorno
parlano di stamattina e della seduta di ieri, e non si riusano. Il ciclo che
li lancia invece e' lo stesso, parametrato su `sections.Report`
(`api/sections.py`).

Due giri, agganciati a quelli del giorno:

| | quando | sezioni |
|---|---|---|
| apertura | lunedi, 10:00 | summary_start |
| chiusura | domenica, 22:00 | health, recovery, load, fitness, training, next, summary_end |

**Il lunedi scrive una sezione sola**, e non e' una dimenticanza: una
settimana al primo giorno non ha numeri da commentare. Chi apre non guarda i
numeri di questa settimana — guarda **come ci arrivi**, e lo legge nel
report della settimana prima, scritto la sera avanti. Tutto il resto si
scrive la domenica, quando i sette giorni ci sono.

Come nel giorno, il verdetto e' in due pezzi e il secondo legge il primo:
l'apertura del lunedi e la chiusura della domenica stanno una sopra l'altra
nel riquadro Summary. **Next e' solo la strategia** dei sette giorni che
vengono — quante sedute, di che tipo, dove l'intensita' e dove il lungo — e
si scrive la domenica sera, per la settimana che comincia il giorno dopo.

Il settimanale **non scarica mai**: gira in coda al giro del giorno, che ha
appena chiamato Garmin.

```bash
make weekly_report                      # la settimana di oggi
make weekly_report WEEK=2026-10-12      # un lunedi' a scelta
make weekly_report SECTION=health       # solo una sezione
```

### Riscrivere lo storico

I report vecchi non si aggiornano da soli quando le card cambiano, e dal
todo 44 in poi sono cambiate molto. `--from` (todo 50) riscrive un
intervallo invece di un periodo solo, e vale per tutti e due i comandi:

```bash
make backfill_reports FROM=2026-09-01 TO=2026-09-07    # una settimana di giorni
make backfill_reports FROM=2026-08-01                  # fino a oggi
make backfill_weeks FROM=2026-08-03                    # le settimane, FROM e TO lunedi'
```

Tre regole, e sono quelle che lo rendono ripetibile:

- **Salta le sezioni che ci sono gia'**, non i periodi: un backfill
  interrotto riprende da dove si era fermato, e rilanciarlo su un periodo
  gia' fatto costa qualche secondo. Per rifare da capo ci sono `--day` /
  `--week` con `--section`.
- **Non scarica niente**: i dati storici sono gia' su disco.
- **Se trova il lock occupato si ferma** e lo dice. I giri dei timer hanno
  la precedenza: il backfill si rilancia dopo, e riprende da li'.

I giri non sono quelli dei timer, perche' qui il periodo e' finito: il
giorno si scrive in tre passate (le card e Next con la voce della sera, poi
il sole, poi la luna che legge il sole), la settimana in due (prima la
chiusura, poi l'apertura). L'apertura di una settimana legge il report di
quella **precedente**: se non c'e' ancora, si salta e la scrive il
rilancio dopo, quando c'e'.

**Sono ore di agenti**: otto sezioni per giorno, a una ventina di secondi
l'una, fanno circa tre ore e mezza per gli ottanta giorni da agosto; le
settimane mezz'ora. Si lancia quando non c'e' altro in corso.

### Le righe di cron

I giri sono righe di **cron**, in `deploy/crontab`:

```bash
make install_cron            # le mette nel tuo crontab, ripetibile
make uninstall_cron          # le toglie
crontab -l | grep mygarmin   # cosa c'e' adesso
tail -f ~/.local/state/mygarmin-report.log   # com'e' andata
```

Le righe sono quattro e non due: il lunedi e la domenica il giro del giorno
**si tira dietro la settimana**, nella stessa riga e con un `;` in mezzo. Il
settimanale deve girare dopo il giornaliero, perche' il lock ne lascia
passare uno solo e chi lo trova occupato se ne va senza fare niente; con due
righe a orari diversi bisognerebbe indovinare quanto dura il primo. Il `;` e
non `&&`, cosi' una sezione del giorno che fallisce non si porta via anche
la settimana.

L'installazione toglie le righe che ha messo l'ultima volta (le riconosce dal
marcatore `# mygarmin` in fondo) e rimette queste: il resto del crontab non
si tocca. Cron da' un `PATH` scarno (`/usr/bin:/bin`), dove `make` e `claude`
ci sono ma `uv` no, e **non basta scrivere `uv` per intero**: dentro il
lavoro c'e' un `make update_activity` che a sua volta chiama `uv run`. Per
questo le righe allargano il `PATH` con la cartella di `uv`. I primi due giri
automatici sbagliarono proprio qui: i report furono scritti, ma sui dati
vecchi.

Prima erano due timer di systemd (todo 47), con il vantaggio di recuperare un
giro saltato a macchina spenta. Su questa macchina, accesa sempre e mai
sospesa, quel vantaggio non valeva il prezzo: i timer utente girano solo
finche' sei collegato, a meno di `loginctl enable-linger`. **Cron non ha
quel problema** — in cambio non recupera i giri saltati, e l'output va nel
file qui sopra invece che nel journal.

Un lavoro alla volta vale anche fra processi diversi, con un lock su file in
`<dati>/.refresh.lock`: se un giro parte mentre premi Refresh, il secondo se
ne va senza fare niente.
