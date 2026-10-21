---
status: done
---

# Fitness rifatta sullo stampo di Health e Recovery

Health e' stata rifatta fra il 19 e il 20 ottobre, Recovery il 21 (todo 46):
quattro misure in griglia 2x2, ognuna con la **barra della sua fascia** (la
media dei 28 giorni prima piu' e meno uno scarto tipo, e in tinta piu' chiara
piu' e meno due), niente testo sotto i numeri, e sotto un commento da
allenatore che apre con un verdetto.

Fitness e' l'ultima card rimasta alla forma vecchia: quattro numeri con una
riga di testo sotto ognuno — "Measured 19 Oct · 40.7 four weeks ago",
"Intermediate · 20 Oct", "6:00 /km · 10.0 km/h · Detected 16 Oct".

I dati per le barre ci sono gia': `health_daily` tiene `vo2max`,
`endurance_score` e `hill_score` giorno per giorno, e `_band()` in
`daily_data.py` e' lo stesso conto che serve.

## Decisioni

Prese con Andrea il 2026-10-21:

- **Sotto le tre misure con fascia, solo la barra.** Spariscono le date e il
  livello "Intermediate". Il `+1.2 in 28 days` **non si perde**: sta accanto
  al numero, dentro `value`, non nella riga sotto.
- **La soglia del lattato: solo il numero.** Non ha una serie storica da cui
  ricavare una fascia, quindi niente barra; e sotto non va piu' niente,
  nemmeno il passo e la data. La card diventa uniforme: quattro numeri, tre
  con la barra, uno nudo.
- **Il testo si riscrive sullo stampo di Health**: verdetto in apertura e poi
  tutte e quattro le misure, ogni giorno.

### Una fascia a 28 giorni, come le altre

Misurato sui dati del 2026-10-21: la fascia a 28 giorni e quella a 90 danno
lo **stesso verdetto** su tutte e tre le misure. Non c'e' ragione di
inventare una finestra diversa per questa card.

| | fascia 28g | quel giorno | |
|---|---|---|---|
| VO2max | 40.9 - 41.5 | 41.9 | sopra |
| Endurance | 4842 - 5011 | 4970 | dentro |
| Hill | 48.5 - 54.0 | 55 | sopra |

### La barra si legge al contrario

Per le altre card la fascia e' una **normalita'** attorno a cui il valore
oscilla, e uscirne e' un segnale da guardare. Qui no: queste misure salgono o
scendono lentamente, e **sopra la fascia vuol dire che stai ancora
migliorando**. E' l'opposto di stress o battito a riposo, ed e' un'aggiunta
necessaria a `_style.md`, che oggi elenca solo dove stare sotto e' male.

Ne viene anche una cosa utile: **la fascia si muove ogni giorno anche quando
il valore sta fermo**, perche' e' una media mobile. Un VO2max che resta a
41.9 mentre la fascia lo raggiunge racconta che la salita si e' fermata, ed
e' quello che da' al testo nuovo qualcosa da dire anche nei giorni piatti.

## Work

### 1. Le fasce nei dati — `src/training/interface/daily_data.py`

`_latest_with_change()` guadagna la fascia, calcolata come quelle di
`morning`: `_band(_window(health, column, day, BASELINE_LONG), limits)`.
Stessa funzione, stessa finestra, stesso `MIN_BAND_DAYS = 14`, quindi i
giorni vecchi dello storico restano senza barra e la card regge (lo fa gia'
per Health).

`hill_score` dichiara i limiti `(0, 100)` come readiness e stress (todo 46):
Garmin lo da' in quella scala, e la fascia non deve promettere un 61 che non
esiste. VO2max ed endurance non hanno un tetto.

### 2. Il modello — `src/training/api/models.py`

`Vo2maxNow` e `ScoreNow` guadagnano `band: Band | None`, lo stesso `Band` che
usano gia' le misure di `morning`. `LactateThreshold` e `ThresholdHr` non si
toccano: non hanno fascia e non ne avranno.

`make frontend_types` rigenera `schema.ts`, che va committato.

### 3. La card — `frontend/src/components/FitnessCard.tsx`

- I tre riquadri con fascia passano da `sub={...testo...}` a
  `sub={band && <RangeBar value={now} band={band} />}`. **`RangeBar` va bene
  com'e'**: prende `value` e `band` e sta gia' in `Stat.tsx` (todo 46).
  `MeasureBar` no, perche' vuole un `Measure` con il campo `value`, e qui il
  campo si chiama `now`.
- Il riquadro della soglia perde il suo `sub`. Resta il bivio di oggi fra
  soglia del lattato e frequenza di soglia dell'orologio.
- Spariscono `paceLabel()` e l'import di `shortDayLabel`, che non servono
  piu' a nessuno dei quattro riquadri.
- `Change` resta identico.

**Le barre prendono il blu dell'icona** (`#2563c8`), come Recovery ha preso
il suo cremisi: `.fitness-card { --range-fill; --range-wide-fill; }` nei due
temi, piu' la classe sulla `<section>`. Il meccanismo c'e' gia' in
`styles.css`, sono quattro righe.

### 4. Il testo — `.claude/agents/04_fitness.md` e `_style.md`

In `_style.md`, dopo la riga sulle direzioni: per VO2max, endurance e hill
**sopra la fascia e' buono** (vuol dire che stai ancora salendo) e sotto vuol
dire che stai scendendo.

`04_fitness.md` si riscrive sullo stampo di `01_health.md`:

- **Verdetto in apertura**, una frase corta senza numeri ("the engine is
  still growing", "you are holding where you were", "this is a body losing
  ground"). E' il riassunto: niente seconda frase alla fine.
- Poi **le quattro misure**, una o due clausole ognuna, giudicate contro la
  propria fascia, con il `change` a 28 giorni che resta il soggetto
  principale.
- **Mai un numero che la card non mostra**, con **una sola eccezione
  dichiarata**: della soglia il testo puo' dare anche il passo e la data,
  perche' la card non li mostra piu' ma sono il senso pratico di quel numero
  — e' la misura che decide a che andatura si allena.
- La regola della brevita' **non sparisce, cambia forma**: le quattro misure
  si nominano tutte, ma una misura ferma e dentro la sua fascia si liquida in
  una clausola. Il prompt di oggi la mette cosi' perche' il rischio e' reale
  e scritto: "if you describe them every morning you will write the same
  paragraph for a fortnight". Un mese piatto deve ancora poter uscire in
  quaranta parole.
- Circa 90 parole, ed **esempio riscritto**: quello di oggi non apre con un
  verdetto e non nomina nessuna fascia.

## Vincoli

- Nessuna dipendenza nuova.
- Le fasce di `morning` non devono cambiare di un decimale: `_band` e
  `_window` si riusano, non si toccano.
- `make update_activity` non si chiama a mano: le prove degli agenti vanno
  fatte con `--no-update`.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Il testo si ripete nei mesi piatti.** E' il motivo per cui il prompt di
  oggi dice "quando non si e' mosso niente, dillo e fermati". Le fasce mobili
  danno qualcosa di nuovo da dire anche a valore fermo, ma non e' una
  garanzia: va riletto fra qualche giorno su un periodo senza movimenti.
- **La card perde tre informazioni vere**: quando il VO2max e' stato misurato
  (il 21 ottobre era del 19, non di quella mattina), il livello di Garmin e
  il passo di soglia. Le prime due non si vedranno piu' da nessuna parte; il
  passo resta nel testo per l'eccezione qui sopra.
- **Sopra la fascia e' buono, qui e solo qui.** La stessa barra, nella card
  accanto, vuol dire il contrario. Lo spiega il testo, non la barra.

## Verifica

1. `uv run python -c "from training.interface import daily_data"` e le fasce
   del 2026-10-21: VO2max e hill sopra, endurance dentro, hill che non sfora
   100, e le fasce di `morning` identiche a prima.
2. Un giorno vecchio con meno di 14 valori misurati: `band` nulla, il numero
   resta, nessuna barra, niente si rompe.
3. `make frontend_types` (`schema.ts` cambia una volta e si committa; la
   seconda esecuzione non lo tocca), `npm run typecheck`, `npm run build`.
4. La pagina del 2026-10-21 in Firefox headless: tre barre blu in Fitness, il
   `+1.2 in 28 days` ancora accanto al numero, la soglia col solo numero,
   Health e Recovery invariate nella stessa schermata, nessun errore in
   console. Un controllo anche in tema scuro.
5. `uv run training-daily-report --day 2026-10-21 --section fitness
   --no-update`: il testo apre con un verdetto senza numeri, nomina tutte e
   quattro le misure contro le loro fasce, e non cita ne' il livello
   "Intermediate" ne' la data di misura del VO2max.

## Come e' andata

Fatto come scritto, con un difetto trovato guardando la card a schermo:

- **La fascia aveva i decimali sbagliati.** `_band` arrotondava sempre a un
  decimale, quindi sotto il punteggio di resistenza le tacche dicevano
  "4841.8 - 5010.7": una precisione che quel numero non ha, su un intero a
  quattro cifre. Adesso `_band` prende i decimali della sua misura, e i
  punteggi li hanno a zero (4842 - 5011, 48 - 54). Le fasce di `morning` non
  si muovono: `_morning` non passa il parametro e resta a un decimale.
- `FITNESS_LIMITS` tiene solo `hill_score` a `(0, 100)`. Sui dati di oggi
  non morde (la fascia larga arriva a 57), ma e' la stessa protezione di
  readiness e stress.
- Le barre di Fitness prendono il blu dell'icona (`#2563c8`) con lo stesso
  meccanismo di Recovery: due variabili CSS sulla card, nei due temi.

Il testo fa quello che doveva: apre con un verdetto senza numeri ("The engine
is still growing, and not marginally"), distingue chi e' **sopra** la fascia
(VO2max e hill, ancora in salita) da chi ci e' **dentro** (endurance, "the
rise there has flattened"), e usa l'eccezione della soglia per dare il passo
e la data che la card non mostra piu'. Non nomina ne' "Intermediate" ne' la
data di misura del VO2max.

Resta da vedere, fra qualche settimana, se nei mesi piatti il testo si
ripete: le fasce mobili dovrebbero dargli qualcosa da dire anche a valori
fermi, ma e' una scommessa, non una verifica.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_48'$" --format=%H -1)
```

Effetti fuori dal repo: resta riscritto il frammento
`summary/01.daily/2026-10-21/fitness.md`, che e' il testo nuovo. Il codice
vecchio lo mostra lo stesso, e' solo testo; per riavere quello di prima va
rifatta la sezione con `make daily_report DAY=2026-10-21 SECTION=fitness`.

Dopo il revert, rifare il merge di `todo_48` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
