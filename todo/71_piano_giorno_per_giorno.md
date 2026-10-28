---
status: done
---

# La card Plan della settimana: i sette giorni, non i totali

Il todo 70 ha messo una card Plan nella vista Training della Week e ci ha
messo dentro **i totali** — quante sedute, quanti chilometri, la piu' lunga,
quante di qualita', quanti riposi. Guardandola, ad Andrea non e' piaciuta: di
una settimana si vuole il piano **giorno per giorno**, che e' come la
settimana e' fatta.

Quindi i totali via, e al loro posto le sette sedute: una riga per giorno.

```
Mon 26 Oct   Rest
Tue 27 Oct   Running · easy · 5 km
Wed 28 Oct   Rest · or Cycling
Thu 29 Oct   Running · quality · 7 km
Fri 30 Oct   Rest
Sat 31 Oct   Rest · or Cycling
Sun 1 Nov    Running · long · 14 km
```

## Perche' non e' la vista Plan

E' la domanda che il todo 70 aveva impostato bene e riempito male. La vista
Plan ha il **documento**: la tabella con dentro il perche' di ogni seduta
(«Quality, the first in months: 2 km easy, then 4 x 5 min at 5'55"-6'05"...»),
i ritmi, i segnali per scaricare. Si apre e si legge.

La card ha le stesse sette sedute come **dati**: sport, tipo, distanza, in
sette righe corte. Si scorre con un'occhiata, accanto alle sedute che hai
fatto due riquadri piu' sotto. Lo stesso file, due usi — e due forme, che e'
quello che tiene le due cose dall'essere la stessa.

## Work

- `api/models.py`: `PlannedSession` — la seduta di un giorno nei suoi campi —
  e `DayPlan` che **eredita** da lei, come `ActivityDetail` da `Activity`:
  una seduta con attorno da che file viene. `WeekPlan.sessions` al posto di
  `planned`, e `PlannedWeek` sparisce.
- `api/plans.py`: `_session(entry, day, text)`, i campi di una voce, usata da
  tutti e due i loader; `_planned_sessions(meta, text)` per le sette. Via
  `_planned_week`, `_distance_ends` e `_km_label`, che servivano ai totali.
  `load_day_plan` adesso e' `{**_session(...), week, file, written_at}`.
- `components/PlanSession.tsx` (nuovo): il tipo `Sport`, `sessionLabel`,
  `sessionIcon` e `PlanLine`. La composizione del testo era dentro
  `DayPlanCard` e la card della Week avrebbe dovuto copiarla; e il tipo
  `Sport` era dichiarato due volte.
- `components/WeekPlanCard.tsx`: `WeekPlanBrief` rifatta — i quattro riquadri
  del blocco e l'elenco dei sette giorni.
- `styles.css`: `.plan-days` e `.plan-day`. Una griglia a tre colonne, non
  una tabella: sono sette righe corte, e una tabella aggiungerebbe bordi e
  allineamenti per nulla.
- `make frontend_types`, `README.md`.

## Le sedute vanno in ordine di data

Il front matter le scrive da lunedi' a domenica, ma **non e' garantito**: il
file di settembre 2026 ha la tabella che parte dalla domenica, ed e' lo stesso
file che aveva imposto, nel todo 63, di cercare la seduta di un giorno per
data e non per posizione. Una card che le mette in fila le vuole in fila,
quindi `_planned_sessions` ordina per data e salta le voci che una data non
l'hanno — senza quella, una seduta non si sa di che giorno e'.

Quel file il front matter non ce l'ha affatto, quindi per la sua settimana la
card mostra i quattro riquadri del blocco a trattino e nessuna riga. E' la
stessa scelta del todo 63: le sedute a macchina non ci sono, e ricavarle dalla
prosa e' la strada che il todo 14 aveva scartato.

## Verifica

1. L'endpoint rende sette sedute in ordine di data per una settimana del
   blocco, e `null` per il file di settembre.
2. Le sette righe nella pagina, con l'icona di ogni sport.
3. Una settimana col file vecchio: i trattini e nessuna riga. Una senza file:
   la cornice vuota.
4. La vista Plan e la card della Day non cambiano.

## Come e' andata

Fatto. Il grosso e' stato **non copiare**.

`sessionLabel` — «Running · easy · 5 km», e «Rest · or Cycling» per un riposo
con uno sport ammesso — era scritta dentro `DayPlanCard`, con tre righe di
commento su perche' `rest` non passa da `sport.label` (non e' uno sport, non
sta in `/api/sports`, e la chiave cruda si leggerebbe «rest» minuscolo). La
card della Week ne aveva bisogno identica. Copiarla avrebbe messo quelle tre
righe di ragionamento in due posti, e il secondo e' quello che non si aggiorna
mai: e' finita in un file suo, `PlanSession.tsx`, con il tipo `Sport` che era
anche lui dichiarato due volte.

Lo stesso dalla parte dell'API: i campi di una seduta erano scritti dentro
`load_day_plan`, e `_planned_sessions` li voleva per sette. `_session` adesso
li scrive una volta, e `load_day_plan` ci aggiunge attorno `week`, `file` e
`written_at` — che e' esattamente quello che `DayPlan` dice ereditando da
`PlannedSession`. La forma del modello e quella del codice combaciano.

### Come e' stato verificato

- **Le sette sedute** della settimana del 26 ottobre, lette dal loader:
  riposo lunedi', easy 5 km martedi', riposo con bici mercoledi', quality 7 km
  giovedi', riposo venerdi', riposo con bici sabato, long 14 km domenica — e
  ognuna porta anche la riga della tabella, che qui non si mostra ma c'e'.
- **Il file di settembre**: `sessions` e' `null`.
- **`load_day_plan` non e' cambiata**: il 29 ottobre rende ancora
  `running / quality / 7 km` con `week` e `file` attorno.
- **Le pagine**, in Firefox headless, leggendo le righe dal DOM:
  - Week/Training del 26 ottobre: `[Plan, Sessions, Comment]`, sette righe
    `Mon 26 Oct Rest`, `Tue 27 Oct Running · easy · 5 km`, ... `Sun 1 Nov
    Running · long · 14 km`, e sette icone;
  - 28 settembre: i quattro riquadri a trattino, zero righe;
  - 19 ottobre, senza piano: la cornice vuota;
  - Day/Training del 27 ottobre: invariata, `Running · easy · 5 km` col testo
    sotto.
- `make frontend_types`, `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_71'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Si legge e si ordina, niente si scrive.

Il revert riporta i **totali** del todo 70, non la card vuota: il todo 70 e'
il commit prima, e tornarci vuol dire tornare alla card che non piaceva.

Dopo il revert, rifare il merge di `todo_71` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
