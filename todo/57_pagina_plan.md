---
status: done
---

# Plan: i piani di allenamento nella pagina

I piani di allenamento stanno in `plan/`, un file Markdown per piano, scritti
a mano. Fino a qui si leggevano solo da editor: la pagina non li conosceva.

Qui si aggiunge la voce **Plan** alla barra e la pagina che li mostra.

## Dove va, nella barra

Non fra Day e Week: quelle sono periodi e guardano indietro, un piano guarda
avanti a una gara e dura quanto dura il blocco. Sta a destra, accanto ad
Activities, e nell'URL e' `?period=plan&plan=<slug>`, cioe' il nome del file
senza `.md`.

## Il formato

Front matter YAML davanti al testo, nello spirito del todo 14 ma per un blocco
intero: le chiavi dicono la gara (`race`, `race_name`, `distance_km`,
`target_time`, `target_pace_min_km`, `target_speed_kmh`, `block_start`,
`block_weeks`, `peak_weekly_km`), non le sedute dei sette giorni.

**Il front matter non e' obbligatorio.** Un file che non ce l'ha non si salta:
si mostra col solo testo e i riquadri vuoti. Un piano invisibile perche' gli
manca una chiave sarebbe peggio di un piano senza numeri in cima.

Il titolo non sta nel front matter: e' il primo `# ...` del testo, che la
pagina si prende per la sua intestazione e toglie dal corpo.

## Work

- `api/plans.py`: `load_plans(folder)`, una riga per file, la gara piu' vicina
  per prima e, a pari gara, il bersaglio piu' veloce. Un front matter che YAML
  non legge vale come assente.
- `PlanSummary`, `Plan` (con `body`) e `PlanList` in `api/models.py`, sulla
  falsariga di `Activity`/`ActivityDetail`.
- `GET /api/plans` (elenco senza testi, per il selettore) e
  `GET /api/plans/<slug>` (un piano col suo Markdown). Lo slug si cerca fra i
  file trovati, **non** si attacca a un percorso: non puo' uscire da `plan/`.
- `plan_dir` in `UserContext`, come `summary_dir`.
- `components/PlanPage.tsx`: i riquadri in cima dal front matter (la gara,
  quanti giorni mancano, il bersaglio, il ritmo, la velocita', la settimana
  piu' pesante), il selettore dei piani, il testo sotto.
- `markdown.tsx`: **titoli e tabelle**, che i report non hanno e un piano si'.
  I titoli partono da `h2`, l'`h1` e' il titolo della pagina.
- `dayDiff` in `format.ts` per i giorni che mancano alla gara.

## Vincoli

- Niente libreria di Markdown: trenta righe in `markdown.tsx`, come il resto.
- Niente elenco di piani nel codice: un file nuovo in `plan/` si vede
  ricaricando.
- Le tabelle larghe scorrono dentro il loro riquadro, non fanno scorrere la
  pagina.
- Commenti in italiano senza accenti, UI in inglese.

## Verifica

1. `GET /api/plans` da' i tre piani della mezza del 28 febbraio, dal 2h10 al
   2h30; `GET /api/plans/half_marathon_2.20` porta anche il testo.
2. Un file senza front matter si vede comunque, titolo dal `#` e riquadri a
   trattino.
3. Uno slug inventato da 404, e `?plan=` con uno slug che non c'e' apre il
   primo piano invece di una pagina vuota.
4. Il Markdown dei tre piani reso fuori dal browser: otto tabelle e undici
   titoli per piano, nessuna stanghetta rimasta nel testo. Sui frammenti dei
   report di un giorno, solo paragrafi ed elenchi come prima.
5. `npm run typecheck` e `npm run build`.
