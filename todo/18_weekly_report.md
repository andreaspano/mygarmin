---
status: todo
---

# Weekly: un report per settimana in `summary/02.weekly/`

Un report scritto per ogni settimana, che racconta all'atleta com'e' andata:
allenamento, recupero, e la tendenza delle ultime quattro settimane. La
pagina Week lo mostra gia' (merge `45a3ae4`): legge
`summary/02.weekly/<lunedi'>.md` per la settimana selezionata e lo mette in
alto a destra, accanto alla tabella. Qui si fa quello che lo scrive.

Il formato e' stato deciso su un report di prova (la settimana del
2026-09-21, oggi in `summary/02.weekly/2026-09-21.md`, riportato in fondo).

## Il formato del report

- **In inglese.**
- **Per un atleta, non per un analista**: si racconta cosa e' successo e cosa
  vuol dire. Pochi numeri: quelli stanno nelle tabelle e nei grafici
  dell'app. Niente gergo ("ACWR", "aerobic-high shortage", "acute load"): si
  dice con parole semplici ("your training load is back in a healthy range",
  "almost no harder efforts").
- **Tre sezioni**, in quest'ordine, con questi titoli esatti:
  - `## 1. Training`: le sedute, come sono distribuite nella settimana,
    l'intensita', il carico rispetto alla settimana prima;
  - `## 2. Recovery`: readiness, FC a riposo, HRV, sonno, stress, cioe' come
    il corpo ha risposto giorno per giorno;
  - `## 3. Trend`: le ultime quattro settimane, cosa sale, cosa scende, cosa
    e' stabile. Le variazioni piccole sono rumore e vanno dette come tali.
- **Niente** piani, niente suggerimenti per la settimana dopo, niente
  riferimenti a `summary/05.plan/`, niente tabelle.
- In testa: `# Weekly report — <lunedi'> to <domenica>` e una riga
  `Week: <lunedi'> to <domenica> · Health data: <n>/7 days`. La pagina Week
  li nasconde (lo dice gia' la riga selezionata), ma restano nel file per
  chi lo legge fuori dall'app.
- Lunghezza: quella del report di prova, due o tre paragrafi brevi per
  sezione.

## Settimana e nome del file

- Lunedi'-domenica. Il file si chiama come il lunedi':
  `summary/02.weekly/2026-09-21.md`. E' il nome che la pagina Week cerca.
- Di default l'ultima settimana **chiusa** (quella prima della settimana di
  oggi). Una settimana a scelta si chiede col suo lunedi'.
- Una settimana non finita si puo' chiedere lo stesso: la riga `Week:` dice
  `(partial, up to <ultimo giorno>)` e il testo lo tiene presente.
- Un report per settimana: rilanciarlo sovrascrive il file.

## Work

Due pezzi: uno script che prepara i fatti, un agente che scrive. I numeri
nel report sono pochi, ma i fatti devono essere giusti, e i conti non li fa il
modello.

### Lo script: `interface/weekly_data.py`

- `build_weekly_data(monday: date, data_dir=DATA_DIR) -> dict` e punto
  d'ingresso `training-weekly-data` (`pyproject.toml`), che stampa il JSON su
  stdout. `--week YYYY-MM-DD` (un lunedi'; una data che non e' un lunedi' e'
  un errore, non viene arrotondata); senza argomento, l'ultima settimana
  chiusa. Target `make weekly_data WEEK=YYYY-MM-DD` (WEEK facoltativo).
- Legge solo dati locali: `db.list_activities()` e
  `health_db.load_health_db()`. Niente chiamate a Garmin, niente scritture.
- Il JSON:
  - `week`: `start`, `end`, `partial`, `last_day`;
  - `activities`: una riga per attivita' (giorno della settimana e data,
    sport, nome, distanza, durata, dislivello, FC media e massima);
  - `days`: una riga per ognuno dei 7 giorni, con le attivita' del giorno
    (o nessuna) e le misure di recupero di quella mattina. Serve all'agente
    per non sbagliare il calendario (vedi sotto);
  - `training`: sedute, tempo, distanza **per sport** (mai sommata fra corsa
    e bici: insieme non vuol dire niente), dislivello, giorni di riposo;
  - `load`: carico acuto e cronico, ACWR e il suo stato, training status,
    bilancio del carico con la frase di Garmin, presi dall'ultimo giorno
    della settimana che li ha (e quale giorno e');
  - `vo2max`: le misure con `vo2max_date` dentro la settimana;
  - `coverage`: **per metrica**, quanti giorni su 7 hanno un valore (vedi
    Rischi);
  - `four_weeks`: per questa settimana e le tre prima, gli stessi totali e
    le medie di recupero, ognuna con il numero di giorni su cui e' fatta.
- Una media su zero giorni e' `null`, mai `0`.

### L'agente: `.claude/agents/weekly-report.md`

Sul modello di `.claude/agents/fitness-status.md`: strumenti Bash, Read,
Write, passi obbligatori.

1. **I dati**: `uv run training-weekly-data [--week YYYY-MM-DD]`. Se
   l'utente nomina una settimana ("last week", "the week of 21 September"),
   la traduce nel lunedi'. Se il comando fallisce, lo dice e si ferma.
2. **Il testo**, nel formato sopra. Prima di salvare controlla:
   - le tre sezioni, con i titoli esatti, in ordine;
   - niente piani, niente "next week", niente tabelle, niente gergo;
   - **ogni frase sul calendario** ("the long run on Friday", "rest days on
     Tuesday and Thursday", "back to back") verificata contro `days`;
   - **le notti**: Garmin mette il sonno di una notte sotto la mattina del
     risveglio. Il sonno con data 2026-09-21 (lunedi') e' la notte fra
     domenica e lunedi': si scrive "the night going into Monday", non
     "Monday night";
   - una metrica con pochi giorni (`coverage`) non si commenta come se fosse
     la settimana intera: si dice che i dati sono pochi.
3. **Il salvataggio**, sempre, in `summary/02.weekly/<lunedi'>.md`. Se il
   file c'e' gia', prima lo legge e poi lo sovrascrive.

- Nella `description`: quando usarlo ("how did my week go", "weekly report",
  "report for the week of ...").
- Nel corpo, il report di prova qui sotto come esempio di tono e lunghezza,
  con la nota che i fatti vengono sempre dal JSON e non dall'esempio.

## Vincoli

- Non toccare la pagina Week ne' `period_page.py`: la visualizzazione c'e'
  gia'.
- Lo script non chiama Garmin. Aggiornare i dati (`make update_activity`)
  resta un passo a parte.
- Niente storico in blocco: i report delle settimane passate si fanno una
  alla volta, a richiesta.
- Non toccare `fitness-status` ne' i report giornalieri.
- Nessuna dipendenza nuova.
- Commenti in italiano senza accenti; report in inglese.

## Rischi

- **Copertura per metrica, non per giorno.** Readiness e carico Garmin li
  calcola anche senza orologio al polso; HRV, sonno, FC a riposo e stress no.
  Nella settimana del 2026-08-31 la readiness c'e' per 7 giorni, ma HRV,
  sonno e FC a riposo per uno solo (l'orologio non c'era dal 09-01 al 09-06).
  Un unico "7/7" li avrebbe fatti sembrare confrontabili. La riga
  `Health data: <n>/7` usa i giorni con il sonno registrato, cioe' quelli con
  l'orologio.
- **Buchi nei dati di salute**: oggi mancano dal 2025-01-01 al 2026-07-31.
  Per quelle settimane la sezione Recovery dice che non ci sono dati, e Trend
  confronta solo quello che c'e'.
- **Il carico di Garmin e' a fine giornata**: si prende l'ultimo giorno della
  settimana che lo ha.

## Verifica

1. `uv run training-weekly-data --week 2026-09-21`: settimana 2026-09-21 ->
   2026-09-27, 5 attivita' (3 corse, 2 uscite in bici), riposo martedi' e
   giovedi', `coverage` 7/7 su tutte le metriche.
2. I totali dello script contro query dirette su `activities.db` per la
   stessa settimana: devono coincidere.
3. `--week 2026-08-31`: `coverage` di sonno, HRV e FC a riposo 1/7, readiness
   7/7.
4. `--week 2026-09-22` (un martedi'): errore chiaro.
5. Una settimana del 2025: nessun dato di salute, medie `null`, nessuna
   eccezione.
6. L'agente sulla settimana del 2026-09-21: tre sezioni con i titoli esatti,
   nessun riferimento a piani o alla settimana dopo, nessuna tabella, fatti
   coerenti con il report di prova. Il file sovrascrive
   `summary/02.weekly/2026-09-21.md`, e la pagina Week lo mostra.

## Il report di prova (2026-09-21)

```markdown
# Weekly report — 2026-09-21 to 2026-09-27

Week: 2026-09-21 to 2026-09-27 · Health data: 7/7 days

## 1. Training

A well-balanced week: three runs and two road rides, with two
rest days placed so that no two demanding days came back to back. Friday's run
was the longest of the week and Sunday's ride the biggest outing, with an easy
run in between. Wednesday's ride was a gentle recovery spin. Everything stayed
comfortable and aerobic: there was no really hard effort anywhere.

After the hilly, demanding week before, this one was lighter, and it brought
your training load back into a healthy range. The one thing missing over the
past month is harder work. Almost all of your training is easy, and Garmin
also notes the shortage of tempo or faster efforts.

## 2. Recovery

You started the week tired. Monday's readiness was very low, the
clear echo of the previous hilly weekend, and the night going into Monday was
the poorest sleep of the week. From there your body bounced back steadily: by
Thursday you were fully fresh, and you stayed in good shape through the
weekend. Resting heart rate went down day by day, ending the week at its
lowest, a good sign that the fatigue had cleared. Heart rate variability was
in your normal range every night.

Sleep was good overall. There were a couple of shorter nights (Tuesday and
Friday), but they didn't knock you back, and a long, restful Saturday night
closed the week well. Day-to-day stress stayed low.

## 3. Trend

The month tells a clear story: a gradual build, one big
hilly week that pushed you hard, and this week to absorb it. Your body handled
the cycle well: you dipped after the big week, but recovered within a few days.
Resting heart rate has stayed steady all month.

Your VO2max has been creeping up a little each week. Each step is small, but
the direction is consistent, and it fits a growing aerobic base. Heart rate
variability is a touch lower than in early September, but it has been stable
for the last three weeks, so it is something to keep an eye on rather than a
concern.

The first week of September is hard to compare: the watch wasn't worn for most
of it.
```
