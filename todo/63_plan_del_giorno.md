---
status: done
---

# La card Plan: cosa prevedeva il piano, per quel giorno

Il todo 62 ha dato alla seduta una vista sua, **Training**, con la card di
quello che si e' fatto. L'altra meta' manca: **cosa era previsto**.

I piani delle settimane stanno in `summary/05.plan/<lunedi>.md` da fine
settembre, le sette sedute nel front matter e una tabella `Day | Session` nel
testo, ma l'unico posto dove si leggono e' la vista Plan della Week, tutte e
sette insieme. Per sapere cosa il piano prevedeva per **oggi** si apre la Week
e si cerca la riga a occhio.

Qui la vista Training di ogni giorno prende una card **Plan**, sopra quella
della seduta: prima quello che era previsto, poi quello che e' successo.

## La card c'e' sempre

Un giorno senza piano lo dice dentro la cornice invece di far sparire la
cornice. La vista Training ha due riquadri a qualunque data, e uno che va e
viene si legge come un errore. I giorni senza piano non sono pochi: il blocco
parte dal 26 ottobre, e prima c'e' solo la settimana del 28 settembre.

## Due cose in una card

**La riga strutturata** dal front matter — icona dello sport, tipo, distanza,
e lo sport che un riposo ammette comunque — e sotto **il testo di quel
giorno**, la riga della tabella. I campi dicono cosa, il testo dice perche':
«la quality e' giovedi e non martedi: la readiness di oggi vuole prima due
giorni tranquilli». Nessuno dei due da solo e' il piano di quel giorno.

## `sessions` qui si legge

E' il vincolo che decide il lavoro. `load_week_plan` legge il front matter ma
**scarta `sessions` di proposito** (todo 60): la lettura a macchina serviva al
confronto previsto/fatto del todo 14, che non c'e', e un campo che l'API manda
e nessuno guarda non si manda. La tabella dei sette giorni che si vede nella
Week e' il Markdown del corpo, non dati.

Una card del giorno vuole **una** seduta, nei suoi campi, e la tabella del
testo non la da' separata. Quindi `sessions` si legge, da questa parte: il
todo 61 lo diceva gia' — marcare oggi nella tabella «vuole o le sette sedute
del front matter dall'API o la tabella letta dal testo», e di farlo insieme
alla struttura che serve comunque. Questo lavoro fa quella meta', per un
giorno. **Marcare oggi nella vista Plan della Week resta aperto**: il piano
settimanale non guadagna il campo `sessions`, e quando si marchera' si
decidera' allora.

## La settimana del 28 settembre vale come senza piano

E' l'unico file di formato vecchio: niente front matter, e la tabella parte
dalla domenica con otto righe. Un piano per quei giorni si potrebbe tirare dal
testo, ma e' la strada fragile che il todo 14 aveva scartato, e aprirla per un
file solo lascerebbe due strade da mantenere. Vale come settimana senza piano,
e la risposta e' una sola — 404 — per tutti i modi in cui un piano non c'e':
file assente, front matter assente o illeggibile, `sessions` assente, nessuna
voce con quella data. Per chi guarda sono la stessa cosa: quel giorno non e'
previsto niente.

Quel file dimostra anche **perche' la voce si cerca per data e non per
posizione**: ne' l'ordine ne' il numero delle righe sono garantiti.

## Work

- `api/plans.py`: `load_day_plan(summary_dir, day)`, che riusa `week_plan_path`
  (normalizza gia' un giorno qualunque al suo lunedi'), `_front_matter` e i
  coercitori. Piu' `_distance_label`, che del numero o dell'intervallo
  `[min, max]` fa un'etichetta pronta — l'etichetta la fa l'API come fanno
  gia' `Sport.label` e `section_icon`, che nel frontend non si fanno conti
  (todo 52) — e `_day_row`, che cerca la riga della tabella.
- `api/models.py`: `DayPlan`, sullo stampo di `WeekPlan`.
- `api/app.py`: `GET /api/daily/<giorno>/plan`. Un giorno futuro e' permesso,
  al contrario di `/api/daily/<giorno>`: un blocco si scrive in avanti.
- `components/DayPlanCard.tsx`, sullo stampo di `WeekPlanCard`, che ha gia'
  risolto le stesse cose — l'icona `next.png` dei piani, e soprattutto la
  regola che **"Loading…" e "No plan" sono due cose diverse**.
- `api/client.ts`: `dayPlan` con `getOrNull`, che del 404 fa `null`, come
  `weekPlan`.
- `components/DayPage.tsx`: lo stato del piano e un effetto gated su
  `view !== "training"`, sullo stampo di quello della Week; la card prima della
  Training.
- `styles.css`: la sola riga della seduta. Il blocco delle tabelle del todo 61
  **non si tocca**: e' scoped a `.week-plan-card` di proposito.
- `make frontend_types`: `DayPlan` e' un modello nuovo.

## Vincoli

- Nessuna dipendenza nuova. `WeekPlan` non cambia.
- Il testo del giorno e' un **extra**: se la riga non si trova, la card mostra
  la sola riga strutturata. Niente di quello che la card dice dipende dalla
  regex.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Il testo del giorno viene da una regex sul Markdown**, la strada che il
  todo 14 aveva scartato come fragile. Qui regge perche' non decide niente.
  Va tenuto cosi': il giorno in cui l'esito «previsto contro fatto»
  dipendesse da quella regex, la regex e' sbagliata.
- **I mesi non si scrivono con `strftime("%b")`**, che segue la lingua del
  processo: `make api` con LANG italiano direbbe "ott" e la riga non si
  troverebbe piu'. Stanno in una tupla, in inglese come i file.
- **`duration_min` non si legge.** Lo schizzo del todo 14 lo nomina, il
  `README.md` di `summary/05.plan/` no, e nessuno dei diciannove file lo usa.
  Le chiavi sconosciute si ignorano, quindi il giorno che comparisse si
  aggiunge allora.

## Verifica

1. `GET /api/daily/2026-10-29/plan` da' 200 con `running`, `quality`, `7 km` e
   il testo che comincia con «Quality, the first in months»; `2026-10-28` da'
   `rest` con `optional: cycling`; `2026-11-01` da' `long` e `14 km`.
2. `2026-10-20` (fuori dal blocco) e `2026-09-30` (file vecchio) rispondono
   404 col loro `detail`.
3. Nella pagina, su un giorno con piano: la card Plan sopra la Training, la
   riga della seduta con l'icona, il testo del giorno, il nome del file in
   coda. Un riposo con sport facoltativo lo dice.
4. Su un giorno senza piano la cornice c'e' e dice "No plan". Durante la
   richiesta si legge "Loading…", non "No plan".
5. Solo nella vista Training: dal Report e dal Trend non parte nessuna
   richiesta a `/api/daily/*/plan`.
6. La riga mostrata e' quella del file, parola per parola.
7. `make frontend_types`, poi `npm run typecheck` e `npm run build`.
8. La pagina nei due temi.

## Come e' andata

Fatto come scritto, niente deviazioni sulla struttura. Due cose trovate
provando, una delle quali cambia quello che il punto 3 della verifica puo'
davvero controllare.

### "rest" non e' uno sport

La riga diceva **`rest · or Cycling`**, con la r minuscola. `sport.label` viene
da `/api/sports`, e li' `rest` non c'e': gli sport sono quelli delle attivita',
il riposo ha solo la sua icona (`rest_icon`), a parte. Senza una voce in
elenco l'adattatore rende la chiave cruda. Adesso il nome lo scrive la card —
`"Rest"` — come fa gia' `TrainingCard` nel suo stato di riposo. Trovato nel
browser e non dal typecheck: e' una stringa che passa, solo brutta.

### La Day non va nel futuro, e quindi il piano futuro non si vede

`dayFromUrl` (`DayPage.tsx:47-51`) riporta a oggi qualunque `?day=` oltre
oggi. Quindi `?day=2026-11-01` apre il 28 ottobre, e **la card non puo'
mostrare la seduta di un giorno che non e' arrivato**, per quanto l'API la
sappia dare.

La rotta resta giusta cosi' — un blocco si scrive in avanti, e rifiutare il
futuro vorrebbe dire rifiutare il caso per cui esiste — ma va detto:
dell'intero blocco, oggi dalla pagina si raggiungono i tre giorni dal 26 al 28
ottobre. Il resto si vede dalla vista Plan della Week, o con `curl`. Se un
giorno si vorra' sbirciare il piano di domani dalla Day, la cosa da cambiare
e' quel `day > now`, non questa card.

### Come e' stato verificato

**L'API** con `curl`, tutti e sei i casi del punto 1 e 2: il 29 ottobre
`running / quality / 7 km` col testo «Quality, the first in months»; il 28
`rest` con `optional: cycling`; il 1 novembre `long / 14 km`; il 27 `easy /
5 km`. Il 20 ottobre e il 30 settembre rispondono 404 con il loro `detail` —
il secondo e' il file vecchio, che e' la decisione presa qui.

`_distance_label` provata a parte sui casi che i file non hanno: `7` → `7 km`,
`10.5` → `10.5 km`, `[10, 11]` → `10-11 km`, `[10.5, 11]` → `10.5-11 km`, e
niente da un valore che numero non e'.

**La pagina** in Firefox headless, sui tre giorni raggiungibili:

| giorno | riga | testo |
|---|---|---|
| 26 Oct | `Rest` | «**Rest.** Nothing today…», col grassetto reso |
| 27 Oct | `Running · easy · 5 km` | «Easy 5 km at 7'15"-7'40"…» |
| 28 Oct | `Rest · or Cycling` | «Rest, or an easy spin of 45 min.» |

con l'icona giusta ogni volta (`rest.png`, `running.png`) e
`summary/05.plan/2026-10-26.md` in coda. L'ordine dei riquadri letto dal DOM e'
`["Plan", "Training"]`: la card sta sopra, come doveva.

I giorni senza piano (20 ottobre, 30 settembre) mostrano la cornice con "No
plan" dentro, non una cornice che sparisce.

**Il punto 5 verificato per davvero**, non a occhio: contando le richieste in
`performance.getEntriesByType('resource')`, dal Report e dal Trend non parte
**nessuna** chiamata a `/api/daily/*/plan`, e dalla Training ne parte una sola,
quella del giorno mostrato.

**I due temi** sulla card: `rgb(255,255,255)` nel chiaro, `rgb(23,26,34)` nello
scuro, cioe' le variabili di `.card` che c'erano gia'. L'unica regola nuova e'
`.plan-line`.

`make frontend_types` (110 righe in piu' in `schema.ts`), `npm run typecheck` e
`npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_63'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Si legge e basta — nessuna scrittura in
`summary/`, nessuna chiamata a Garmin, nessuna colonna nuova in
`activities.db`.
