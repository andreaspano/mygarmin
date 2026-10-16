---
status: todo
---

# Il tipo delle corse

Le corse (`running`) prendono un campo nuovo, **run_type**, con cinque
livelli: `race`, `intervals`, `long`, `tempo`, `easy`.

Il tipo si indovina dai dati e Andrea lo puo' correggere dalla scheda
Training della Day in React, come il terreno (todo 35). Si vede solo nella
Day in React ed e' un campo di `Activity` nell'API. Report giornalieri,
settimanali e di attivita' e Streamlit non cambiano.

## Decisioni

Prese con Andrea il 2026-10-16:

- **Solo la corsa.** Il tipo vale per `running`, tapis roulant compreso; per
  gli altri sport e' `null`.
- **Niente trail.** Il trail e' gia' un terreno (todo 35), non un tipo.
- **Indovinato, poi correggibile.** Ogni corsa ha un tipo stimato; la
  correzione di Andrea, se c'e', vince.
- **Regole della stima**, in ordine. Usano l'allenamento pianificato nel FIT
  (messaggi `workout` e `workout_step`, oggi non letti da nessuna parte) e la
  durata:
  1. allenamento con almeno 2 passi `active`: `intervals` (es. `Rip_4x5`,
     `Rip_3x5`);
  2. allenamento con 1 solo passo `active` di almeno 10 minuti: `tempo`;
  3. senza allenamento e durata >= `LONG_MIN` minuti: `long`;
  4. altrimenti `easy`.
- **`race` non si stima mai**, e nemmeno `tempo` senza allenamento: dai
  battiti non si distingue una corsa libera forte da una gara, e le corse
  facili di Andrea stanno gia' a 130-140 bpm. Li mette Andrea, come
  `gravel` per il terreno.
- **Soglia della corsa lunga.** Si parte da 100 minuti: nell'ultimo anno le
  corse stanno tra 32 e 90 minuti e tra 111 e 139, niente in mezzo. Prima di
  fissarla si riguarda la distribuzione in `activities.db`, e il commento
  sopra la costante dice perche' quel valore.
- **L'allenamento si salva nel database.** Al contrario del terreno, la stima
  ha bisogno di dati che oggi non ci sono: tre colonne nuove in
  `activities` (`workout_name`, `workout_active_steps`,
  `workout_active_max_s`), lette dal FIT, e salto di `LOGIC_VERSION` (7 -> 8)
  con rebuild. La stima invece si calcola in lettura.
- **Le correzioni stanno fuori dal database**, in
  `data_dir/activity_run_type.json` (`{"<activity_id>": "<run_type>"}`),
  accanto a `activity_terrain.json`, cosi' un rebuild non le perde.
- **Due campi nell'API.** `run_type` e' il valore in uso; `run_type_source`
  e' `"user"`, `"guess"` o `null` (sport che non e' corsa).
- **Scrittura.** `PUT /api/activities/{id}/run_type` con corpo
  `{"run_type": <run_type> | null}`; `null` toglie la correzione e torna alla
  stima.

## Work

### Python

- `src/training/interface/fit.py`: `_workout(fit)` dallo stesso `FitFile` di
  `load_activity_summary` (nessun costo in piu', vedi il commento verso
  l.82). Restituisce `workout_name` (`workout.wkt_name`),
  `workout_active_steps` (quanti `workout_step` hanno `intensity` `active`) e
  `workout_active_max_s` (il `duration_time` piu' lungo tra questi). Tutti
  `None` senza messaggio `workout`.
- `src/training/interface/db.py`: le tre colonne in `_SCHEMA`, nella lista
  dell'INSERT e nell'UPDATE di `_insert_activity`; `LOGIC_VERSION` 8 con la
  riga di storia. In `list_activities`, `_add_run_type(df, data_dir)` accanto
  a `_add_terrain`, con la stessa logica (correzione -> `user`, altrimenti
  stima -> `guess`, altri sport `None`/`None`).
- `src/training/interface/run_type.py` (nuovo), sul modello di
  `terrain.py`: `RUN_TYPES`, `LONG_MIN`, la durata minima del passo tempo,
  `has_run_type(sport)`, `guess_run_type(...)` (funzione pura),
  `load_run_type_overrides(data_dir)` (con `fit._load_json_map`) e
  `save_run_type_override(data_dir, activity_id, run_type | None)`:
  scrittura atomica sotto un lock, come `save_terrain_override`.

### API

- `models.py`: `RunType = Literal["race", "intervals", "long", "tempo",
  "easy"]`; in `Activity` i campi `run_type: RunType | None` e
  `run_type_source: Literal["guess", "user"] | None`, con descrizione; il
  corpo `RunTypeUpdate`.
- `app.py`: `PUT /api/activities/{activity_id}/run_type`, copiato da
  `put_activity_terrain`: 404 se l'attivita' non c'e', 422 se non e' una
  corsa; dopo la scrittura `invalidate(ctx.data_dir)` e risposta con
  l'`Activity` aggiornata. Il `GET` non cambia: `_activity_fields` prende i
  campi nuovi da solo.
- `make frontend_types` rigenera `frontend/src/api/schema.ts`.

### Frontend

- `frontend/src/api/client.ts`: `type RunType` e `api.setRunType(id,
  run_type | null)`, come `setTerrain`.
- `TrainingCard.tsx`: un `RunTypePicker` sul modello di `TerrainPicker`
  ("Auto (guess: Intervals)" e i cinque valori; errore "Could not save the
  run type."), accanto al terreno in `training-side`, solo per le corse. Il
  tipo si vede anche come etichetta accanto al titolo, es. "Intervals" o
  "Intervals (guessed)".
- `styles.css`: si riusano gli stili di `.terrain`, generalizzati se serve.

### Docs

- `README.md`: un paragrafo accanto a quello del terreno, con dove stanno le
  correzioni.

## Vincoli

- Nessuna dipendenza nuova, ne' nel frontend ne' in Python.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Il frontend non calcola la stima: viene dall'API.

## Rischi

- **Rebuild**: il salto di `LOGIC_VERSION` riparsa tutti i FIT (circa 975)
  al primo accesso: qualche minuto, una volta.
- **Allenamenti con nomi o forme diverse** (es. fartlek con passi a
  distanza): la regola conta solo i passi `active`, il resto lo corregge
  Andrea.
- **Fuori da questo todo**: `activity_names.json` e `activity_types.json`
  nella cartella dati hanno solo 7 voci, mentre le copie `.conflict` della
  sincronizzazione cloud ne hanno 971. Il tipo di corsa non ne dipende (usa
  lo sport del FIT e l'allenamento), il terreno si'. Da sistemare in un todo
  a parte.

## Verifica

Con l'API accesa e i dati locali:

1. `uv run python -c "from training.interface import run_type, db"`;
   `guess_run_type` sui casi delle regole (ripetute, tempo, lunga sopra e
   sotto la soglia, facile, sport non corsa).
2. Su una copia della cartella dati in una cartella temporanea: `rebuild()` e
   `list_activities()`. Le corse del 15/10 (`Rip_4x5`), 13/10 e 07/10
   (`Rip_3x5`) escono `intervals`; quelle del 10/10 (112 min) e 11/10
   (139 min) `long`; le altre `easy`.
3. Con il `TestClient` sulla stessa copia: PUT `race` -> `run_type_source`
   `user`; PUT `null` -> si torna alla stima; 404 su un id che non c'e'; 422
   su un'attivita' in bici. La correzione sopravvive a `rebuild()`.
4. `cd frontend && npm run build`: nessun errore. `npm run gen:api` e
   `git diff --exit-code frontend/src/api/schema.ts`.
5. Nel browser (Claude in Chrome), su
   `http://127.0.0.1:5173/?day=2026-10-15`: l'etichetta dice "Intervals
   (guessed)"; si sceglie `Race`, si ricarica e resta; si torna ad "Auto" e
   torna la stima. Un giorno con un'attivita' non di corsa non ha il campo.
   Screenshot nel report finale.
6. Alla fine `data_dir/activity_run_type.json` non ha le correzioni fatte per
   la verifica, e tutti i server avviati per la verifica si fermano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_36'$" --format=%H -1)
```

Effetti fuori dal repo: `activity_run_type.json` nella cartella dati, se
Andrea ha corretto qualche tipo dopo il merge; dopo il revert nessuno lo
legge, e' innocuo. Il ritorno di `LOGIC_VERSION` a 7 fa un altro rebuild di
`activities.db` al primo accesso.

Dopo il revert, rifare il merge di `todo_36` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
