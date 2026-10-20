---
status: done
---

# Un agente per card, piu' due che danno il verdetto

Oggi un agente solo, `fitness-status`, scrive tutte e cinque le sezioni del
report giornaliero in `summary/01.daily/<giorno>.md`, e l'API spacca quel
file per le card. Il suo prompt e' a 276 righe, di cui circa 150 sono le
specifiche delle sezioni: il 2026-10-20 lo abbiamo toccato cinque volte, e
una volta l'esempio scritto per la sezione Health ha fatto sconfinare il
testo proprio dove la regola lo vietava.

Dividerlo non e' solo ordine. Le regole di proprieta' che oggi scriviamo come
divieti ("il sonno e' di Recovery", "non citare numeri che la tua card non
mostra") diventano **vere per costruzione**, perche' ogni agente vede solo la
sua fetta di JSON. E i due agenti di verdetto hanno bisogno dei *giudizi*
degli altri, non dei numeri: e' gia' quello che Next fa di fatto.

## Decisioni

Prese con Andrea il 2026-10-20:

- **Sette agenti.** Per le card: `01_health`, `02_load`, `03_recovery`,
  `04_fitness`, `05_training`. Per i verdetti: `06_next` e `07_summary`.
  Andrea li aveva chiamati `01_next` e `02_summary`; rinominati subito dopo il
  merge, perche' con due serie che ripartono da uno i nomi si mescolavano in
  ordine alfabetico in `.claude/agents/` e l'ordine di lancio non si leggeva
  piu' dall'elenco.
- **La card Fitness avra' un testo**, sul modello di Health. Cambia la scelta
  del todo 38 ("il report non ha una sezione Fitness"), e il report passa da
  cinque a sei sezioni piu' il Summary.
- **`07_summary` e' il verdetto del giorno**: legge i giudizi di tutte le
  sezioni e dice come sta la giornata, nel box accanto a Next. La frase di
  apertura di Health resta dov'e', come verdetto della sola salute.
- **Refresh per card**: il tasto generale rifa' tutto, e ogni card ha il suo
  tasto che rilancia solo il suo agente.
- **Si costruisce tutta la macchina**, non un assaggio.
- **In fila, non in parallelo** (deciso la sera del 2026-10-20, con Andrea
  via): gli agenti girano uno dopo l'altro. A parita' di lavoro i gettoni
  sono gli stessi, ma in fila un giro che va storto si ferma al primo
  errore invece di bruciare cinque sessioni insieme, e non si rischiano i
  limiti di frequenza con i loro tentativi ripetuti. Il refresh completo
  dura di piu' (sette giri da circa un minuto), e non importa a nessuno:
  lo lancia il tasto in background.

## Work

### La forma, in due fasi

`make daily_data` una volta sola produce il JSON del giorno. Poi i cinque
agenti di card girano **in fila**, ognuno sulla sua fetta, e scrivono il loro
frammento. Alla fine girano `06_next` e `07_summary`, che leggono i frammenti
e non i numeri: quei due devono comunque venire dopo gli altri cinque, quindi
l'ordine e' health, load, recovery, fitness, training, next, summary.

### 1. Dove scrivono: una cartella per giorno

`summary/01.daily/<giorno>/` con dentro `health.md`, `load.md`,
`recovery.md`, `fitness.md`, `training.md`, `next.md`, `summary.md`. Ogni
file e' il **corpo** della sezione, senza il titolo `##`: il titolo lo mette
chi compone.

Sette agenti sullo stesso file si cancellerebbero a vicenda; cosi' non si
toccano mai. Il vecchio `<giorno>.md` resta valido e non si tocca: i giorni
gia' scritti devono continuare a vedersi.

### 2. L'API: `src/training/api/app.py`, `interface/report_text.py`

- `get_daily_report` compone le sezioni in quest'ordine fisso: `Summary`,
  `Training`, `Recovery`, `Health`, `Load`, `Fitness`, `Next`, leggendo i
  frammenti della cartella del giorno e saltando quelli che non ci sono. Se
  la cartella non esiste, ricade su `parse_report(<giorno>.md)` come fa oggi.
  Il modello `Report` non cambia: la pagina non cambia contratto.
- `REPORT_SECTION_ICONS` guadagna `"fitness": "fitness.png"`. L'icona esiste
  gia' in `icons/`, oggi cablata dentro `FitnessCard`.
- Endpoint nuovo: `POST /api/reports/daily/{day}/refresh/{section}` con
  `section` fra i sette nomi (422 per un nome che non esiste). Quello senza
  sezione resta e vuol dire "tutte".

### 3. L'orchestratore: `src/training/api/refresh.py`

Oggi lancia un agente col nome cablato e tiene uno stato solo. Diventa:

- I fatti del giorno **una volta sola**, su un file temporaneo che gli agenti
  leggono: sette letture per conto proprio vorrebbero dire sette
  sincronizzazioni di `activities.db` e della salute.
  **Non** il JSON di `make daily_data`: quello non ha il blocco `fitness`,
  che l'API aggiunge sopra in `get_daily` (todo 37 e 38), e l'agente di
  Fitness scriverebbe che i punteggi non ci sono mentre la card accanto li
  mostra. I fatti sono quelli che riceve la pagina: la parte comune va in
  `api/daily.py::daily_payload`, che usano sia l'endpoint sia
  l'orchestratore. Dopo lo scaricamento la cache si invalida subito, se no i
  fatti sono quelli di prima.
- I sette agenti **in fila**, in un thread solo come il lavoro di oggi:
  health, load, recovery, fitness, training, poi next e summary. Un errore
  ferma il giro li' dove e' successo invece di sprecare le sessioni rimaste.
- **Stato per sezione**: `_state` diventa una mappa
  `{sezione: {status, started, finished, message}}` piu' lo stato
  complessivo (`running` finche' almeno un agente gira). `RefreshStatus` nei
  modelli guadagna il dettaglio per sezione, e `make frontend_types`
  rigenera `frontend/src/api/schema.ts`.
- **Fallimento parziale**: la sezione che fallisce **tiene il frammento di
  prima** e lo stato dice quale ha fallito; le altre vanno avanti. Un report
  con un buco e' peggio di un report con una sezione di ieri, purche' si
  veda quale.
- `ALLOWED_TOOLS` per agente: `Read` (il JSON e i frammenti) e
  `Write(summary/01.daily/**)`. Ai sette non serve
  `Bash(make update_activity)`: l'aggiornamento dei dati lo fa
  l'orchestratore prima, una volta sola, come fa oggi l'agente al passo 1.

### 4. Gli agenti: `.claude/agents/`

Ognuno prende dal prompt di oggi la **sua** sezione, gia' scritta e tarata, e
niente altro: la voce, le regole, gli esempi si spostano pari pari.
`fitness-status` resta dov'e' per l'uso da terminale finche' la macchina non
e' in piedi; poi il suo compito di scrivere il file intero sparisce, e il
file dice che il lavoro e' passato ai sette.

- **Le cinque card** ricevono nel prompt il percorso del JSON e la fetta che
  gli spetta: `morning` per `01_health` e `03_recovery`, `load` per
  `02_load`, `fitness` per `04_fitness`, `sessions` (piu' `hr_zones` e
  `recent`) per `05_training`.
- **`04_fitness` e' nuovo**, sul modello di Health: verdetto in apertura, poi
  VO2max, endurance, hill score e soglia. Questi numeri si muovono in
  settimane, non in giorni: se parla ogni giorno dira' la stessa cosa per una
  settimana. Il prompt punta sul **cambiamento** (le variazioni a 28 giorni
  sono gia' nel JSON) e deve poter essere molto corto quando non si e' mosso
  niente.
- **`06_next`** legge i cinque frammenti piu' `hr_zones` (gli servono i bpm) e
  scrive la seduta consigliata, con il formato a tre parti di oggi (titolo in
  grassetto, il perche', i passi come elenco).
- **`07_summary`** legge i cinque frammenti e scrive il verdetto del giorno:
  nessun numero, e **puo' dire che i giudizi non concordano**, che e' proprio
  il caso in cui cinque agenti ciechi l'uno all'altro sbagliano.
- **Stile condiviso**: le regole comuni (inglese, niente gergo, i numeri
  vengono dal JSON, non si inventa niente) stanno in un `_style.md` solo,
  invece che copiate sette volte. Primo passo: provare se
  `--append-system-prompt-file` arriva a un agente lanciato con `--agent`; se
  non arriva, ogni prompt dice di leggere `_style.md` e l'orchestratore
  concede il `Read`.

### 5. La pagina: `frontend/src/components/`

- `FitnessCard` prende `text` e `icon` come le altre card e perde la costante
  `FITNESS_ICON` cablata.
- `SummaryCard` mostra la sezione `Summary` (oggi gli si passa `null`).
- Un tasto piccolo per card che chiama il refresh della sua sezione, con
  l'icona che gira mentre il suo agente lavora: lo stato per sezione arriva
  gia' da `GET /api/refresh`.

## Vincoli

- Nessuna dipendenza nuova.
- I report gia' scritti (`summary/01.daily/<giorno>.md`) continuano a
  vedersi: la ricaduta nell'API non e' facoltativa.
- Commenti in italiano senza accenti, testo dei report in inglese.
- Non si tocca `frontend/src/api/schema.ts` a mano: lo genera
  `make frontend_types`.
- Non si toccano gli altri file di `todo/`.
- Mai `make update_activity`, `make backfill_health`, `make backfill` ne'
  `make backfill_activity_names` a mano nella verifica.

## Rischi

- **Costo**: sette sessioni invece di una a ogni refresh completo. Il tasto
  per card serve proprio a non pagare il conto pieno per un ritocco.
- **Sezioni che si contraddicono**: Recovery "ben recuperato" e Health
  "affaticato" nello stesso giorno. Lo scudo e' la proprieta' stretta dei
  dati piu' `07_summary`, che deve poterlo dire invece di nasconderlo.
- **Tempo**: sette agenti in fila sono circa sette minuti, contro i 60
  secondi di oggi. E' il prezzo della scelta di non parallelizzare, e lo
  paga un lavoro in background che nessuno guarda.
- **Lo stato in memoria** si perde al riavvio dell'API, come oggi: con sette
  lavori la finestra in cui si perde qualcosa e' piu' larga.
- **Il `claude` vero**: i permessi si provano solo lanciandolo davvero. Un
  permesso che manca viene negato, non chiesto.

## Verifica

1. `uv run python -c "import training"` piu' un import di ogni modulo
   toccato.
2. `make daily_data DAY=2026-10-19` invariato: l'orchestratore usa lo stesso
   JSON, non un altro.
3. Un refresh completo su un giorno passato: i sette frammenti scritti nella
   cartella del giorno, e `GET /api/reports/daily/{day}` che rende le sezioni
   nell'ordine `Summary, Training, Recovery, Health, Load, Fitness, Next`.
4. **La ricaduta**: un giorno che ha solo il vecchio `<giorno>.md` si legge
   ancora, con le sue sezioni.
5. Un refresh di una sola sezione: cambia solo quel frammento, gli altri
   restano con il loro `mtime`.
6. Un fallimento finto (un `claude` tolto dal `PATH`, o un agente che non
   scrive): le sezioni gia' scritte restano, lo stato dice quale ha fallito,
   il frammento vecchio resta al suo posto.
   **Tutta la verifica dell'impianto si fa con un `claude` finto**, come il
   todo 41: uno script in testa al `PATH` che scrive il frammento ed esce 0,
   e uno che esce 1. Costa zero gettoni e prova orchestratore, stato,
   endpoint, ricaduta e fallimento parziale. Solo alla fine un giro vero,
   per guardare il testo.
7. `make frontend_types`, poi `cd frontend && npm run typecheck` e
   `npm run build`: nessun errore.
8. La pagina in Firefox headless (`--remote-debugging-port`, WebDriver BiDi:
   su questa macchina Chromium e' solo lo stub dello snap): la card Fitness
   col suo testo, il box Summary pieno, i tasti per card che girano mentre il
   loro agente lavora, nessun errore in console.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_44'$" --format=%H -1)
```

Effetti fuori dal repo:

- **I frammenti gia' scritti restano.** La cartella
  `summary/01.daily/2026-10-20/` con i sette file ci rimane, e dopo il revert
  nessuno la legge piu': l'API torna al file unico `2026-10-20.md`, che e'
  ancora al suo posto (scritto dall'agente di prima alle 18:16), quindi la
  pagina del giorno continua a mostrare un report, quello vecchio. Le
  cartelle dei giorni si possono cancellare a mano quando danno fastidio.
- **I dati scaricati** dal `make update_activity` del giro di prova restano,
  come dopo un Refresh qualunque.
- **Gli agenti in `.claude/agents/`** tornano indietro col revert, compreso
  `fitness-status`, che ridiventa quello che scrive il report intero.

Dopo il revert, rifare il merge di `todo_44` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
