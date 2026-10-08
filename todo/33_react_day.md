---
status: todo
---

# La pagina Day in React

Quarto passo del piano del todo 32 ("Contesto: dove si va"), anticipato su
richiesta di Andrea il 2026-10-08: prima della suite di test (passo 2) e del
login (passo 3), per vedere presto la nuova interfaccia. L'API della Day c'e'
gia' (todo 32); qui si scrive il frontend che la usa.

Si crea `frontend/`: un'app React (TypeScript, Vite) con una sola pagina,
la **Day**, che fa quello che fa oggi la pagina Day di Streamlit
(`app_pages/activities.py`). Streamlit resta acceso e non cambia.

Non c'e' un mockup: il riferimento e' la pagina Streamlit di oggi, descritta
sotto. Dove questo todo non dice niente, si fa come lei.

## Cosa mostra la Day oggi

- **Filtri** in una riga: "Sport" (scelta multipla, "All" se vuota) e le
  date "From" / "To". Date invertite: un avviso al posto della tabella.
- **Due colonne 3:2.** A sinistra la tabella dei giorni, a destra il report
  giornaliero del giorno scelto.
- **Tabella**: una riga per attivita' e una riga vuota per ogni giorno senza
  attivita' (`with_empty_days`, todo 30), dalla piu' recente. Colonne: icona
  dello sport, data ("ddd D MMM YYYY"), ora ("HH:MM"), nome, km (1
  decimale), minuti (0 decimali), D+ (0 decimali). Alta dieci righe, poi
  scorre. Le righe vuote hanno l'icona del riposo (`icons/rest.png`), tranne
  oggi e tranne quando c'e' un filtro per sport. All'apertura e' scelta la
  prima riga con un'attivita', non la prima riga.
- **Scheda** sotto la tabella, nella colonna di sinistra, per la riga
  scelta: icona e "**Sport** — 07 Oct 2026, 12:28"; poi tre righe da tre
  metriche: Distance, Duration (hh:mm), Elevation ("+164 / -163 m"); Avg
  speed, Avg HR, VO2Max; i tre effetti stimati (hh:mm) e i due Training
  Effect di Garmin, ognuna solo se ha valori. Ogni metrica ha il suo testo di
  aiuto (`activity_detail.py`: si riprendono uguali). Giorno vuoto: "No
  activity on this day."
- **Report** a destra (`report_view.show_report`): le sezioni con l'icona
  accanto al titolo (`REPORT_SECTION_ICONS`), su fondo grigio
  semitrasparente, alto quanto tabella e scheda insieme. Senza file: "No
  daily report for this day.". C'e' anche per un giorno vuoto.
- **Sotto, a tutta larghezza**: il grafico a tre fasce e la mappa della
  traccia ("Route").

## Decisioni

- **Il grafico non si riscrive**: si mostra la specifica di
  `/api/activities/{id}/chart/vega` con `vega-embed`, con `theme` preso da
  `prefers-color-scheme`. I dati di `/chart` restano per dopo.
- **I tipi vengono dall'OpenAPI**: `openapi-typescript` genera
  `frontend/src/api/schema.ts` da `/openapi.json`. Il file generato sta nel
  repo, cosi' chi apre il progetto non deve avere l'API accesa per compilare.
  Nessun tipo scritto a mano per le risposte tipate. `/api/daily/{day}` non
  serve alla Day e non si usa.
- **Niente CORS**: in sviluppo Vite inoltra `/api` e `/icons` a
  `http://127.0.0.1:8000` (`server.proxy`). Il frontend usa solo percorsi
  relativi.
- **Una sola fonte per sport, etichette e icone**: l'API, non una copia in
  TypeScript (vedi "Work", parte API).
- **Data di partenza**: la Streamlit apre su tutto lo storico, qui si apre
  sugli ultimi 28 giorni fino a oggi (il default di `/api/activities`).
  Tutto lo storico sono quasi mille righe da scaricare a ogni apertura.
  Le date restano modificabili.
- **Solo locale**: Vite ascolta su `127.0.0.1`, come l'API.
- **Niente router, niente libreria di stato, niente libreria di
  componenti**: una pagina, `fetch` e `useState`/`useEffect`, CSS semplice
  con le variabili per il tema chiaro e scuro. Arriveranno quando le pagine
  saranno piu' di una.

## Work

### API (piccole aggiunte, in `training.api`)

- **Sport ed etichette fuori da Streamlit**: `SPORT_ICON_FILES`,
  `REST_ICON_FILE` e `sport_label` passano da `activity_table.py` (che
  importa Streamlit) a un modulo nuovo senza Streamlit,
  `interface/sports.py`. `activity_table.py` li importa da li'; le pagine
  Streamlit non cambiano.
- **`GET /api/sports`** -> lista di `Sport`: `sport`, `label`
  (`sport_label`), `icon` (il nome del file, o `null`), per ogni sport
  presente nelle attivita', in ordine alfabetico della chiave (come il
  filtro della Streamlit). La risposta e' `SportList`, con `sports` e
  `rest_icon` (il file dell'icona del riposo): il frontend non conosce
  nessun nome di file.
- **`/icons`**: la cartella `icons/` della radice del repo, servita in sola
  lettura con `StaticFiles` (percorso da `context.REPO_ROOT`, non dalla
  cartella corrente).
- **Icone delle sezioni del report**: `REPORT_SECTION_ICONS` passa da
  `report_view.py` a `report_text.py`, e `ReportSection` prende un campo
  `icon` (nome del file o `null`), con la stessa regola di
  `_report_icon_path` (il nome nel titolo, minuscolo).

### Frontend (`frontend/`)

- **Progetto Vite** React + TypeScript, `strict` acceso. Dipendenze:
  `react`, `react-dom`, `vega-embed` (con `vega` e `vega-lite`), `leaflet`,
  `react-leaflet`. Di sviluppo: `typescript`, `vite`, `@vitejs/plugin-react`,
  `@types/react`, `@types/react-dom`, `@types/leaflet`, `openapi-typescript`.
  `package-lock.json` nel repo; `node_modules/` e `dist/` in `.gitignore`.
- **Script npm**: `dev` (Vite su 127.0.0.1:5173), `build` (`tsc -b` e
  `vite build`), `typecheck`, `gen:api` (`openapi-typescript
  http://127.0.0.1:8000/openapi.json -o src/api/schema.ts`).
- **`src/api/`**: `schema.ts` (generato) e `client.ts`, una funzione per
  endpoint con i tipi di `schema.ts`, che lancia un errore sui codici non 2xx
  e rende `null` sui 404 dove il 404 vuol dire "non c'e'" (report, grafico).
- **Componenti**, uno per file, con i nomi della pagina Streamlit:
  `Filters`, `DayTable`, `ActivityCard`, `DailyReport`, `RunChart`,
  `RouteMap`, e `DayPage` che li compone.
  - `DayTable`: le righe vuote si costruiscono nel frontend dai giorni
    dell'intervallo (stessa regola di `with_empty_days`). Selezione con un
    click sulla riga e con le frecce su e giu'.
  - `ActivityCard`: i testi di aiuto come `title` (tooltip) o un'icona "?"
    con il testo al passaggio.
  - `DailyReport`: il testo e' Markdown, ma i report usano solo paragrafi,
    elenchi puntati e grassetto: bastano poche righe di conversione in
    elementi React, senza `react-markdown` (sarebbe una dipendenza in
    piu') e senza `dangerouslySetInnerHTML`.
  - `RouteMap`: Leaflet con le tessere di OpenStreetMap (come oggi
    `st.map` carica le sue da Carto: la traccia resta nel browser, alle
    tessere arriva solo la zona). Linea della traccia da `/route`. Senza
    punti, la mappa non c'e'.
- **Tema**: chiaro e scuro da `prefers-color-scheme`, con i colori in
  variabili CSS. Il riquadro del report con lo stesso grigio
  semitrasparente della Streamlit.
- **Larghezza**: le due colonne sopra i 900 px circa, una sotto l'altra
  sotto, con la tabella che scorre in orizzontale se serve.

### Repo

- **`Makefile`**: `frontend` (`cd frontend && npm run dev`) e
  `frontend_types` (`cd frontend && npm run gen:api`, con l'API accesa).
- **`README.md`**: nella sezione "API", come si lancia la Day in React
  (`make api` e `make frontend`, poi `http://127.0.0.1:5173`) e come si
  rigenerano i tipi.

## Vincoli

- Dipendenze nuove: solo quelle elencate qui. Lato Python nessuna.
- Le pagine Streamlit si vedono e si comportano come prima.
- Solo `GET` sull'API. Niente login, niente CORS.
- Commenti in italiano senza accenti, nel TypeScript come nel Python. Testi
  a schermo in inglese, come la Streamlit.
- `schema.ts` non si modifica a mano.

## Rischi

- **Altair e Vega-Lite**: la specifica di Altair 6 dichiara la versione di
  Vega-Lite nello `$schema`. `vega-lite` nel frontend deve essere della
  stessa versione principale, o il grafico non si disegna.
- **`width: "container"`**: i pannelli del grafico prendono la larghezza del
  contenitore. Il contenitore deve avere una larghezza definita al momento
  dell'`embed`, e il grafico si ridisegna quando cambia.
- **Le date**: l'API rende ore locali senza fuso
  (`2026-10-07T12:28:50`). `new Date(...)` le legge come locali, che e'
  giusto qui, ma i giorni (`2026-10-07`) `new Date` li legge in UTC: per i
  giorni si lavora sulle stringhe, non su `Date`.
- **Lo stato dell'OpenAPI**: se si cambia un modello e non si rigenera
  `schema.ts`, il frontend compila sui tipi vecchi. Da qui la verifica 3.

## Verifica

Non c'e' ancora una suite di test (passo 2 del piano). Con l'API accesa
(`make api`) e i dati locali:

1. API: `uv run python -c "import sys, training.api.app; assert 'streamlit'
   not in sys.modules"`. Con il `TestClient`: `/api/sports` contiene
   `running` con label "Running" e icona `running.png`, e `rock_climbing`
   con `climbing.png`; `/icons/running.png` risponde 200 con `image/png`;
   `/api/reports/daily/2026-10-07` ha `icon` `training.png` sulla sezione
   Training.
2. `cd frontend && npm ci && npm run build`: nessun errore, nessun avviso di
   TypeScript.
3. `npm run gen:api` e poi `git diff --exit-code frontend/src/api/schema.ts`:
   lo schema nel repo e' quello dell'API.
4. `make frontend` in background: `http://127.0.0.1:5173` risponde, e
   `http://127.0.0.1:5173/api/activities` passa dal proxy.
5. Nel browser (Claude in Chrome), su `http://127.0.0.1:5173`:
   - la tabella ha una riga per ogni giorno degli ultimi 28, la corsa
     "Canegrate - Rip_3x5" del 07/10/2026 con 6.8 km, 46 min, icona della
     corsa; il riposo ha la sua icona; oggi, se vuoto, no;
   - scelta la corsa: la scheda mostra Avg HR 136 bpm, Low aerobic (est.)
     00:31, High aerobic (est.) 00:14, Anaerobic (est.) 00:00, Aerobic
     TE 3.5, Anaerobic TE 0.4. L'anaerobico sono 30 s: `round` di Python
     arrotonda 0,5 al pari, quindi 00:00 nella Streamlit, mentre
     `Math.round` di JavaScript darebbe 00:01. Si arrotonda come la
     Streamlit;
   - a destra le cinque sezioni del report del 2026-10-07, con le icone;
   - sotto il grafico a tre fasce e la mappa con la traccia;
   - un giorno di riposo: "No activity on this day." e il suo report, se
     c'e';
   - con il filtro "Rock climbing" resta la sola seduta dell'08/10, e le
     righe vuote non hanno l'icona del riposo;
   - date invertite: l'avviso, nessun errore in console;
   - tema scuro (emulato): testo leggibile, grafico con la palette scura.
   Uno screenshot della pagina va nel report finale.
6. Streamlit: `uv run streamlit run src/training/interface/app.py
   --server.headless true` parte senza traceback; con `AppTest` la Day, la
   Week e la Month si disegnano senza eccezioni e la Day mostra ancora
   icone, scheda e report.
7. Tutti i server avviati per la verifica si fermano alla fine.
