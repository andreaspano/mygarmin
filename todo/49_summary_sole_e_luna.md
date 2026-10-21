---
status: done
---

# Il Summary in due: il sole e la luna

Dal todo 47 il report si scrive due volte al giorno, e il Summary ha gia' due
mestieri: la mattina giudica la giornata che comincia, la sera quella finita.
Ma il file e' uno solo, `summary.md`, quindi **il giro delle 22 cancella il
verdetto delle 10**. Il consiglio del mattino — "train, easy" — sparisce
proprio quando diventerebbe interessante confrontarlo con com'e' andata.

Due parti, due icone. Il **sole** lo scrive il giro del mattino, la **luna**
quello della sera. La mattina si vede solo il sole, perche' la luna non
esiste ancora: non serve nessuna regola sull'orario, basta mostrare quello
che c'e'.

## Decisioni

Prese con Andrea il 2026-10-21:

- **Un riquadro solo, due blocchi**: Summary resta accanto a Next, con il
  sole sopra e la luna sotto. La riga in alto non diventa di tre.
- **La luna legge il sole.** La sera gira dopo, quindi il verdetto del
  mattino e' gia' su disco: puo' chiudere il cerchio — "stamattina dicevo di
  tenerla facile, e l'hai tenuta facile".
- **Icone a glifo**, il sole e la luna, nel cerchio colorato che gia' usano
  la freccia di Next e le tre righe di Summary. Niente da disegnare.

Lo storico non vincola: **un solo giorno** ha un `summary.md` (il 20
ottobre), e i 77 giorni a file unico sono anteriori alle sezioni e un Summary
non ce l'hanno proprio.

## Work

### 1. Due sezioni — `src/training/api/sections.py`

`summary` si sdoppia in due chiavi, stesso agente:

```python
Section("summary_morning", "Morning summary", "07_summary", True),
Section("summary_evening", "Evening summary", "07_summary", True),
```

in cima a `SECTIONS`, nell'ordine sole-luna. In `_RUN_KEYS` vanno **dopo
`next`**, e `summary_morning` prima di `summary_evening`: conta solo quando
girano insieme (il tasto grande), ma li' la luna deve trovare il sole gia'
scritto.

Le due `assert` del modulo controllano `RUN_ORDER[:5]` e `[5:]` per indice:
vanno riscritte sulla proprieta' (`reads_fragments`), non sulla posizione,
perche' adesso le sezioni sono otto.

`MOMENT_SECTIONS` cambia di una voce per giro:

| | sezioni |
|---|---|
| mattina | health, recovery, load, fitness, next, **summary_morning** |
| sera | load, fitness, training, next, **summary_evening** |

I titoli non collidono con `REPORT_SECTION_ICONS` in
`interface/report_text.py` (nessuna delle sue chiavi compare in "Morning
summary"), quindi `section_icon` rende `None` per tutte e due, come gia' fa
per "Summary": le icone del riquadro sono glifi, non file.

### 2. Il riquadro — `frontend/src/components/SummaryCard.tsx`

Da un corpo a due. La card prende due coppie (testo, ora) piu' i due tasti, e
rende un blocco per ognuna che non sia vuota, nella struttura che gia' c'e':
`.next-main` con l'icona nel cerchio, l'occhiello, il testo e l'ora.

- Occhiello "SUMMARY · MORNING" e "SUMMARY · EVENING", sul modello di
  "NEXT · TOMORROW" che e' li' accanto.
- **Un tasto per blocco**, perche' sono due sezioni e ognuna ha il suo
  agente: `sectionButton("summary_morning")` e `sectionButton("summary_evening")`.
- Nessun blocco scritto: resta "No summary for this day." una volta sola.

In `DayPage.tsx` la chiamata passa da `sectionBody(report, "Summary")` alle
due nuove, per titolo.

Il CSS: una regola per separare i due blocchi (`.summary-card .next-main +
.next-main`) e il colore del cerchio della luna. Il sole tiene
`--summary-accent`, la luna lo prende piu' spento, cosi' si legge che la
seconda e' la stessa cosa in un altro momento. **Da guardare a schermo**:
`.next-icon` ha `font-weight: 700` e i due glifi in grassetto potrebbero
risultare pesanti.

### 3. Il prompt — `.claude/agents/07_summary.md`

L'agente e' lo stesso e i due rami ci sono gia' (todo 47). Cambia una cosa:

**il ramo della sera legge il mattino.** Fra i frammenti della cartella
adesso c'e' anche `summary_morning.md`, ed e' suo: il verdetto con cui la
giornata e' cominciata. Il prompt gli dice di chiudere il cerchio quando c'e'
qualcosa da chiudere — la mattina aveva detto di tenerla facile e lui l'ha
fatto, oppure aveva detto che c'era spazio per il lavoro duro e lo spazio e'
rimasto li'. **Senza ripeterlo**: il sole sta sopra, visibile, e riscriverlo
con altre parole non serve a nessuno.

Il nome del file su cui scrivere lo da' gia' il prompt dell'orchestratore,
quindi non va detto qui. Il ramo del mattino non cambia.

### 4. Il frammento vecchio

`summary/01.daily/2026-10-20/summary.md` resta orfano: nessuna sezione lo
legge piu'. Non serve una ricaduta nel codice per un file solo — si rigenera
quel giorno nella verifica, e il file rimasto si cancella a mano.

## Vincoli

- Nessuna dipendenza nuova; il modello dell'API non cambia (`Report` ha gia'
  una lista di sezioni), quindi `make frontend_types` deve lasciare
  `schema.ts` identico.
- `make update_activity` non si chiama: le prove degli agenti con
  `--no-update`.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Due verdetti sullo stesso giorno possono contraddirsi** senza che sia un
  errore: la mattina il corpo era pronto, la sera la seduta ha detto altro.
  La luna deve poterlo dire, ed e' proprio il motivo per cui legge il sole.
- **Un agente in piu'** solo quando si preme il tasto grande (otto sezioni
  invece di sette). I due giri dei timer restano a sei e cinque.
- **Il riquadro raddoppia di altezza la sera** e la riga in alto diventa
  sbilanciata rispetto a Next. Da guardare.

## Verifica

1. `uv run python -c "from training.api import sections, refresh"`, e
   `MOMENT_SECTIONS` che rende sei chiavi la mattina e cinque la sera.
2. `training-daily-report --day 2026-10-20 --moment morning --no-update`
   scrive `summary_morning.md` e **non** tocca `summary_evening.md`; poi
   `--moment evening` scrive la luna, che si riferisce a quanto detto la
   mattina senza ripeterlo.
3. `make frontend_types` lascia `schema.ts` invariato; `npm run typecheck` e
   `npm run build`.
4. La pagina in Firefox headless nei due temi: un giorno con tutti e due i
   blocchi, uno con il solo sole (oggi, finche' non gira la sera) e uno senza
   nessuno dei due. I due tasti che rifanno il blocco giusto.
5. Un giorno a file unico (2026-10-11): il report vecchio si legge ancora, e
   il riquadro Summary dice che non c'e'.

## Come e' andata

Fatto come scritto. Due note:

- **`.next-card` e' flex in riga**, pensato per Next che mette i chip a
  destra: con due blocchi dentro sarebbero finiti affiancati invece che uno
  sopra l'altro. `.summary-card` adesso dichiara `flex-direction: column`.
- **Il `summary.md` del 20 ottobre non l'ho cancellato.** Nessuna sezione lo
  legge piu', quindi e' innocuo, ma `summary/` lo produce la pipeline e
  toccarlo a mano non e' cosa mia. Se da' fastidio:
  `rm summary/01.daily/2026-10-20/summary.md`.

La prova che contava e' riuscita: il sole del 20 ottobre chiude con "Train,
and let the fast day wait for a fresher morning", e la luna — scritta dopo,
leggendolo — apre con "The day went the way it was asked to" e chiude con
"The sharp work your load is missing is still missing". Il cerchio si chiude
senza che una parola del mattino venga ripetuta, ed e' esattamente quello che
il prompt chiedeva. Il file del sole non e' stato toccato dal giro della
sera (`mtime` identico).

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_49'$" --format=%H -1)
```

Effetti fuori dal repo: restano i frammenti scritti durante la verifica —
`summary_morning.md` e `summary_evening.md` del 2026-10-20 e
`summary_morning.md` del 2026-10-21. Dopo il revert nessuno li legge piu' (le
chiavi tornano a essere `summary`), e quei due giorni restano senza verdetto
finche' non si rifa' la sezione con `make daily_report DAY=... SECTION=summary`.
Il vecchio `summary.md` del 20 ottobre e' ancora li' e tornerebbe a
funzionare da solo.

Dopo il revert, rifare il merge di `todo_49` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
