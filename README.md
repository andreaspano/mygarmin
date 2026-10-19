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
`GET`, niente download da Garmin e niente scrittura di report, tranne due
`PUT`: il terreno di un'attivita' a piedi (todo 35) e il tipo di una corsa
(todo 36).

### Il terreno delle attivita' a piedi

Corse, camminate ed escursioni hanno un terreno: `track`, `road`, `gravel`,
`trail` o `mountain`. L'API lo stima dal tipo dell'attivita' e dalla salita
per km (`src/training/interface/terrain.py`; strada quando i dati non
decidono, sterrato mai), e lo si corregge dalla scheda Training della Day in
React. Le correzioni stanno in `activity_terrain.json` nella cartella dati,
accanto a `activity_names.json`: `activities.db` non le contiene, e un
rebuild non le perde.

### Il tipo delle corse

Le corse (tapis roulant compreso) hanno un tipo: `race`, `intervals`,
`long`, `tempo` o `easy`. L'API lo stima dall'allenamento pianificato
salvato nel FIT e dalla durata (`src/training/interface/run_type.py`):
almeno due passi attivi sono ripetute, un solo passo attivo di almeno 10
minuti e' un tempo, senza allenamento da 100 minuti in su e' una lunga,
altrimenti facile. Gara non si stima mai. Lo si corregge dalla scheda
Training della Day in React; le correzioni stanno in `activity_run_type.json`
nella cartella dati, accanto a `activity_terrain.json`, e un rebuild non le
perde. I report non lo mostrano.

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
o che non sono completi (vedi sotto).
La soglia del lattato no: Garmin la da' solo il giorno in cui ne rileva una
nuova, quindi `make update_activity` tiene l'ultima in un file unico,
`health/lactate_threshold_latest.json`. La card Fitness la mostra dal giorno
in cui e' stata rilevata; prima, la frequenza di soglia salvata nei FIT. Il
report giornaliero non legge nessuna delle tre.

### La pagina Day in React

`frontend/` e' l'interfaccia (React, TypeScript, Vite), l'unica dal todo 40:
per ora la sola pagina Day, che chiede i dati all'API; le altre voci della
barra in alto arriveranno. Mostra un giorno alla volta (todo 34): la striscia della settimana, la seduta suggerita, i segnali
d'allarme, una griglia 2x2 con Health e Load sopra, Recovery e Fitness sotto
(todo 37), e l'allenamento con grafico e mappa. Fitness ha VO2max, endurance
score, hill score e soglia del lattato (todo 38), e non ha testo: il report
non ha una sezione Fitness. Il giorno sta nell'URL (`?day=2026-10-07`). I
testi vengono dal report giornaliero, i passi della seduta dalla sezione
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

Il tasto **Refresh** nell'intestazione (todo 41) aggiorna i dati e riscrive il
report del giorno mostrato: l'API lancia in background l'agente
`fitness-status` con `claude -p` (il comando `claude` deve essere nel `PATH`
di `make api`), che fa `make update_activity` e poi scrive il report. Ci
vogliono qualche minuto, un lavoro alla volta; alla fine la pagina si
ricarica. Il login a Garmin non si chiede mai dal tasto: con il token
scaduto il report si scrive sui dati locali e lo dice, e il login si rifa'
da terminale con `make update_activity`.
