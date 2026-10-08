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

Un'API in sola lettura (FastAPI) espone i dati della pagina Day: attivita',
dettaglio, dati e specifica Vega-Lite del grafico, traccia, i fatti del
giorno e il report giornaliero. Si lancia con:

```bash
make api
```

Ascolta solo su `http://127.0.0.1:8000`: non c'e' ancora il login, e sono
dati di salute. La documentazione interattiva e' su
`http://127.0.0.1:8000/docs`, lo schema OpenAPI su `/openapi.json`. Solo
`GET`: niente download da Garmin e niente scrittura di report.

### La pagina Day in React

`frontend/` e' la nuova interfaccia (React, TypeScript, Vite): per ora la
sola pagina Day, che chiede i dati all'API. Streamlit resta com'e'. Per
lanciarla servono l'API e Node.js:

```bash
cd frontend && npm ci   # la prima volta
make api                # in un terminale
make frontend           # in un altro, poi http://127.0.0.1:5173
```

In sviluppo Vite passa `/api` e `/icons` all'API, quindi non serve CORS.
I tipi delle risposte vengono dall'OpenAPI: dopo un cambio ai modelli
dell'API, con l'API accesa, `make frontend_types` rigenera
`frontend/src/api/schema.ts` (che non si modifica a mano).
