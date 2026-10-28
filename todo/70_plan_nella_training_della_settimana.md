---
status: done
---

# La card Plan nella Training della settimana

La vista Training della Week (todo 68) ha le sedute e il commento: quello che
si e' fatto. Manca l'altra meta' — **cosa chiedeva la settimana** — che e'
quello che la Day ha dal todo 63.

Il piano della settimana c'e' gia' in una vista sua, il **Plan**. Metterci la
stessa card sarebbe la duplicazione che i todo dal 66 al 69 hanno passato il
pomeriggio a togliere. Quindi la card e' **diversa dalla vista**, e la
differenza e' il punto.

## Due domande sullo stesso file

- **La vista Plan ha il documento**, da leggere: la tabella dei sette giorni
  col perche' dentro, i ritmi, i segnali per scaricare, e i quattro numeri
  del blocco in cima.
- **La card Plan ha i numeri che chiedeva**, da mettere accanto alle sedute
  fatte due riquadri sotto: quante sedute, quanti chilometri, la piu' lunga,
  quante di qualita' e quanti riposi.

La prima si apre quando si vuole sapere **com'era scritto**, la seconda si
legge di sfuggita per sapere **quanto chiedeva**. Lo stesso file, due usi.

## I totali li conta l'API

Il piano quella riga se la scrive da solo nel testo — «**Totals:** **26 km**
of running · longest run 14 km · 1 quality session · 4 rest days» — ma e'
**prosa scritta a mano**, e un numero che deve stare accanto a un altro
numero non si prende da una frase. Si contano dalle sette sedute del front
matter, che e' la parte che una macchina deve leggere.

Il conto e' una verifica del file, non un suo sostituto: sulla settimana del
26 ottobre i quattro numeri contati sono gli stessi quattro scritti. Quando
non tornassero, e' il file a dire cos'e' che l'autore voleva.

**Gli intervalli restano intervalli.** Una settimana di `[10, 11]` piu'
`[14, 16]` chiede «24-27 km», non una media che nessuno ha scritto.

## Work

- `api/plans.py`: `_planned_week(sessions)`, piu' `_distance_ends` e
  `_km_label`. `load_week_plan` smette di ignorare `sessions`: non le manda
  una per una — per quelle c'e' `load_day_plan`, un giorno alla volta — ne
  prende i totali.
- `api/models.py`: `PlannedWeek` e il campo `planned` su `WeekPlan`, nullo
  per un file scritto prima che il front matter avesse le sedute.
- `WeekPlanCard.tsx`: `WeekPlanStats` diventa esportata, e accanto nasce
  `WeekPlanBrief` — la card compatta. La cornice c'e' sempre, come nella Day:
  una settimana senza piano la lascia vuota invece di far sparire un riquadro
  su tre.
- `WeekPage.tsx`: la card in testa alla Training, e il piano si chiede anche
  su quella vista.
- `make frontend_types`, `README.md`.

## Verifica

1. L'endpoint rende `planned` con i cinque numeri su una settimana del
   blocco, e `null` sul file di settembre 2026.
2. I quattro numeri contati tornano con la riga «Totals» del file.
3. Nella pagina: la card in testa alla Training, con i quattro riquadri del
   blocco e i quattro dei totali.
4. Una settimana col file vecchio mostra i trattini e nessun totale; una
   senza file lascia la cornice vuota.
5. La vista Plan non cambia.

## Come e' andata

Fatto come scritto.

**Gli intervalli hanno deciso la forma dei campi.** Il primo impulso era
mandare numeri — `planned_km: float` — e sarebbe stato sbagliato per i piani
che scrivono `distance_km: [10, 11]`: sommare i minimi o le medie e' inventare
un numero che il piano non ha scritto. I campi sono due etichette,
`distance_label` e `longest_label`, costruite dai due estremi e collassate
quando coincidono. Lo stesso mestiere di `_distance_label` del todo 63, su una
settimana invece che su un giorno.

**Un inciampo da registrare**, perche' si ripresentera'. Il dizionario che
`load_week_plan` rende finisce con `"written_at": ..., "body": text, }`, e la
stessa coda ce l'ha il loader dei piani di `plan/`: la sostituzione per testo
trovava **due** occorrenze e si fermava. Il rimedio e' cercare dopo
`s.index("def load_week_plan(")`. In quel file i due loader si somigliano di
proposito — un piano settimanale e' un file di piano con altre chiavi — e
chiunque ci faccia una sostituzione cieca ci ricade.

### Come e' stato verificato

- **Il conto contro il file**, che e' la prova che conta: sulla settimana del
  26 ottobre `planned` dice `sessions 3, rest_days 4, quality 1,
  distance_label "26 km", longest_label "14 km"`, e la riga «Totals» del file
  dice «26 km of running · longest run 14 km · 1 quality session · 4 rest
  days». Quattro numeri su quattro. Sulla settimana del 30 novembre: 3 sedute,
  38 km, la piu' lunga 18, due di qualita'.
- **Gli intervalli**, provati a mano su sedute inventate: `[10, 11]` e
  `[14, 16]` danno «24-27 km» e «14-16 km».
- **Il file vecchio**: la settimana del 28 settembre, che il front matter non
  ce l'ha, rende `planned: null`.
- **L'endpoint**: `GET /api/weekly/2026-10-26/plan` porta i cinque campi.
- **Le pagine**, in Firefox headless, leggendo le `aria-label` e i riquadri:
  - Week/Training del 26 ottobre: `[Plan, Sessions, Comment]`, e nella card
    `Phase=base, Block week=1 of 18, Race=28 Feb 2027, Target=2:20,
    Sessions=3, Distance=26 km, Longest=14 km, Quality=1` con «4 rest days»
    sotto;
  - 28 settembre: i quattro riquadri del blocco a trattino e **nessuna riga
    di totali**;
  - 19 ottobre, settimana senza piano: la cornice c'e' e dentro non c'e'
    niente;
  - Week/Plan del 26 ottobre: il documento intero, invariato.
- `make frontend_types`, `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_70'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Si legge e si conta, niente si scrive:
nessuna chiamata a Garmin, nessun file in `summary/`, nessuna colonna nuova.

Dopo il revert, rifare il merge di `todo_70` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
