---
status: todo
---

# La pagina Day in React, nuovo impianto

La Day in React del todo 33 rifa' la pagina Streamlit: filtri, tabella dei
giorni, scheda, report a destra, grafico e mappa sotto. Qui la si ridisegna
sul mockup di Andrea, `todo/assets/34_day_mockup.jpeg` (copiato da `~/ui.jpeg` il
2026-10-09), con le correzioni decise commentandolo. Dove questo todo non
dice niente, si fa come il mockup; dove il mockup e questo todo non sono
d'accordo, vale il todo.

Streamlit resta com'e'. Cambiano il frontend, poco l'API e un poco il
formato del report giornaliero (sezione "Next").

## Cosa mostra il mockup

Dall'alto in basso, un giorno alla volta (non piu' un intervallo di date):

- **Barra in alto**: "Training" e le schede Day, Week, Month, Recovery,
  Activities. A destra "Profile".
- **Intestazione del giorno**: la data grande ("Wednesday 7 October"),
  frecce giorno prima / dopo, "Today", "Pick a date". A destra la
  **striscia della settimana**: gli ultimi otto giorni fino a oggi, ognuno
  con giorno, numero, icona dello sport (o del riposo) e km; il giorno
  scelto in un riquadro, oggi tratteggiato con "today".
- **Riquadro scuro "Next"**: "NEXT · TOMORROW", un titolo ("Run easy"), il
  perche' in due righe, e a destra "Example session" con i passi della
  seduta come chip.
- **"This morning"**, con il badge "No warning signs":
  - RECOVERY: Readiness, Sleep ("8h04", punteggio e notti sotto le 7 h),
    Body battery al risveglio; sotto il testo della sezione Recovery;
  - HEALTH: FC a riposo, HRV media settimanale con la fascia equilibrata
    disegnata, respirazione nel sonno, stress di ieri; sotto il testo della
    sezione Health.
- **"Load"** a destra: un titolo ("In a healthy range"), il testo, il
  bilancio del lavoro (low aerobic, high aerobic, anaerobic), giorni di
  riposo negli ultimi 7, ultima seduta dura, VO2max con la variazione a 28
  giorni.
- **"Training"**: icona, nome, sport, ora e giorni di riposo prima;
  Distance, Duration, Elevation, Average speed, Average heart rate (con la
  massima); la barra "Where the 46 minutes went" con i minuti per effetto;
  a destra il commento e i due Training Effect come barre da 0 a 5;
  "Open the route map". Sotto il grafico a tre fasce, con le zone
  etichettate in alto (nome e FC media del tratto) e la linea "high
  aerobic above this line".

## Decisioni

Prese commentando il mockup il 2026-10-09:

- **Il rosa una volta sola.** Nel mockup il rosa e' sia "anaerobic" sia
  "downhill". La discesa nella fascia della pendenza prende un altro colore
  (un grigio caldo), in entrambi i temi.
- **Contrasto del low aerobic.** Il viola chiaro delle barre si perde sullo
  sfondo viola delle zone Z4. Si schiarisce lo sfondo delle zone o si scurisce
  il low aerobic, finche' le barre si distinguono anche nelle ripetute
  (controllo a occhio sullo screenshot del 07/10, verifica 5).
- **Load con i numeri.** Il bilancio del lavoro non e' solo a parole: tre
  barre da `load.now.load_aerobic_low`, `load_aerobic_high` e
  `load_anaerobic` di `/api/daily/{day}`. Se i JSON di salute hanno anche le
  fasce obiettivo di Garmin, si disegnano sulle barre; se non le hanno,
  barre senza fascia e le parole del mockup come etichetta. Titolo e testo
  vengono dalla sezione Load del report.
- **Piu' attivita' nello stesso giorno.** Il mockup ne mostra una; venerdi'
  02/10 ne ha due (corsa e camminata), l'08/10 l'arrampicata dopo il
  lavoro. Il riquadro Training ha una riga di linguette, una per attivita'
  (icona e ora), sopra la scheda; con una sola attivita' le linguette non
  ci sono. Giorno senza attivita': il riquadro dice "Rest day" e non ha
  grafico.
- **I chip della seduta vengono dal report, non dal testo libero.** Il
  report giornaliero cambia nella sola sezione "Next": prima riga un titolo
  in grassetto da solo ("**High aerobic run**"), poi il perche' in un
  paragrafo, poi i passi della seduta come elenco puntato, un passo per
  voce, corti ("15 min easy under 142 bpm"). Il frontend usa il titolo come
  titolo del riquadro e le voci come chip. Report vecchi senza titolo o
  senza elenco: titolo "Next" e nessun chip, il testo com'e'.
- **"Profile" non c'e'.** Login e utenti non esistono ancora (passo 3 del
  piano del todo 32): niente avatar finche' non servono.
- **Schede in alto**: c'e' solo la Day. Week, Month, Recovery e Activities
  si mostrano disattivate (non cliccabili), per dare la forma della barra.
- **Unita' sugli assi.** Il pannello della velocita' ha "km/h" sull'asse,
  non solo in legenda.
- **Mappa**: "Open the route map" apre la mappa sotto il grafico (la stessa
  `RouteMap` di oggi), non una pagina nuova.
- **Larghezza**: sotto i 900 px circa "This morning" e "Load" vanno uno
  sotto l'altro, le metriche vanno a capo, la striscia della settimana
  scorre in orizzontale. Il grafico resta a tutta larghezza.
- **Niente filtri per sport e intervallo**: la Day e' un giorno. La tabella
  dei giorni del todo 33 sparisce dalla Day (tornera' nella pagina
  Activities).

## Work

### Report giornaliero

- `.claude/agents/fitness-status.md`: il formato nuovo della sezione
  "Next" (vedi Decisioni), con un esempio.
- Nello stesso file, la voce `effect_minutes` dice ancora "`null` when the
  watch saved no anaerobic threshold": dal commit b7bc8e5 le attivita' da
  agosto 2026 prendono la soglia dell'ultima corsa
  (`db.THRESHOLD_FALLBACK_FROM`). Si aggiorna.
- `report_text.parse_report` non cambia: titolo in grassetto ed elenco li
  separa il frontend dal corpo della sezione.

### API

- **Settimana**: la striscia vuole gli otto giorni con sport e km. Si
  usa `/api/activities` con `start`/`end` sugli otto giorni; se manca
  qualcosa (l'icona per giorno con piu' attivita'), si aggiunge li', non un
  endpoint nuovo.
- **`/api/daily/{day}` tipato**: oggi non ha `response_model` e il frontend
  non ha i suoi tipi. Si aggiungono i modelli Pydantic per le parti che la
  pagina usa (`morning`, `alerts`, `load`, `recent`, `sleep_last_7`), si
  rigenera `schema.ts` (`make frontend_types`).
- **Grafico**: colore della discesa, contrasto delle zone e unita' sull'asse
  della velocita' si cambiano in `run_chart.py`, che serve anche la
  Streamlit: si cambia la palette per entrambi, non una copia per React.

### Frontend

- Componenti nuovi: `TopBar`, `DayHeader` (data, frecce, "Today",
  scelta della data con `<input type="date">`), `WeekStrip`, `NextCard`,
  `MorningCard`, `LoadCard`, `TrainingCard` (linguette, scheda, barra degli
  effetti, Training Effect, grafico, mappa). `DayPage` li compone.
- Si tolgono dalla Day `Filters` e `DayTable` (i file restano se servono
  ad Activities, altrimenti si cancellano).
- Il giorno scelto sta nell'URL (`?day=2026-10-07`), cosi' un giorno si
  apre da un link e il tasto indietro funziona. Senza router: `URLSearchParams`
  e `history.pushState`.
- I testi delle sezioni del report vanno nei riquadri: Recovery e Health in
  "This morning", Load in "Load", Next nel riquadro scuro, Training come
  commento nella scheda. Senza report: i numeri restano, i testi no, e una
  riga "No daily report for this day."

## Vincoli

- Nessuna dipendenza nuova, ne' nel frontend ne' in Python.
- Le pagine Streamlit si comportano come prima; cambiano solo i colori del
  grafico (discesa, zone) e l'unita' sull'asse.
- Solo `GET` sull'API. Niente login.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Ogni numero a schermo viene dall'API: il frontend non calcola medie ne'
  conta giorni (come l'agente del report).

## Rischi

- **Report vecchi**: i report fino al 2026-10-09 hanno la sezione Next senza
  titolo ne' elenco. Devono restare leggibili (verifica 5).
- **Fasce obiettivo del carico**: possono non esserci nei JSON di salute;
  in quel caso le barre restano senza fascia, non si inventano.
- **Grafico condiviso**: i colori nuovi valgono anche in Streamlit; uno
  screenshot di entrambi nel report finale.

## Verifica

Con l'API accesa e i dati locali:

1. `cd frontend && npm run build`: nessun errore ne' avviso TypeScript.
2. `npm run gen:api` e `git diff --exit-code frontend/src/api/schema.ts`.
3. Con il `TestClient`: `/api/daily/2026-10-07` risponde con lo schema
   nuovo e `load.now.load_aerobic_low` 1421.0.
4. Un report scritto con l'agente aggiornato (per il giorno della verifica)
   ha la sezione Next con titolo in grassetto ed elenco.
5. Nel browser (Claude in Chrome), su `http://127.0.0.1:5173/?day=2026-10-07`:
   - intestazione "Wednesday 7 October", la striscia con la corsa del 07/10
     (6.8 km) evidenziata, venerdi' 02/10 con due attivita';
   - il riquadro Next con il testo del report del 07/10, senza chip (report
     vecchio);
   - This morning: Readiness 76, Sleep "8h" e minuti (nel JSON di oggi
     `sleep_hours` e' 8.1, arrotondato: i minuti esatti, se servono, li
     da' l'API, non si ricavano da 8.1), Body battery 87, FC a riposo
     50, HRV 45 con la fascia 44-55, badge "No warning signs";
   - Load con le tre barre e VO2max 41.4 (+1.6);
   - Training: "Canegrate - Rip_3x5", barra 31 / 14 / 0.5 min, Aerobic
     3.5, Anaerobic 0.4, grafico con la discesa non rosa e "km/h"
     sull'asse;
   - `?day=2026-10-02`: due linguette; `?day=2026-10-06`: "Rest day";
   - il giorno della verifica: chip dal report nuovo (verifica 4);
   - frecce, "Today" e la data scelta cambiano l'URL; indietro torna al
     giorno prima;
   - tema scuro emulato e larghezza 390 px: leggibile, senza scorrimento
     orizzontale della pagina.
   Screenshot del 07/10 chiaro e scuro e uno a 390 px nel report finale,
   e uno della scheda Streamlit della stessa corsa (colori nuovi).
6. Streamlit parte senza traceback e la Day si disegna con `AppTest`.
7. Tutti i server avviati per la verifica si fermano alla fine.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_34'$" --format=%H -1)
```

Effetti fuori dal repo: i report giornalieri scritti dopo il merge hanno la
sezione Next nel formato nuovo; restano leggibili anche dalla Day di prima
(sono paragrafi ed elenchi).
