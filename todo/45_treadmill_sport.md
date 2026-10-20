---
status: done
---

# Il tapis roulant diventa uno sport a se'

Oggi una seduta sul tapis roulant e' una corsa: `sport` dice `running`, e la
differenza la porta solo `sub_sport`. Da li' nascono una serie di toppe
sparse — il terreno che va escluso a mano, la velocita' equivalente che non
ha senso, il confronto con le uscite su strada, l'agente che scrive "you went
out" — e una bugia vera: **la distanza**. Sul nastro l'orologio la stima dal
polso, e in salita sbaglia di molto. La seduta del 2026-10-20 era 5x(5 min a
8 km/h + 5 min a 5 km/h al 15%): l'orologio ha registrato 3.31 km a una media
di 3.7 km/h, e il report, leggendo quelli, l'ha liquidata come "walking with
some jogging in it". Le calorie (553 in 58 minuti) e la potenza (media 141 W,
picco 410 W) dicevano un'altra cosa.

Lo sport nuovo risolve alla radice: di una seduta sul nastro si misurano
**tempo, battito, potenza e calorie**, e si tratta come un lavoro cardio.
Distanza e passo non sono un suo concetto.

## Decisioni

Prese con Andrea il 2026-10-20:

- **`treadmill` e' uno sport**, accanto a running, cycling, walking, hiking,
  cross country skiing, rock climbing.
- **Niente tipo di seduta.** Facile, ripetute, tempo e lunga restano alle
  corse: sul nastro il report giudica su battito, potenza, calorie ed
  effetto. (Oggi i 23 tapis dello storico hanno tutti `run_type: easy`
  stimato, compresa la seduta a ripetute di ieri: una classificazione che
  vale poco.)
- **La distanza si nasconde, non si butta.** Via dalla pagina, dai report e
  dai totali per sport; resta in `activities.db` e nel JSON, marcata come
  inattendibile. Se un giorno arriva un foot pod calibrato, il dato c'e'.
- **L'icona c'e' gia'**: `icons/treadmill.png`, disegnata nello stile delle
  altre (cerchio pieno verde-acqua, nastro ad anello, montante e console).
  Il verde-acqua non e' usato da nessuna delle altre nove.

## Work

### 1. La classificazione: `src/training/interface/db.py`

**Il tipo di Garmin non basta.** Dei 23 tapis dello storico, 22 hanno
`activity_types.json` a `None` e uno solo dice `treadmill_running`: la
mappa `GARMIN_TYPE_TO_SPORT` da sola ne prenderebbe uno su ventitre. La
regola deve guardare `sub_sport`, che il FIT porta sempre.

- `sport_from_garmin_type` riceve anche il `sub_sport` e rende `treadmill`
  quando vale `treadmill`, prima di ogni altra cosa; `treadmill_running` si
  aggiunge comunque a `GARMIN_TYPE_TO_SPORT`.
- **Lo storico si sistema senza rebuild.** `sub_sport` e' gia' una colonna di
  `activities`: in `sync()` basta un `UPDATE activities SET sport='treadmill'
  WHERE sub_sport='treadmill'` accanto agli altri due aggiornamenti. Un salto
  di `LOGIC_VERSION` rileggerebbe 978 file FIT (circa un secondo l'uno) per
  ricavare un dato che e' gia' in tabella.

### 2. Quello che segue da solo

Da verificare, non da scrivere: il terreno (`has_terrain` vuole uno sport di
`EQUIV_SPEED_SPORTS`), la velocita' equivalente (stessa lista) e il tipo di
corsa (`has_run_type` vuole `running`) **escludono gia'** uno sport nuovo. Le
due condizioni su `treadmill` dentro `has_terrain` diventano morte: vanno
tolte, con il commento aggiornato.

Anche il confronto con le sedute simili si sistema da solo, perche' guarda lo
sport: la bandierina `indoor` e il filtro su `sub_sport` aggiunti in
`_compared_with` il 2026-10-20 diventano inutili e si tolgono.

### 3. La distanza che non c'e'

Una costante sola, `DISTANCELESS_SPORTS = {"treadmill"}` in
`interface/sports.py`, e chi mostra guarda quella:

- `daily_data._session`: `distance_km` resta, con accanto
  `distance_unreliable` vero; la seduta porta gia' `calories`, `avg_power` e
  `max_power` dal 2026-10-20.
- `daily_data._recent`: le righe "running 8.1 km" di `last_7_days` e le
  attivita' di `activities_last_14_days` danno i minuti al posto dei km.
- `weekly_data`: `by_sport` non somma la distanza per questi sport, e
  `_activity_row` e `_days` danno i minuti.
- `frontend/src/components/TrainingCard.tsx`: niente riquadro Distance (o
  "–"), e `WeekStrip.amount()` mostra la durata invece dei km.

### 4. Lo sport a schermo: `interface/sports.py`

`SPORT_ICON_FILES["treadmill"] = "treadmill.png"`. L'etichetta la fa gia'
`sport_label` ("Treadmill").

### 5. Il report: `.claude/agents/05_training.md`

Il paragrafo sul tapis roulant c'e' gia' (2026-10-20) e va riscritto sullo
sport invece che su `indoor`/`sub_sport`: sul nastro non si "esce", non c'e'
terreno, **la distanza e il passo non si nominano affatto**, e il giudizio
sta su calorie al minuto, potenza, battito ed effetto. Resta la riga che dice
di credere al nome dell'attivita' piu' che ai numeri di passo, perche' la
pendenza nel file non c'e'.

## Vincoli

- Nessuna dipendenza nuova.
- Niente rebuild del database: lo storico si riclassifica con un UPDATE.
- I 23 tapis cambiano sport, quindi cambiano i conteggi per sport dei report
  settimanali e le medie delle corse facili: e' voluto, ed e' il punto.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- Non si tocca `frontend/src/api/schema.ts` a mano.

## Rischi

- **Una corsa vera scambiata per nastro**: se un FIT porta `sub_sport`
  `treadmill` per errore, quella seduta perde distanza e tipo. Si corregge
  come il terreno, a mano, ma oggi non c'e' un modo di correggere lo sport.
- **Lo storico si sposta**: i report settimanali gia' scritti citano corse
  che da domani sono tapis. I file vecchi non si riscrivono.
- **La distanza nascosta e' comunque registrata**: chi guarda il database la
  trova e puo' crederci.

## Verifica

1. `uv run python -c "import training"` piu' gli import dei moduli toccati.
2. Dopo un `sync()`: le 23 sedute hanno `sport = treadmill`, nessuna ha un
   `run_type`, nessuna ha un terreno, nessuna ha la velocita' equivalente.
3. Le corse su strada non si muovono: il conto delle `running` cala
   esattamente di 23 e nessun'altra colonna cambia.
4. `make daily_data DAY=2026-10-20`: la seduta ha `sport: treadmill`,
   `distance_unreliable` vero, calorie e potenza al loro posto.
5. `make daily_report DAY=2026-10-20 SECTION=training`: il testo non nomina
   ne' distanza ne' passo, e giudica su calorie, potenza e battito.
6. `make frontend_types`, `npm run typecheck`, `npm run build`.
7. La pagina: l'icona nuova nella striscia della settimana, la scheda
   Training senza il riquadro della distanza, i minuti al posto dei km.

## Come e' andata

Fatto come scritto, con tre aggiunte decise strada facendo, tutte dello
stesso segno:

- **La velocita' media sparisce con la distanza.** E' la stessa stima divisa
  per il tempo: lasciarla a schermo sarebbe stato nascondere la bugia e
  tenerne il quoziente. Al posto del riquadro Distance la scheda Training
  mostra le **calorie**, e i numeri diventano quattro invece di cinque.
- **`execution` perde tutto tranne la cadenza.** Le due meta' sono meta' *di
  distanza*: sul nastro anche il confronto dei battiti sarebbe caduto in un
  punto scelto dalla stima del polso, non a meta' seduta. La cadenza no, e
  resta.
- **Anche i report per attivita'** (`summary/00.activity/`) non dichiarano
  piu' la distanza degli sport che non ne hanno: al suo posto le calorie.

E un difetto trovato per strada, che non c'entra con il tapis roulant ma
fermava la verifica: `_value` lasciava passare gli interi di numpy
(`np.float64` per Python e' un `float`, `np.int64` non e' un `int`), e da
quando il JSON del giorno porta la potenza massima `make daily_data`
moriva con "Object of type int64 is not JSON serializable". Dall'API non si
vedeva, perche' li' `json.dumps` ha un `default=str`.

Il grafico della scheda **continua a disegnare la velocita' campionata**
anche sul nastro: e' una stima, ma e' l'unica cosa che fa vedere la forma
della seduta (i blocchi a 8 km/h e quelli lenti). Se da' fastidio si toglie
in due righe.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_45'$" --format=%H -1)
```

Effetti fuori dal repo: le 23 sedute restano `sport = treadmill` in
`activities.db` con `equiv_speed_kmh` a NULL (l'UPDATE in `sync()` e' gia'
passato); il codice vecchio le rimette a `running` solo al prossimo rebuild,
e fino ad allora la pagina le mostra come uno sport senza icona. Restano
anche il frammento `summary/01.daily/2026-10-20/training.md` riscritto senza
distanza e il report `summary/00.activity/24794900255.md`, che e' ancora
quello vecchio ("# running", "Positive split... pace drop-off"): i report per
attivita' non si rigenerano mai da soli, va cancellato a mano e rifatto con
`make activity_reports`.

Dopo il revert, rifare il merge di `todo_45` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
