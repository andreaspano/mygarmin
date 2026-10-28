---
status: done
---

# Week:Snap sulla linea di Day:Snap

I todo 66 e 67 hanno dato una forma alla Day: lo **Snap** e' il corpo — un
Summary che riassume Health, Load, Recovery e Fitness, e le quattro card — e
la **Training** e' la seduta, con il piano, i dati e il giudizio in tre
riquadri separati.

La Week era rimasta a prima, e il suo Snap teneva **sette riquadri**: Next e
un Summary in due pezzi in una riga a due colonne, le quattro card, e una
card Training che conteneva il commento, il grafico del lavoro per sport e
l'elenco delle sedute. Era il Report del giorno di una settimana fa, con un
nome nuovo.

## Week:Snap — cinque card

1. **Summary**, uno, che riassume Health, Load, Recovery e Fitness
2. Health · 3. Load · 4. Recovery · 5. Fitness

## Week:Training — tre card, vista nuova

1. **Sessions**: il grafico per sport e l'elenco delle sedute
2. **Comment**: il testo della sezione Training, la forma della settimana
3. **Next**: la strategia dei sette giorni che vengono

Il **Plan** e il **Trend** restano le viste che sono. L'intestazione — titolo
col cerotto `N of 7 days`, frecce, calendario, striscia, tasto che riscrive —
resta comune a tutte e quattro.

## Le scelte

- **Le sedute vanno in una vista Training nuova**: simmetria piena col
  giorno, e lo Snap torna a essere una cosa sola.
- **Il verdetto e' uno e si scrive la domenica**, con le card. L'apertura del
  lunedi' sparisce.
- **Il Next della settimana resta**, al contrario di quello del giorno (todo
  66): e' la strategia dei sette giorni che vengono, non il consiglio per
  domani, e nessun piano scritto la da' gia' adattata alla settimana appena
  finita. Siccome lo Snap adesso e' il corpo, va nella Training, in coda —
  com'e' andato il lavoro, cosa dovra' essere quello che viene.

## Quello che si perde, detto chiaro

**Durante la settimana non c'e' piu' nessun testo.** Le quattro sezioni e il
Training si scrivevano tutte la domenica: l'unica cosa che parlava dal
lunedi' al sabato era l'apertura, `summary_start`, scritta il lunedi'
guardando la settimana prima. Togliendola, una settimana in corso mostra i
numeri delle card e **nient'altro** — Summary vuoto, nessuna prosa da nessuna
parte — per sei giorni su sette.

E' la conseguenza della scelta «un verdetto, scritto quando i sette giorni ci
sono»: una settimana ha i numeri alla fine, non all'inizio. Sta scritta qui
perche' chi legge fra sei mesi non la prenda per una rottura.

Con `summary_start` cade anche il **cerchio che si chiudeva**: `w7_summary`
diceva alla chiusura di leggere l'apertura — «Monday said this was a week to
go looking for work and you went looking for it» — e all'apertura di leggere
il `next.md` della settimana prima. Resta la sola chiusura, che guarda le
cinque sezioni.

## Work

### 1. Il registro — `api/sections.py`

- `WEEK_SECTIONS`: `summary_start`/`summary_end` →
  `Section("summary", "Summary", "w7_summary", True)`. Sette sezioni.
- `_WEEK_RUN_KEYS`: `next` e `summary` in coda, in quest'ordine — la chiusura
  legge `next.md`, quindi `next` va prima.
- `WEEK_MOMENT_SECTIONS`: **un momento solo**, `end`, con tutte e sette. Un
  momento che scrive una sezione sola non e' un momento.
- `_WEEK_MOMENT_LINES` e `_WEEK_BACKFILL`: una voce ciascuno.
- `week_moment_at` rende sempre `"end"`. La funzione resta, con un valore
  solo: il momento e' un parametro del ciclo condiviso col giorno, e il tasto
  della pagina lo chiede.
- **`old_fragments` diventa un campo di `Report`.** Il ripiego sui frammenti
  vecchi del todo 66 stava in `app.py` come dizionario del solo giorno;
  adesso serve anche alla settimana, con altri nomi. E' roba del registro.

### 2. Il modello — `api/models.py`

`RefreshStatus.moment` perde `"start"` dal `Literal`, e la descrizione, che
parlava ancora del Next del giorno, dice cosa decide il momento.

### 3. Gli agenti — `.claude/agents/`

- `w7_summary.md`: un lavoro solo, la chiusura. Via la parte «Week start»,
  via il cerchio da chiudere, via `summary_start.md`. L'avviso di non dare
  consigli resta: li' il Next c'e' ancora, nella pagina accanto.
- `w6_next.md`: due riferimenti al Next del giorno non esistevano piu'. Il
  confine che tracciavano resta vero — qui si dice la forma del lavoro, non
  la seduta col suo intervallo — e adesso punta al piano scritto, che e' dove
  quel dettaglio sta per davvero.
- `w5_training.md` **non cambia**.

### 4. I timer — `deploy/crontab`

La riga del lunedi' sparisce: il mattino e' sempre il solo giro del giorno,
tutti i sette. Resta la domenica alle 21, dove la settimana gira in coda al
giorno.

### 5. Il frontend

- `navigation.ts`: `VIEWS.week = ["snap", "training", "trend", "plan"]`.
- `WeekPage.tsx`: lo Snap perde la `.head-row` e prende una `<SummaryCard>` a
  tutta larghezza con il solo `morning`; la vista Training nuova con le tre
  card. I cancelli: gli sport e le sedute passano alla Training, il report
  serve a tutte e due.
- `styles.css`: `.head-row` si cancella, con la sua regola sotto i 900 px —
  la Day l'ha lasciata col todo 66, la Week qui.

### 6. `README.md`

La Week con quattro viste, la tabella del giro settimanale e il paragrafo del
verdetto, che adesso e' uno.

## Rischi

- **Gli `assert` del registro** fanno fallire l'import se il backfill non
  nomina ogni sezione esattamente una volta, o se i verdetti non sono una
  coda contigua. E' una rete, ed e' la prima cosa che si rompe.
- **Il ripiego dei frammenti e' il guasto muto**: senza `old_fragments` per
  la settimana, le tredici settimane scritte mostrerebbero la cornice del
  Summary vuota.
- **Una settimana in corso diventa muta.** Non e' un difetto da sistemare
  dopo: e' la scelta.

## Verifica

1. L'import regge, con gli assert del registro.
2. Il giro: `--moment end` elenca sette sezioni, `--moment start` non esiste
   piu'.
3. Un giro vero su una settimana chiusa scrive `summary.md` accanto agli
   altri sei.
4. Il ripiego: una settimana scritta prima rende un Summary pieno.
5. Le pagine, in Firefox headless: Week/Snap cinque card, Week/Training tre,
   le altre invariate.
6. Il menu: sotto Week `Snap | Training | Trend | Plan`.

## Come e' andata

Fatto come scritto, senza deviazioni. Gli `assert` del registro hanno fatto
il loro lavoro due volte durante il lavoro, fermando l'import finche'
`_WEEK_BACKFILL` nominava ancora `summary_end`.

### Cosa e' stato verificato

- **L'import**: `import training.api.app` passa.
- **Il registro**, letto a mano: momenti `('end',)`; sette sezioni; ordine di
  lancio `health, load, recovery, fitness, training, next, summary`;
  backfill in una passata sola; i due ripieghi, `{'summary':
  ('summary_evening', 'summary_morning')}` per il giorno e `{'summary':
  ('summary_end', 'summary_start')}` per la settimana.
- **Il CLI rifiuta il momento che non c'e'**:
  `--moment: invalid choice: 'start' (choose from 'end')`.
- **Un giro vero** sulla settimana del 19 ottobre: sette sezioni, tutte
  `done`, e i file riscritti sono esattamente i sette, `summary.md`
  compreso. Il verdetto nuovo e' uno e guarda la settimana: «A good week, and
  one that paid. Six days of long steady work, built around the day in the
  mountains (...) Only the nights argue: you got back up every morning
  without ever feeling fresh.» Nessun numero, nessun consiglio.
- **Il ripiego**: `GET /api/reports/weekly/2026-10-19` e `.../2026-08-03`
  rendono sette sezioni con il Summary pieno — preso da `summary_end.md` —
  non un riquadro vuoto.
- **Le pagine**, in Firefox headless, leggendo le `aria-label`:

  | vista | menu | card |
  |---|---|---|
  | Week/Snap | `Snap* Training Trend Plan` | Summary, Health, Load, Recovery, Fitness |
  | Week/Training | `Training*` | Sessions (col grafico dentro), Comment, Next session |
  | Week/Plan | `Plan*` | Weekly plan |
  | Day/Snap | `Snap* Training Trend` | le cinque di sempre |
  | Day/Training | `Training*` | Plan, Session, Comment |

  Nessuna `.head-row` da nessuna parte.
- **La vista viaggia fra i periodi**: da Day/Training il collegamento alla
  Week e' `?day=...&view=training&period=week`, che prima non esisteva.
- `make frontend_types` (due righe: il `Literal` del momento e la sua
  descrizione), `npm run typecheck` e `npm run build` puliti.

### Cosa resta su disco

Nelle tredici settimane gia' scritte restano `summary_start.md` e
`summary_end.md`. Il secondo si legge ancora, col ripiego; il primo no, e
nessuno dei due si cancella: sono il testo che quelle settimane avevano.

### Tre bugie piccole sistemate passando

- `WeekPicker` diceva «le otto settimane» e le costanti dicono sei.
- Il commento di `CARD_ICONS` in `WeekPage` diceva che «la Week un report non
  ce l'ha ancora», e ce l'ha dal todo 53.
- Il docstring di `week_moment_at` citava «il giro delle 22», che dal todo 66
  sono le 21.

### Fuori da questo lavoro

La pagina chiede **due volte le stesse sedute**: `api.activities` per
l'elenco, mentre `/api/weekly/{monday}` ne rende gia' una lista
(`weekly_data.py:576`). Non si e' toccato.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_68'$" --format=%H -1)
```

Effetti fuori dal repo: il `summary.md` della settimana del 19 ottobre resta
nella cartella, con le altre sei sezioni riscritte dalla verifica. Il codice
vecchio non legge `summary.md` e tornerebbe a `summary_start.md` e
`summary_end.md`, che sono ancora li': quella settimana si rileggerebbe col
verdetto di prima. Il `cron` installato va reinstallato con
`make install_cron` per riavere la riga del lunedi'.

Dopo il revert, rifare il merge di `todo_68` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
