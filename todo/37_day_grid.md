---
status: done
---

# La Day in React: Recovery, Health, Fitness e Load in una griglia 2x2

Fra la card Next e la card Training, la Day in React oggi ha una riga con due
card: *This morning* (con dentro i blocchi Recovery e Health) e *Load* (con
in fondo il VO2max). Diventa una griglia 2x2 di quattro card:

```
┌──────────────────── Next (scura, tutta la larghezza) ───────────┐
├──────────── Recovery ──────────┬──────────── Health ────────────┤
├──────────── Fitness ───────────┼──────────── Load ──────────────┤
├──────────────────── Training (tutta la larghezza) ──────────────┤
```

La card Fitness e' nuova: cosa Andrea e' capace di fare, che cambia piano
nelle settimane. In questo todo mostra solo quello che c'e' gia' nei dati
locali: il VO2max e la frequenza di soglia. Endurance score, hill score e la
soglia del lattato di Garmin arrivano con il todo 38.

Streamlit, i report e il JSON di `make daily_data` non cambiano.

## Decisioni

Prese con Andrea il 2026-10-18:

- **Quattro card, griglia 2x2**: Recovery e Health sopra, Fitness e Load
  sotto, nell'ordine. Due colonne uguali; sotto i 900 px (il punto in cui
  oggi `.cards-row` va a una colonna) una colonna sola, nello stesso ordine.
- **Next resta sopra e Training sotto**, a tutta larghezza, come oggi.
- **Il VO2max passa da Load a Fitness.** Load resta solo carico: stato,
  bilancio, giorni di riposo, ultima seduta dura.
- **Il badge dei segnali d'allarme** ("No warning signs" / "N warning
  signs", con la lista) oggi sta nel titolo di *This morning*. Riguarda sia
  Recovery sia Health, quindi va in una riga sottile sopra la griglia.
- **Fitness senza testo del report.** Il report giornaliero non ha una
  sezione Fitness e non la prende: la card ha solo numeri.
- **Due todo.** Questo e' solo layout e dati gia' in locale; i tre download
  nuovi da Garmin sono il todo 38.

## Work

### Python / API

- Il VO2max in Fitness va mostrato sempre, ma `load.vo2max_change` oggi c'e'
  solo se il VO2max si e' mosso di almeno 0.5 in 28 giorni. Serve un campo
  nuovo: `fitness` in `DailyData`, con `vo2max`: `now`, `as_of` (il giorno
  del valore, da `vo2max_date`), `days_ago_28` e `change` (questi due `null`
  se 28 giorni prima non c'e' un valore). `null` se non c'e' nessun VO2max
  fino al giorno.
- La funzione in `src/training/interface/daily_data.py`
  (`fitness_on(health, day)`, pubblica), ma il campo lo aggiunge solo
  l'endpoint `GET /api/daily/{day}` in `app.py`, non `build_daily_data`:
  cosi' il JSON di `make daily_data`, che legge l'agente del report
  giornaliero, non cambia.
- `load.vo2max_change` resta com'e' nell'API (lo usa il report), il
  frontend non lo legge piu'.
- La frequenza di soglia c'e' gia': `hr_zones.threshold_hr` e
  `hr_zones.as_of` in `DailyData`. Nessun cambio.
- `models.py`: `Fitness`, `Vo2maxNow`, con descrizioni.
- `make frontend_types` rigenera `frontend/src/api/schema.ts`.

### Frontend

- `components/MorningCard.tsx` si divide in `RecoveryCard.tsx` e
  `HealthCard.tsx`, ognuna con il suo titolo, i suoi numeri e il testo della
  sua sezione del report (Recovery, Health) con la sua icona, come oggi
  dentro i due `Block`. `Stat` e i piccoli aiuti in comune (`num`, ...)
  vanno in un file condiviso invece di essere copiati.
- `components/Alerts.tsx` (nuova): la riga dei segnali d'allarme sopra la
  griglia, con lo stesso badge e la stessa lista di oggi.
- `components/FitnessCard.tsx` (nuova), nello stile delle altre:
  - **VO2max**: il valore, la variazione in 28 giorni (con le classi
    `delta up` / `delta down` di oggi) e la data del valore;
  - **Threshold heart rate**: `hr_zones.threshold_hr` in bpm, "from the
    activity of <data>";
  - un numero che manca si vede come "–", la card non sparisce.
- `components/LoadCard.tsx`: via il blocco VO2max.
- `components/DayPage.tsx`: Next, poi `Alerts`, poi la griglia con le
  quattro card, poi Training.
- `styles.css`: `.cards-grid` a due colonne uguali, una colonna sotto i
  900 px; `.cards-row` va via se non la usa piu' nessuno. Tema chiaro e
  scuro come il resto.

### Docs

- `README.md`: la sezione della Day in React descrive le quattro card.

## Vincoli

- Nessuna dipendenza nuova, ne' nel frontend ne' in Python.
- Solo lettura: niente chiamate a Garmin.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Il frontend non fa conti: variazioni e date vengono dall'API.
- Training e Next non cambiano.

## Rischi

- **Altezze diverse**: in ogni riga la card piu' corta ha spazio vuoto in
  fondo. Va bene; le card non si allungano per riempirlo.
- **Fitness povera** finche' non c'e' il todo 38: due numeri. E' voluto.
- **Soglia vecchia**: le attivita' prima del 2026-10-16 hanno la soglia 154;
  la data accanto al valore lo rende chiaro.

## Verifica

Con l'API accesa sui dati locali:

1. `uv run python -c "import training; from training.api import app"`.
2. `TestClient`: `GET /api/daily/2026-10-15` ha `fitness.vo2max.now` e
   `as_of`; un giorno prima del primo VO2max ha `fitness.vo2max` `null`;
   `make daily_data DAY=2026-10-15` da' lo stesso JSON di prima del todo
   (salvarlo prima di cominciare e confrontare).
3. `cd frontend && npm run build`: nessun errore. `npm run gen:api` e
   `git diff --exit-code frontend/src/api/schema.ts`.
4. Nel browser (Claude in Chrome, o Chrome headless se l'estensione non c'e'),
   su `http://127.0.0.1:5173/?day=2026-10-15`: Next, la riga dei segnali,
   Recovery e Health sopra, Fitness e Load sotto, Training in fondo; Load
   senza VO2max; Fitness con VO2max e soglia. In chiaro e in scuro, e a
   400 px di larghezza (una colonna, stesso ordine). Un giorno senza dati di
   salute non rompe la pagina. Screenshot nel report finale.
5. Tutti i server avviati per la verifica si fermano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_37'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_37` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
