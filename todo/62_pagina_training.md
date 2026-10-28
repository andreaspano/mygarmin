---
status: done
---

# Training: la seduta esce dal Report e prende una casella sua

Sotto Day la seconda riga del menu ha due voci, Report e Trend (todo 55 e 59).
Il Report e' lungo: Next e Summary in cima, la griglia 2x2 delle quattro card,
e **in fondo a tutto la card Training** — la seduta del giorno col selettore
delle attivita', il grafico, la mappa, il terreno, il tipo di corsa, il testo
della sezione e il suo tasto.

E' la parte piu' ricca della pagina, e per arrivarci si scorre tutto il resto.
Qui prende una casella sua: **Report | Training | Trend**.

## La card si sposta, non si copia

La pagina nuova mostra **esattamente** quello che la card mostra adesso, e la
card esce dal Report. Lo stesso contenuto in due viste vorrebbe dire due posti
da tenere allineati, e due risposte alla stessa domanda: dov'e' la seduta di
oggi.

Si riusa `<TrainingCard>` com'e'. Non una seconda disposizione a tutta pagina,
senza cornice: la card ha gia' dentro la sua struttura — `CardHead` con
l'icona della sezione e il tasto che la rifa', il selettore delle attivita'
quando il giorno ne ha piu' d'una, lo stato di riposo quando non ne ha
nessuna. Rifarla distesa sarebbe riscriverla, e «esattamente quello che
contiene» e' letterale.

Il Report resta con Next, Summary, le quattro card e la nota sui dati.

## Dove va, nella barra

Fra Report e Trend, che l'ordine del menu e' quello dell'array `VIEWS.day` in
`navigation.ts`. Non prima del Report: la **prima della lista e' la vista di
partenza** (todo 59), quella che `hrefFor` non scrive nell'URL, e il Report
deve restare quello che si apre senza chiedere niente.

La Week il Training non ce l'ha. Non e' una dimenticanza da riempire piu'
avanti: una settimana non ha una seduta, ne ha sette, e quelle lo Snap le
mostra gia'. Quindi da Day/Training si clicca Week e si arriva su Week/Snap —
`vistaSu` in `TopBar` gia' porta la vista solo dove quel periodo ce l'ha.

## Work

- `navigation.ts`: `"training"` nell'unione `View` e in mezzo a
  `VIEWS.day = ["report", "training", "trend"]`.
- `navigation.ts`: la mappa delle etichette si sposta qui da `TopBar.tsx`,
  esportata. Sta accanto a `View` e `VIEWS` di cui e' il vocabolario, e serve
  in due posti — la riga del menu e il titolo della pagina. Essendo un
  `Record<View, string>` il compilatore obbliga a riempirla: la voce nuova non
  si puo' dimenticare.
- `DayPage.tsx`: il cancello dei dati diventa `if (view === "trend") return;`.
  Era `view !== "report"`, e avrebbe lasciato la card senza `data` e senza
  `report`, cioe' senza seduta e senza testo. Solo il Trend ne fa a meno, che
  ha i suoi pannelli.
- `DayPage.tsx`: il titolo prende l'etichetta della vista invece di nominare
  il Trend a mano.
- `DayPage.tsx`: il ternario a due rami diventa tre guardie indipendenti, come
  fa gia' la Week che di viste ne ha tre. La `<TrainingCard>` si sposta nella
  sua, con le stesse props che ha adesso.

## Vincoli

- Nessuna dipendenza nuova, nessuna regola CSS nuova: `.training-card` non ne
  ha di proprie, vale `.card`, e la card e' gia' a tutta larghezza.
- **L'API non si tocca**: nessun modello cambia, quindi niente
  `make frontend_types`. La vista nuova chiama quello che la Day gia' chiama.
- `dataNote` resta nel Report: e' `preamble(report)`, la sezione senza titolo
  del report, la nota sui dati del giorno. Stava sotto la card per posizione,
  non perche' fosse della card.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Il cancello dei dati e' il punto che si rompe in silenzio.** Lasciandolo
  com'e' la pagina non da' errore: la card si disegna con `data` e `report`
  nulli, cioe' mostra lo stato «giorno di riposo» anche quando la seduta c'e'.
  Va provato su un giorno con seduta, non su uno qualunque.
- **Il titolo della pagina diventa ripetuto**: `Training · <giorno> ·
  Training`, perche' «Training» e' sia il nome dell'app sia quello della
  vista. Una fonte sola per le etichette vale la ripetizione; se da' fastidio
  si cambia il prefisso in un posto solo.

## Verifica

1. Sotto Day la seconda riga e' `Report | Training | Trend`, in quest'ordine.
   Cliccando Training l'URL diventa `?view=training` e la voce ha
   `aria-current="page"`.
2. Su un giorno con seduta la pagina mostra la card identica a quella che il
   Report aveva: selettore, grafico, mappa, terreno, tipo di corsa, testo
   della sezione con l'ora e il tasto. Su un giorno di riposo, lo stato di
   riposo.
3. Il Report non ha piu' la card in fondo: restano Next, Summary, le quattro
   card e la nota sui dati.
4. Cambiando vista il giorno resta, e il tasto indietro torna alla vista di
   prima sullo stesso giorno.
5. Da Day/Training si clicca Week e si arriva su Week/Snap; da Day/Trend si va
   ancora su Week/Trend.
6. I link vecchi valgono: `?` nudo apre Day/Report, `?page=week` apre
   Week/Snap, `?day=2026-10-07` apre quel giorno nel Report, e
   `?period=week&view=training` ricade sullo Snap invece di una pagina muta.
7. Il tasto della sezione dalla pagina nuova fa partire la POST su
   `/api/reports/daily/<giorno>/refresh/training` e passa in stato «in corso».
8. `npm run typecheck` e `npm run build`, e la pagina nei due temi.

## Come e' andata

Fatto come scritto. Tre note.

**Le etichette si sono spostate per davvero.** `ETICHETTE` stava in
`TopBar.tsx`, ma il titolo della pagina nominava il Trend a mano
(`view === "trend" ? ... : ...`), e con tre viste sarebbe diventato un
ternario annidato con i nomi scritti due volte. Adesso sta in
`navigation.ts`, accanto a `View` e `VIEWS`, e serve tutti e due.
Conseguenza voluta del `Record<View, string>`: aggiungendo la vista senza
l'etichetta il typecheck si ferma.

**Il titolo e' ripetuto, come previsto**: `Training · 2026-10-27 · Training`.
Si cambia il prefisso in un posto solo, se stufa.

**Il frammento di troppo e' sparito.** Dentro `{data ? (...)}` c'era un
`<>…</>` attorno alla sola `cards-grid`, rimasto da quando ci stava altro.

### Un inciampo che non e' un difetto

Aprendo `?day=...&view=training` da URL, per un momento la card dice **"Rest
day"** anche su un giorno con la seduta: le attivita' arrivano da
`api.activities` (la striscia della settimana), che e' asincrona, e con
`activities` vuoto la card mostra il riposo. Poi arriva la lista e si
sistema. Non e' nuovo e non viene da qui — succedeva identico nel Report, solo
che li' la card stava in fondo e nessuno la guardava mentre caricava. Se un
giorno desse fastidio, la via d'uscita e' distinguere "nessuna attivita'" da
"non ancora chieste", che oggi sono lo stesso stato.

Per questo la verifica nel browser **non va fatta aspettando
`.training-card`**: esiste subito. Si aspetta che `.rest-day` sparisca.

### Come e' stato verificato

Firefox headless, geckodriver 0.37.1 pilotato in **WebDriver classico via
`urllib`** — niente Selenium, sono quaranta righe. Sette prove su
`http://127.0.0.1:5173`: le tre viste da URL, il clic sulla voce dal Report,
il tasto indietro, `?period=week&view=training` e `?page=week`.

Esito: menu `Report | Training | Trend` nell'ordine giusto con
`aria-current` sulla voce aperta; sulla pagina nuova la card col titolo
`Legnano RunningEasy`, il testo della sezione, `written at 22:01`, il
grafico, i selettori Run type (`easy`) e Terrain (`road`), il tasto *Rewrite
the training section* e *Open the route map*; nel Report zero
`.training-card` e le quattro card al loro posto; il giorno resta cambiando
vista e l'indietro torna al Report sullo stesso giorno;
`?period=week&view=training` ricade sullo Snap. Il 26 ottobre, giorno di
riposo vero, mostra il riposo.

**Il punto 7 della verifica e' rimasto a meta' di proposito**: del tasto
della sezione si e' controllato che ci sia e con che props, non lo si e'
premuto. Premerlo chiama Garmin (`make update_activity`) e riscrive
`summary/01.daily/2026-10-27/training.md` con un agente: due minuti e un
file cambiato, per provare un bottone che e' lo stesso oggetto di prima
spostato di posto.

Due cose imparate sull'attrezzatura, per chi verifica domani:

- **il `--profile-root` dell'allowlist non va bene**:
  `~/snap/firefox/tmp/gecko-profiles` lo snap non lo vede scrivibile e
  geckodriver muore con *Unable to write to temporary directory*. Funziona
  `~/snap/firefox/common/gecko-profiles`.
- **il tema scuro si falsifica**, al contrario di quanto dice il todo 55:
  non da BiDi ma con la preferenza `ui.systemUsesDarkTheme` nelle
  `moz:firefoxOptions.prefs`. Provati tutti e due: card
  `rgb(255,255,255)` su pagina `rgb(244,244,246)` nel chiaro,
  `rgb(23,26,34)` su `rgb(14,17,23)` nello scuro.

`npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_62'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Solo frontend, nessuna chiamata a Garmin,
nessuna scrittura in `summary/`, nessun cambio all'API.
