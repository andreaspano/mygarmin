---
status: todo
---

# Recovery ridisegnata sulla logica di Health

La card Health e' stata rifatta fra il 19 e il 20 ottobre e adesso funziona:
quattro misure, ognuna con la sua **barra** (la media dei 28 giorni prima
piu' e meno uno scarto tipo, e in tinta piu' chiara piu' e meno due),
nessun testo sotto i numeri, e sotto un commento da allenatore che apre con
un verdetto e poi giudica **quelle quattro misure e nient'altro**.

Recovery e' rimasta alla forma vecchia: tre numeri con una riga di testo
sotto ognuno — "7-day avg 60.7 · 28-day avg 65.5", "Score 81 · 2 of 7 nights
under 7 h", "Yesterday's low 9". Sono le stesse medie che la barra
mostrerebbe da sola, scritte a parole. E il testo sconfina: il report del 20
ottobre chiude con "Three rest days in the last seven; yesterday was the hard
one", due numeri che la card Load accanto gia' mostra.

Il lavoro e' quasi tutto di forma, perche' **i dati ci sono gia'**: ogni
misura di `morning` porta la sua `band`. Sul 20 ottobre: readiness 50.1-80.9,
ore di sonno 6.5-8.7, body battery al risveglio 61.5-99.7, minimo di ieri
12.4-31.3. Il modello dell'API non si tocca.

## Decisioni

Prese con Andrea il 2026-10-20:

- **Quattro misure, come Health, nella griglia 2×2**: Readiness, Sleep (ore),
  Body battery al risveglio, Body battery minimo di ieri. Lo **sleep score**
  e il conteggio delle notti corte **spariscono dalla card**: restano nei
  dati, e nessuno li cita piu'.
- **Testo stretto come Health**: solo le misure della sua card, nessun numero
  che la card non mostra. Giorni di riposo e ultima seduta dura restano a
  Load, che li ha gia' a schermo.

## Work

### 1. La card — `frontend/src/components/RecoveryCard.tsx`

Diventa il gemello di `HealthCard.tsx`: `<div className="stats two">` con
quattro `Stat`, ognuno con `sub={<MeasureBar measure={...} />}` e niente
altro sotto il numero.

| riquadro | valore | fascia |
|---|---|---|
| Readiness | `morning.readiness.value` | `morning.readiness.band` |
| Sleep | `sleep_minutes`, scritto "7h25" | `morning.sleep_hours.band` (ore) |
| Body battery, wake-up | `morning.body_battery_morning.value` | la sua |
| Body battery, yesterday's low | `morning.body_battery_low_yesterday.value` | la sua |

Spariscono `avgs()` e la riga delle notti corte; `sleepValue()` resta per il
numero grande.

### 2. Le barre diventano di tutti — `frontend/src/components/Stat.tsx`

`RangeBar` e `MeasureBar` oggi stanno dentro `HealthCard.tsx`. Si spostano in
`Stat.tsx`, accanto a `Stat`, `num` e `CardHead`, che e' gia' il modulo dei
numeri condivisi fra Recovery, Health e Fitness; le due card le importano da
li'. Nessuna copia.

### 3. Il sonno: valore in h:mm, fascia in ore

La fascia di `sleep_hours` e' in ore (6.5 - 8.7) e il numero grande e' "7h25":
le tacche leggerebbero "6.5" e "8.7" sotto un valore in ore e minuti.
`RangeBar` prende quindi una funzione opzionale per scrivere le tacche (di
default il numero com'e'), e il riquadro Sleep le passa `durationLabel(ore *
60)` (`frontend/src/format.ts`, da' "6h30"). Il marcatore sta su
`sleep_minutes / 60`, cosi' valore e fascia sono nella stessa unita'.

### 4. Le fasce che sforano il possibile — `src/training/interface/daily_data.py`

La fascia del body battery al risveglio arriva a `outer_high` 118.7, che non
esiste: la batteria si ferma a 100. La barra ci costruisce sopra una scala
che va oltre il massimo e schiaccia il valore a sinistra. `_band()` prende
dei limiti opzionali, e le misure che vivono fra 0 e 100 (readiness, sleep
score, stress, body battery e il suo minimo, SpO2) li dichiarano accanto a
`MORNING_METRICS`. Sulle altre misure non cambia niente, e sulla card Health
di oggi nemmeno: stress e sleep score stanno gia' dentro.

### 5. Il prompt — `.claude/agents/03_recovery.md`

Riscritto sullo stampo di `01_health.md`, che e' gia' tarato:

- **Apre con il verdetto**, una frase corta che prende posizione e **senza
  numeri** ("good enough to work, not to race"). Quella frase e' il
  riassunto: niente seconda frase di chiusura alla fine.
- Poi **le quattro misure della card**, una o due clausole ognuna, giudicate
  contro la **propria fascia**. Le regole delle fasce stanno gia' in
  `_style.md`, direzione cattiva compresa: sotto la fascia e' male per
  readiness, sonno e body battery.
- **Mai un numero che la card non mostra**: via lo sleep score, via le notti
  corte, via i giorni di riposo e l'ultima seduta dura.
- Il minimo di ieri va letto per quello che e': sotto la fascia vuol dire che
  **ieri ha chiesto molto**, non che il recupero e' andato male. Quello che
  conta e' se la mattina e' risalita.
- L'allarme `short_sleep` resta suo, ma detto da allenatore e **senza il
  conteggio**, che la card non mostra piu' ("you are coming off a run of
  short nights").
- Circa 80 parole, un paragrafo. **L'esempio va riscritto**: quello di oggi
  cita le notti corte e i giorni di riposo, e un esempio che fa quello che la
  regola vieta e' gia' costato un report sbagliato una volta.

## Vincoli

- Il modello dell'API non cambia: `make frontend_types` deve lasciare
  `frontend/src/api/schema.ts` identico.
- Nessuna dipendenza nuova.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **La card perde due numeri** (sleep score, notti corte). La fascia del
  sonno dice se la notte e' stata corta *per le sue abitudini*, che e' quello
  che serve, ma il punteggio di Garmin non si vede piu' da nessuna parte.
- **Due barre del body battery vicine** raccontano cose diverse: una il
  recupero, l'altra la fatica di ieri. Se il testo non lo spiega si leggono
  come due misure della stessa cosa.
- Il testo si accorcia e in certi giorni dira' poco. E' il punto: Health fa
  cosi' e funziona.

## Verifica

1. `uv run python -c "from training.interface import daily_data"`, e le
   fasce di un giorno: nessuna oltre 100 per le misure limitate, le altre
   identiche a prima.
2. `make frontend_types` lascia `schema.ts` invariato, poi `npm run
   typecheck` e `npm run build`.
3. La pagina del 2026-10-20 in Firefox headless: quattro barre nella card
   Recovery, le tacche del sonno in "6h30"/"8h42", il marcatore del minimo di
   ieri fuori dalla fascia a sinistra, nessun errore in console.
4. La card Health nella stessa schermata non cambia di niente: lo
   spostamento di `RangeBar` non si deve vedere.
5. `uv run training-daily-report --day 2026-10-20 --section recovery
   --no-update`: il testo apre con un verdetto senza numeri, parla delle
   quattro misure e **non** nomina sleep score, notti corte, giorni di riposo
   ne' l'ultima seduta dura.
6. Un giorno vecchio con poche misure (fascia `null`): il numero resta, la
   barra non c'e', niente si rompe.
