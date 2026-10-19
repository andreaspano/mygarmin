---
status: todo
---

# La sezione Training come un allenatore che parla al suo atleta

Il paragrafo `## Training` del report giornaliero elenca, non giudica. Quello
del 2026-10-19 dice:

> An interval run in the evening, at 19:46: "Canegrate - Rip_4x5", 7.63 km in
> 52 minutes, average heart rate 134 with a peak of 161, coming after a rest
> day. The work broke down into 32.9 minutes easy, 16.9 minutes of harder
> aerobic running and 2.3 minutes above threshold...

Tutti i numeri sono giusti e non e' detto niente. Deve leggersi come un
allenatore che parla al suo atleta dopo la seduta: cosa e' andato bene, cosa
no, detto in faccia.

Per giudicare servono dei termini di paragone, e due dei tre che ha scelto
Andrea non stanno nel JSON che l'agente legge. Quindi qui si cambiano prima i
dati (`daily_data.py`) e poi una sezione del prompt dell'agente: il prompt da
solo non basta.

## Decisioni

Prese con Andrea il 2026-10-19:

- **Solo la sezione `## Training`** del report giornaliero
  (`.claude/agents/fitness-status.md`): e' il testo che la Day mostra nella
  scheda Training, accanto alla seduta di cui parla. Le altre quattro
  sezioni restano come sono.
- **Tre appigli per la lode e per la critica**: l'intento contro
  l'esecuzione, come la seduta e' stata corsa, e il confronto con le sedute
  simili di prima.
- **Fuori lo stato del corpo contro lo sforzo**: readiness e sonno stanno in
  `## Recovery`, e il giudizio sulla seduta non li ripete.
- **Voce onesta**: lode meritata, critica dovuta, nessuna delle due
  inventata. Una seduta che e' andata e basta non si prende un complimento
  costruito apposta.
- **Circa 120 parole** invece di 80, cosi' i fatti e il giudizio ci stanno
  tutti e due. Nessuna sezione nuova, nessun cambio di impaginazione.

## Work

### 1. I fatti: `src/training/interface/daily_data.py`

`_session()` e' l'unica funzione che cambia forma. La riga di
`list_activities` che riceve porta gia' tutto quello che serve per
l'intento: dal database non si legge niente di nuovo.

- **Intento**: aggiungere `run_type`, `run_type_source` (cosi' si sa se il
  tipo l'ha scelto Andrea o e' una stima), `terrain`, e l'allenamento
  pianificato dall'orologio: `workout_name`, `workout_active_steps`,
  `workout_active_max_s`. Sono tutte colonne gia' presenti sulla riga.
- **Come e' stata corsa**: un blocco `execution` con i numeri, non con le
  frasi: velocita' e battiti della prima e della seconda meta' con la
  differenza in percento, variabilita' della cadenza, battiti in salita
  contro quelli in piano. Sono esattamente i conti che
  `activity_report.activity_comments()` fa gia', dentro alle frasi che
  scrive. **Non si riscrivono**: si tira fuori l'aritmetica in una funzione
  che rende i numeri, e `activity_comments()` ci costruisce sopra le sue
  frasi come prima. I report per attivita' devono continuare a venire
  identici, carattere per carattere.
- **Contro le sedute di prima**: un blocco `compared_with`. Simile vuol dire
  stesso sport, stesso `run_type` quando la seduta ne ha uno, negli ultimi 90
  giorni, escluso il giorno stesso; si prende dal DataFrame `activities` che
  `build_daily_data()` ha gia' in mano, senza altre letture. Si danno
  `count` e la **mediana** di distanza, durata, battiti medi e velocita'
  equivalente. Sotto le 3 sedute simili solo `count` e nessuna mediana: su
  due sedute una mediana non vuol dire niente, e l'allenatore non deve poter
  raccontare un andamento che non c'e'.
- **I record si leggono una volta sola**: oggi `_session()` chiama
  `load_activity_records()` due volte (`daily_data.py:239` e `:255`), e un
  terzo aiutante ne farebbe tre letture delle stesse righe. Si legge una
  volta in `_session()` e si passa il DataFrame a `_effect_minutes()`, a
  `_minutes_above_z3()` e alla funzione nuova.

Ogni valore nuovo segue il contratto del modulo: quello che manca e' `null`,
mai `0`, e passa da `_value()`. Le sedute senza GPS, senza cadenza o senza
battiti devono dare `null`, non errori.

### 2. La voce: `.claude/agents/fitness-status.md`

Si riscrive il punto `## Training` dello "Step 2 — write the report". Resta
quello che la sezione racconta (le sedute del giorno, una per volta; se non
ce n'e' lo si dice, con quanti giorni sono passati dall'ultima) e si
aggiunge:

- **Chi parla**: un allenatore che parla al suo atleta dopo la seduta.
  Diretto, seconda persona, niente registro da analista.
- **Un giudizio, appoggiato ai fatti**: dire cosa e' andato bene e cosa no, e
  legare ogni giudizio a un dato del JSON. Il tipo della seduta contro quello
  che i numeri dicono sia stata davvero (`run_type` contro `effect_minutes` e
  `minutes_above_z3`; l'allenamento pianificato contro il lavoro fatto), come
  e' stata corsa (`execution`), e dove sta rispetto a `compared_with`.
- **Niente lodi inventate e niente colpe inventate.** Se la seduta ha fatto
  quello che doveva, lo si dice e si chiude li'. Se `compared_with.count` e'
  sotto il minimo, nessun confronto.
- **Non si pesta il terreno di Recovery**: readiness, sonno e battito a
  riposo non sono l'argomento qui, nemmeno come scusa.
- **Circa 120 parole**, un paragrafo solo, sempre sotto `## Training`, e
  nessun numero che non sia nel JSON.
- Sotto la sezione, un esempio di tono e lunghezza come fa gia' l'agente del
  settimanale ("Example (tone and length only...)"), scritto su un giorno
  vero, cosi' l'esempio non puo' allontanarsi dalla forma vera dei dati.

## Vincoli

- Nessuna dipendenza nuova.
- Fuori dal paragrafo Training e dai campi nuovi del JSON non cambia niente.
- `activity_report.py` continua a scrivere lo stesso testo di prima.
- `sessions` e' `dict[str, Any]` in `api/models.py`: i campi nuovi non
  toccano i modelli, e `make frontend_types` deve lasciare
  `frontend/src/api/schema.ts` invariato.
- Commenti in italiano senza accenti, testo del report in inglese.
- Non si toccano gli altri file di `todo/`, ne' il loro `status`.
- Non si scrive nell'albero dei dati.

## Rischi

- **Un allenatore che deve per forza dire qualcosa.** La voce onesta deve
  poter dare un verdetto piatto: l'esempio nell'agente ne mostri uno.
- **Confronti su pochi numeri.** Poche sedute simili rendono la mediana una
  coincidenza: il minimo di 3 serve a questo, e l'agente lo deve rispettare.
- **Sport senza tipo.** Le uscite in bici e le camminate non hanno
  `run_type`: li' l'intento lo danno la durata, il terreno e la divisione
  degli effetti.
- **Riscrivere un report costa poco, richiamare Garmin no.** La verifica
  lavora su giorni passati e sui soli dati locali.

## Verifica

1. `uv run python -c "import training"` e `uv run python -c "from
   training.interface import daily_data, activity_report"`.
2. `make daily_data DAY=2026-10-19` (corsa con allenamento pianificato),
   `make daily_data DAY=2026-10-17` (uscita lunga in bici, senza tipo) e un
   giorno senza seduta: JSON valido, i blocchi nuovi al loro posto, `null`
   dove il dato non c'e'.
3. **I report per attivita' non si muovono**: rigenerare in una cartella
   temporanea il report di un'attivita' che ne ha gia' uno in
   `summary/00.activity/` e confrontare i due file. Identici, o il refactor
   e' sbagliato.
4. `make frontend_types` lascia `frontend/src/api/schema.ts` invariato.
5. La voce, da capo a fondo: far scrivere all'agente il report di un giorno
   passato, con i soli dati locali, e rileggerlo. Deve leggersi come un
   allenatore, ogni numero deve stare nel JSON, e una seduta che non merita
   lodi non ne deve ricevere.
6. Mai `make update_activity`, `make backfill_health`, `make backfill` ne'
   `make backfill_activity_names`.
