---
status: done
---

# Due pagine, due giri: il corpo la mattina, la seduta la sera

Oggi la Day mescola due domande in orari sbagliati. Il Report tiene Next e un
Summary in due pezzi (sole e luna, todo 49) sopra le quattro card del corpo;
la Training tiene il piano e la seduta, col commento del coach **dentro** la
card della seduta. E i due giri dei timer (10:00 e 22:00) riscrivono entrambi
pezzi di entrambe le pagine: `load` e `fitness` girano due volte, `next` due
volte, e il Summary ha una meta' per giro.

La forma che si vuole e' **due pagine, un giro ciascuna**.

## Day:Report — cinque card, scritte alle 08:00

1. **Summary**, uno solo, che riassume Health, Load, Recovery e Fitness
2. Health
3. Load
4. Recovery
5. Fitness

## Day:Training — tre card, scritte alle 21:00

1. **Plan**, il piano del giorno
2. **la seduta del giorno**
3. **il commento alla seduta**, che guarda sia il piano sia l'esecuzione

Il Trend non si tocca: non ha testo, legge solo i numeri.

## Cosa cambia, in concreto

**Le sezioni passano da otto a sei.** Via `next` e il suo agente;
`summary_morning` e `summary_evening` diventano un `summary`.

| | ora | sezioni | scrive |
|---|---|---|---|
| mattina | 08:00 | health, recovery, load, fitness, summary | Report |
| sera | 21:00 | training | Training |

Ogni sezione gira **una volta al giorno**, e ogni pagina ha un giro suo. Era
il disordine piu' grosso: `load` e `fitness` scritti due volte, e un Summary
che si contraddiceva con se stesso a dodici ore di distanza.

**Il commento esce dalla card della seduta.** Oggi `TrainingCard` tiene
dentro il selettore, il grafico, la mappa, i numeri, i selettori di terreno e
tipo, **e** il testo della sezione col suo tasto. Il testo diventa la terza
card.

Nomi proposti per le due: **Session** per i dati, **Comment** per il testo.
"Training" per una delle due sarebbe ambiguo, che la vista si chiama cosi'.

## Quello che si perde, detto chiaro

**La seduta suggerita.** Next era l'unica cosa che prendeva i numeri di
stamattina e diceva cosa fare oggi. Il piano lo dice, ma scritto diciotto
settimane prima; le sue regole di deroga («readiness under 40: run it easy and
move the session to Friday») restano scritte e **nessuno le applica piu'**. E
sui giorni fuori dal blocco — tutto lo storico, e dopo il 22 febbraio 2027 —
di piano non ce n'e', quindi di suggerimento non ce n'e' nessuno.

E' una conseguenza voluta, non un effetto collaterale: sta scritta qui perche'
chi legge fra sei mesi sappia che non e' stata una dimenticanza.

**Load e Fitness raccontano lo stato prima della seduta di oggi.** Scritti
alle otto, includono la seduta di ieri e non quella di oggi. Il Report diventa
dichiaratamente «come stai stamattina», e il carico di oggi si legge domani.
Oggi si riscrivono anche la sera proprio per includerla: e' un cambio di
significato, non solo di orario.

## Work

### 1. Il registro — `api/sections.py`

- `SECTIONS`: via `next`, e `summary_morning`/`summary_evening` →
  `Section("summary", "Summary", "07_summary", True)`.
- `_RUN_KEYS`: sei chiavi, il verdetto in fondo (c'e' un `assert` che lo
  pretende).
- `MOMENT_SECTIONS`:
  `morning: (health, recovery, load, fitness, summary)`,
  `evening: (training,)`.
- `_DAY_BACKFILL`: va riscritto e **l'assert che copre ogni sezione va
  soddisfatto** — oggi pretende che il backfill nomini tutte le chiavi.
- `_DAY_MOMENT_LINES`: le due righe restano, ma dicono un'altra cosa. La
  mattina il Summary parla del corpo di stanotte; la sera il Training parla
  della seduta appena fatta.
- `EVENING_FROM_HOUR`: resta, e gli resta un lavoro solo — il tasto Refresh
  della pagina rifa' **tutte** le sezioni a qualunque ora, e il momento decide
  con che voce. Il commento sopra la costante va corretto: non parla piu' di
  Next.
- `WEEK_SECTIONS` e tutto il settimanale **non si toccano**: la Week ha la sua
  apertura, la sua chiusura e il suo Next, che e' la strategia dei sette
  giorni, un'altra cosa.

### 2. Gli agenti — `.claude/agents/`

- `06_next.md` si cancella.
- `07_summary.md` si riscrive: **il soggetto sono le quattro sezioni del
  corpo**, non la giornata intera. Un pezzo solo, voce del mattino. Via la
  parte sole/luna del todo 49, via la delega a Next («there is nothing left to
  decide today, and tomorrow is Next's»), e via il giudizio sulla seduta, che
  adesso e' tutto nel commento della sera.
- `05_training.md` **non cambia**: dal todo 64 guarda gia' sia il piano sia
  l'esecuzione, che e' esattamente il punto 3 dello schema.

### 3. I timer — `deploy/crontab`

Le quattro righe passano da `0 10` e `0 22` a `0 8` e `0 21`. Resta la
divisione fra i giorni soli e la coppia col settimanale (lunedi e domenica).

### 4. Il frontend

- `SummaryCard.tsx`: da due `Part` a una. I due `SummaryPart` e il
  `tone="moon"` spariscono; resta il riquadro con il testo, l'ora e il tasto.
- `TrainingCard.tsx`: perde `comment`, `commentWrittenAt` e `refresh`, e con
  loro il blocco `.prose` e il `WrittenAt`. Diventa la card della sola seduta.
- `TrainingCommentCard.tsx` (nuovo): il testo della sezione Training, l'ora e
  il tasto. Cornice `.card` e `CardHead` come tutte le altre.
- `DayPage.tsx`: nel Report via `<NextCard>` e via la riga `.head-row` (il
  Summary diventa una card a tutta larghezza sopra la griglia, e
  `.summary-card` e' gia' `flex-direction: column`); nella Training la terza
  card dopo la seduta. `sectionButton("summary")` al posto dei due.
- `NextCard.tsx` **resta**: lo usa la Week. Va via solo dalla Day.

### 5. I report vecchi

`summary/01.daily/` ha settantanove giorni scritti con le chiavi di prima: i
loro file si chiamano `summary_morning.md` e `summary_evening.md`, e il
titolo nel report composto e' «Morning summary». Cercando «Summary» non si
troverebbe niente, e **tutti i giorni passati mostrerebbero un Summary
vuoto**.

Quindi la card legge `Summary` e, non trovandolo, ricade su `Morning summary`
e poi su `Evening summary`. Tre righe in `markdown.tsx`, e settantanove giorni
che continuano a leggersi. Il `next.md` dei giorni vecchi invece resta su
disco e non si mostra piu': e' voluto.

### 6. `README.md`

Le due pagine e i due giri, la tabella delle ore, e il paragrafo che spiega
perche' Next non c'e' piu'.

## Rischi

- **L'`assert` del backfill** (`sections.py:236-237`) fa fallire l'import se la
  mappa non nomina ogni sezione: toccando `SECTIONS` senza toccare
  `_DAY_BACKFILL` non parte piu' niente, API compresa. E' una rete, non un
  rischio, ma e' la prima cosa che si rompe.
- **Il tasto Refresh rifa' tutto a qualunque ora.** Premuto alle 21:30
  riscrive anche Health, Recovery e Summary, con la voce della sera. E' il
  comportamento di oggi e non cambia; va solo saputo che il Report puo' essere
  riscritto fuori dal suo giro.
- **Nessun report vecchio si aggiorna da solo.** I giorni passati tengono i
  loro otto frammenti; la pagina ne mostrera' sei, con il Summary preso dal
  ripiego.
- **Il Summary non vede piu' la seduta**, per costruzione: gira alle otto,
  quando il commento della sera non c'e' ancora. Se un giorno si volesse un
  verdetto che tiene insieme corpo e seduta, va in un terzo giro, non qui.

## Verifica

1. **L'import regge**: `uv run python -c "import training.api.app"`, che e'
   dove scattano gli assert del registro.
2. **I due giri scrivono quello che devono**, senza lanciare gli agenti: i
   prompt e l'elenco delle sezioni per `--moment morning` e
   `--moment evening`. La mattina cinque sezioni e nessuna di loro e'
   `training`; la sera una sola.
3. **Un giro vero** su un giorno vecchio: `--moment evening --no-update`
   scrive solo `training.md`; `--moment morning --no-update` scrive le altre
   cinque, fra cui `summary.md`.
4. **Il Report** mostra cinque card: un Summary a tutta larghezza e le
   quattro del corpo. Niente Next.
5. **La Training** mostra tre card, in ordine: Plan, la seduta, il commento.
   Il tasto del commento rifa' la sola sezione Training.
6. **Un giorno vecchio** (per esempio 2026-10-05, che ha `summary_morning.md`)
   mostra il Summary dal ripiego, non un riquadro vuoto.
7. **La Week non e' cambiata**: Snap con Next e Summary a due colonne,
   apertura e chiusura al loro posto.
8. `make frontend_types` se qualche modello cambia, `npm run typecheck`,
   `npm run build`, e le pagine nei due temi in Firefox headless.

## Come e' andata

Fatto come scritto, con due deviazioni da registrare.

**Il ripiego dei report vecchi non sta in `markdown.tsx`.** Il todo diceva
tre righe li', e li' non potevano stare: `_fragment_sections` in `app.py`
costruisce l'elenco delle sezioni **dal registro**, cercando `<chiave>.md`.
Con il registro nuovo il titolo «Morning summary» non esiste piu' come
sezione, quindi al frontend non arriva niente su cui ricadere. Il ripiego sta
dove si leggono i file: `_OLD_FRAGMENTS` e `_fragment_path`, che del `summary`
cercano prima `summary_evening.md` e poi `summary_morning.md`. La luna prima
del sole: su un giorno concluso e' lei il verdetto.

**`SummaryCard` non e' diventata a un pezzo**, perche' la usa anche la Week,
che di pezzi ne ha due veri (il lunedi e la domenica). `evening` e' diventata
opzionale: senza di lei la card e' un pezzo solo e l'occhiello dice «Summary»
senza aggiungere altro, che non c'e' niente da cui distinguerlo. La Week non
e' stata toccata.

Altre cose decise per strada:

- **La card della seduta si chiama «Session»**, non piu' «Training»: con il
  commento in un riquadro a parte, due card di nome «Training» nella vista
  «Training» non si distinguevano. Il commento e' «Comment».
- **Il ramo `next` di `_planned` resta scritto**, con un commento che dice
  che adesso lo prende solo la settimana. La domanda e' la stessa per tutti e
  due, e se il consiglio del giorno tornasse non ci sarebbe niente da
  riscrivere.
- **`.head-row` non si tocca.** Il Report non la usa piu' — il Summary e' una
  card a tutta larghezza — ma la griglia a due colonne serve ancora allo Snap
  della Week.

### Come e' stato verificato

- **L'import**, che e' dove scattano gli assert del registro (backfill
  completo e verdetti in coda): `import training.api.app` passa. I due
  assert hanno fatto il loro lavoro durante il lavoro, fermando l'import
  finche' `_DAY_BACKFILL` nominava ancora otto chiavi.
- **Tutti gli agenti del registro esistono**: controllato per nome sui file
  di `.claude/agents/`, dopo aver cancellato `06_next.md`.
- **I due prompt**: quello del Summary dice «This is the morning run» e
  manda a leggere i frammenti; quello del Training dice «This is the evening
  run» e nomina il piano del giorno.
- **I due giri veri**, sul 27 ottobre, con `--no-update`. La sera: una
  sezione, `training done`, e l'unico file riscritto e' `training.md`. La
  mattina: cinque sezioni, tutte `done`, e i file riscritti sono esattamente
  `health`, `load`, `recovery`, `fitness` e `summary`. Il `summary.md` nuovo
  parla del solo corpo e chiude con una clausola di direzione: «You are in
  good order and ready to be used (...) Train, but keep it easy.» — nessun
  numero, nessuna parola sulla seduta.
- **Il report composto**: `GET /api/reports/daily/2026-10-27` rende sei
  sezioni (Summary, Training, Recovery, Health, Load, Fitness) con ore
  diverse, come deve essere con due giri.
- **Il ripiego**: `GET /api/reports/daily/2026-08-01`, un giorno scritto con
  le chiavi vecchie, rende un Summary pieno — preso da `summary_evening.md` —
  invece di un riquadro vuoto.
- **Le pagine**, in Firefox headless, leggendo le `aria-label` dal DOM:
  - Report del 27: `["Summary", "Health", "Load", "Recovery", "Fitness"]`,
    nessuna `.head-row`, occhiello «Summary» e basta;
  - Training del 27: `["Plan", "Session", "Comment"]`, col commento che
    comincia «Five easy kilometres at 7'15"-7'40" with six...»;
  - Report del 1 agosto: le stesse cinque card, Summary compreso;
  - Week/Snap: invariata — `Next · next week`, `Summary · week start`,
    `Summary · week end`, e la riga a due colonne ancora al suo posto.
- `make frontend_types` (una riga: la descrizione di `sections`),
  `npm run typecheck` e `npm run build` puliti.

### Cosa resta su disco

Nei giorni gia' scritti restano `next.md`, `summary_morning.md` e
`summary_evening.md`. Non si leggono piu' — tranne i due summary, quando il
`summary.md` manca — e non si cancellano: sono il testo che quei giorni
avevano, e buttarlo per far quadrare un registro sarebbe la cosa sbagliata.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_66'$" --format=%H -1)
```

Effetti fuori dal repo: il `summary.md` del 27 ottobre resta nella cartella
del giorno, e con lui le cinque sezioni riscritte dalla verifica. Il codice
vecchio non legge `summary.md` e tornerebbe a `summary_morning.md` e
`summary_evening.md`, che sono ancora li': il giorno si rileggerebbe come
prima, col verdetto di prima. Il `cron` installato va reinstallato con
`make install_cron` per tornare alle 10 e alle 22.

Dopo il revert, rifare il merge di `todo_66` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
