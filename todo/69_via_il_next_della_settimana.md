---
status: done
---

# Via il Next anche dalla settimana

Il todo 68 ha portato il Next della settimana nella vista Training, in coda
alle sedute e al commento. Andrea ha chiesto di togliere quella card.

**E non solo la card.** Una card che non c'e' piu' e una sezione che si
scrive ancora vuol dire un agente che gira ogni domenica per un testo che
nessuno legge — che e' esattamente la condizione da cui il todo 60 ha tirato
fuori i piani settimanali («diciannove file nel repo, e nessun modo di
leggerli dall'interfaccia»). Quindi via la card, via la sezione, via
`w6_next`.

## Cosa resta senza

Il Next della settimana era **l'unica cosa che adattava la forma del blocco a
com'era andata la settimana appena finita**. Il suo prompt aveva le tre
diramazioni: le sezioni sono d'accordo col piano e lo prescrive com'e'; non
lo sono e dice cosa ha tagliato e perche'; una settimana di scarico resta di
scarico. Adesso nessuno le percorre.

Con il Next del giorno (todo 66) il conto e' chiuso: **le sezioni raccontano,
nessuna prescrive**. Quello che si deve fare lo dice il piano scritto a mano
in `summary/05.plan/<lunedi>.md`, e lo si segue come e' scritto. Chi vorra'
l'adattamento lo riscrivera' nei piani, non in un agente.

## Work

- `WeekPage.tsx`: via la `<NextCard>` dalla vista Training e il suo import.
- `api/sections.py`: `next` via da `WEEK_SECTIONS`, `_WEEK_RUN_KEYS`,
  `WEEK_MOMENT_SECTIONS` e `_WEEK_BACKFILL`. Giorno e settimana hanno ora
  **le stesse sei sezioni**.
- `.claude/agents/w6_next.md`: cancellato.
- `.claude/agents/w7_summary.md`: non legge piu' `next.md`, e la regola «no
  advice» cambia motivo — non piu' «e' il lavoro di Next» ma «la forma della
  settimana che viene sta nel piano, e non e' tua da rivedere».
- `api/models.py`: la descrizione delle chiavi di `RefreshStatus.sections`,
  che adesso sono le stesse per i due periodi.
- `api/refresh.py`: il ramo `next` di `_planned` era **codice morto** —
  nessun periodo ha piu' quella sezione — e con lui `_next_subject`, che
  esisteva solo per dire «la sera parla di domani».
- `frontend`: `NextCard.tsx` e `nextParts` in `markdown.tsx` non li usa piu'
  nessuno, e vanno. Il CSS di Next resta solo dove serve al Summary, che la
  cornice `.next-card` se l'e' ereditata: via il titolo, la colonna di destra
  e i chip della seduta.
- `README.md`.

## Verifica

1. L'import regge, con gli assert del registro.
2. Sei sezioni per la settimana, le stesse del giorno, e sei agenti
   `w*`.
3. Un giro vero scrive sei sezioni e nessun `next.md`.
4. Nessuna pagina mostra piu' un riquadro `Next session`.
5. `npm run typecheck` e `npm run build` puliti, e nessun componente orfano.

## Come e' andata

Fatto, e il grosso e' stato il codice morto che si e' tirato dietro.

### Quattro cose che sono rimaste senza nessuno

- **`_planned`** aveva ancora il ramo `if section.key == "next"`, lasciato
  apposta dal todo 66 «se un giorno il consiglio del giorno tornasse». Con la
  settimana senza Next quel ramo non lo prende nessuno: via. La funzione
  adesso serve **una sezione sola**, il Training del giorno.
- **`_next_subject`** esisteva solo per quel ramo — la data per cui Next
  prescrive, che non e' quella del report. Via anche lei.
- **`NextCard.tsx`**: la Day l'ha lasciata col todo 66, la Week qui. Niente
  la importa piu': cancellata.
- **`nextParts`** in `markdown.tsx`, che spezzava il testo di Next in titolo,
  perche' e passi: la usava solo `NextCard`.

Nel CSS la cornice scura **resta**, perche' `SummaryCard` e' un
`.next-card summary-card` e se l'e' ereditata. Sono andati solo i pezzi che
erano di Next e di nessun altro: il titolo `h2`, la colonna di destra
(`.next-session`) e i chip della seduta (`.chips`). Il nome della classe
resta, con un commento che dice perche': rinominare sei regole e due
componenti per un riquadro solo costa piu' di quanto rende.

### Come e' stato verificato

- **L'import** passa, e il registro dice le stesse sei sezioni per i due
  periodi: `summary, training, recovery, health, load, fitness`. Gli agenti
  della settimana sono sei, `w1_health` ... `w5_training` e `w7_summary`, e
  nessuno dei due registri nomina un file che non c'e'.
- **Un giro vero** sulla settimana del 19 ottobre: `6 sezioni`, tutte `done`,
  e i file riscritti sono esattamente `health, load, recovery, fitness,
  training, summary`. Nessun `next.md`.
- **Le pagine**, in Firefox headless: nessun riquadro `Next session` da
  nessuna parte. Week/Snap `[Summary, Health, Load, Recovery, Fitness]`,
  Week/Training `[Sessions, Comment]`, Day/Snap e Day/Training invariate.
- `make frontend_types` (una riga: la descrizione delle chiavi),
  `npm run typecheck` e `npm run build` puliti.

### Cosa resta su disco

Il `next.md` delle settimane gia' scritte, e quello dei giorni dal todo 66.
Non si legge e non si cancella: e' il testo che quei periodi avevano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_69'$" --format=%H -1)
```

Effetti fuori dal repo: le sei sezioni della settimana del 19 ottobre restano
riscritte dalla verifica, e il suo `next.md` e' quello di prima — il codice
vecchio lo rileggerebbe e la card tornerebbe a mostrarlo.

Dopo il revert, rifare il merge di `todo_69` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
