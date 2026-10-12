---
status: todo
---

# Il terreno delle attivita' a piedi

Corsa, camminata ed escursione (`running`, `walking`, `hiking`, gli sport di
`grade.EQUIV_SPEED_SPORTS`) prendono un campo nuovo, **terrain**, con cinque
livelli: `track`, `road`, `gravel`, `trail`, `mountain`.

Il terreno si indovina dai dati e Andrea lo puo' correggere dalla scheda
Training della Day in React. Si vede nelle pagine Day (React e Streamlit) ed
e' un campo di `Activity` nell'API. Report giornalieri e settimanali non
cambiano.

## Decisioni

Prese con Andrea il 2026-10-12:

- **Solo a piedi.** Il terreno vale per `running`, `walking` e `hiking`;
  per gli altri sport e per il tapis roulant (`sub_sport` treadmill o tipo
  Garmin `treadmill_running`) e' `null`.
- **Indovinato, poi correggibile.** Ogni attivita' a piedi ha un terreno
  stimato; la correzione di Andrea, se c'e', vince.
- **Strada di default.** Dai dati del FIT non si distingue lo sterrato dalla
  strada: dove i dati non decidono, la stima e' `road`. `gravel` non si
  stima mai, lo mette Andrea.
- **Regole della stima**, in ordine (la salita per km e'
  `total_ascent_m / total_distance_km`):
  1. tipo Garmin `track_running` o `sub_sport` track: `track`;
  2. tipo Garmin `mountaineering`: `mountain`;
  3. salita per km >= `MOUNTAIN_M_PER_KM`: `mountain`;
  4. tipo Garmin `trail_running`, `sub_sport` trail, oppure sport `hiking`:
     `trail`;
  5. salita per km >= `TRAIL_M_PER_KM`: `trail`;
  6. altrimenti `road`.
- **Soglie.** Si parte da 60 e 25 m/km. Prima di fissarle si guarda la
  distribuzione vera della salita per km delle attivita' a piedi in
  `activities.db`, e il commento sopra le costanti dice perche' quei valori.
- **La stima si calcola in lettura, non si salva nel database.** Niente
  colonna nuova in `activities`, niente salto di `LOGIC_VERSION`, niente
  rebuild: la stima dipende solo da colonne che ci sono gia' e dal tipo
  Garmin (`activity_types.json`).
- **Le correzioni stanno fuori dal database.** `activities.db` e' una cache
  che `rebuild()` cancella: le correzioni vanno in
  `data_dir/activity_terrain.json` (`{"<activity_id>": "<terrain>"}`),
  accanto a `activity_names.json` e `activity_types.json`.
- **Due campi nell'API.** `terrain` e' il valore in uso (la correzione se
  c'e', altrimenti la stima); `terrain_source` e' `"user"`, `"guess"` o
  `null` (sport senza terreno). Cosi' il frontend sa se mostrare la stima
  come tale.
- **La prima scrittura dell'API.** `PUT /api/activities/{id}/terrain` con
  corpo `{"terrain": <terrain> | null}`; `null` toglie la correzione e torna
  alla stima. Resta solo su 127.0.0.1 e senza login, come il resto.

## Work

### Python

- `src/training/interface/terrain.py` (nuovo): `TERRAINS`, le due soglie,
  `guess_terrain(sport, sub_sport, garmin_type, distance_km, ascent_m)`
  (funzione pura), `load_terrain_overrides(data_dir)` (con
  `fit._load_json_map`, come `load_activity_names`) e
  `save_terrain_override(data_dir, activity_id, terrain | None)`: scrittura
  atomica (file temporaneo e `os.replace`) sotto un lock; con `None` toglie
  la voce.
- `db.list_activities`: aggiunge le colonne `terrain` e `terrain_source`,
  dalla stima e dalle correzioni. Il tipo Garmin viene da
  `fit.load_activity_types`.

### API

- `models.py`: `Terrain = Literal["track", "road", "gravel", "trail",
  "mountain"]`; in `Activity` i campi `terrain: Terrain | None` e
  `terrain_source: Literal["guess", "user"] | None`, con descrizione;
  il corpo `TerrainUpdate`.
- `app.py`: l'endpoint `PUT /api/activities/{activity_id}/terrain`. 404 se
  l'attivita' non c'e', 422 se lo sport non ha terreno (o per un valore
  fuori elenco, gia' da Pydantic). Dopo la scrittura svuota la cache di
  `api/cache.py` per quella cartella dati, e risponde con l'`Activity`
  aggiornata. `_activity_fields` prende i campi nuovi da solo.
- La docstring di `app.py`, la `description` di FastAPI e il README non
  dicono piu' "sola lettura" senza eccezioni: tutto `GET` tranne il terreno.
- `make frontend_types` rigenera `frontend/src/api/schema.ts`.

### Frontend

- La chiamata PUT in `frontend/src/api/`, accanto alle altre.
- `TrainingCard.tsx`: una voce "Terrain" nella scheda, solo per le attivita'
  con terreno. Un `<select>` con "Auto (guess: Road)" e i cinque valori;
  con la stima in uso e' scelto "Auto". Al cambio si manda la PUT e si
  ricarica l'attivita'; se la PUT fallisce, il valore torna com'era e una
  riga dice "Could not save the terrain."
- Il proxy di Vite passa gia' `/api`, PUT compresa.

### Streamlit

- `activity_detail.py`: "Terrain" in sola lettura nella scheda, con
  "(guessed)" quando e' una stima. Niente modifica da Streamlit.

## Vincoli

- Nessuna dipendenza nuova, ne' nel frontend ne' in Python.
- L'unica scrittura e' la PUT del terreno; `activities.db` non cambia.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Il frontend non calcola la stima: viene dall'API.

## Rischi

- **Soglie sbagliate**: una corsa collinare su strada puo' uscire `trail`.
  Le soglie si tarano sui dati veri, e Andrea corregge il resto.
- **Cache dell'API**: senza svuotarla, la correzione si vedrebbe solo dopo un
  minuto. La cache di Streamlit (`interface/data.py`) resta di un minuto:
  li' la correzione arriva al piu' un minuto dopo, e va bene.
- **Scritture insieme** sullo stesso JSON: lock e sostituzione atomica.
- **Sport riclassificato** dopo una correzione (es. da `walking` a un altro
  sport): la correzione resta nel JSON ma non si usa, perche' lo sport non
  ha terreno.

## Verifica

Con l'API accesa e i dati locali:

1. `cd frontend && npm run build`: nessun errore ne' avviso TypeScript.
2. `npm run gen:api` e `git diff --exit-code frontend/src/api/schema.ts`.
3. Con il `TestClient`, su una copia della cartella dati in una cartella
   temporanea:
   - una corsa piatta su strada ha `terrain` `road` e `terrain_source`
     `guess`; un'escursione ha `trail` o `mountain`;
   - PUT `gravel`: la risposta e il `GET` dopo hanno `gravel` / `user`;
   - PUT `null`: si torna alla stima;
   - PUT su un'attivita' in bici: 422; su un id che non c'e': 404;
   - un'attivita' in bici ha `terrain` e `terrain_source` `null`.
4. `guess_terrain` sui casi delle regole (pista, alpinismo, trail, salita
   sopra e sotto le soglie, tapis roulant, sport non a piedi).
5. La correzione sopravvive a `rebuild()`.
6. Nel browser (Claude in Chrome), su `http://127.0.0.1:5173/?day=2026-10-07`:
   la scheda della corsa mostra "Auto (guess: ...)"; si sceglie `Gravel`,
   si ricarica la pagina e resta `Gravel`; si torna ad "Auto" e torna la
   stima. Un giorno con un'attivita' non a piedi (l'arrampicata dell'08/10)
   non ha la voce Terrain. Screenshot nel report finale.
7. Streamlit parte senza traceback e la Day si disegna con `AppTest`, con la
   voce Terrain nella scheda della corsa.
8. Alla fine `data_dir/activity_terrain.json` non ha le correzioni fatte per
   la verifica, e tutti i server avviati per la verifica si fermano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_35'$" --format=%H -1)
```

Effetti fuori dal repo: `data_dir/activity_terrain.json`, se Andrea ha
corretto qualche terreno. Dopo il revert nessuno lo legge: si puo' lasciare
o cancellare. Nessun cambio a `activities.db`.

Dopo il revert, rifare il merge di `todo_35` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
