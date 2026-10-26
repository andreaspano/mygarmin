---
status: done
---

# Il Trend della Day: ventotto giorni di grafici

La barra in alto ha una riga sola, e mescola due assi: Day e Week sono
periodi, Activities e' un archivio. Questo todo spezza il menu in due righe
e riempie la casella nuova che si apre sotto Day.

**Prima riga**: il periodo — Day, Week. **Seconda riga**: cosa guardi di
quel periodo — Report, Trend.

Il Report e' quello di oggi, non si tocca. Il Trend e' nuovo: i grafici
delle misure giornaliere nei **28 giorni** che finiscono nel giorno scelto.

## Perche' 28 giorni, e perche' sotto Day

Non e' una finestra nuova. `BASELINE_LONG = 28` in `daily_data.py:94` e'
gia' la finestra con cui ogni card della Day si confronta: le barre delle
misure, il `days_ago_28` e il `change` che si leggono adesso a parole sono
calcolati li' sopra. **Il Trend disegna quello che il Report racconta.**

E "Day" qui vuol dire **granularita' giornaliera**, non "un giorno solo":
un punto per giorno. Quando ci sara' il Trend della Week sara' un punto per
settimana, e la griglia restera' coerente.

I dati reggono. Nei 28 giorni fino al 25 ottobre `health_daily` e' pieno:
28 giorni misurati su 28 per readiness, HRV, battito a riposo, punteggio del
sonno, VO2max, carico acuto ed endurance score. Niente buchi da inventare.

## Cosa si disegna

**Cinque pannelli, nell'ordine delle card della Day**, cosi' Report e Trend
sono due forme della stessa struttura e non c'e' una tassonomia nuova da
imparare:

| pannello | serie |
|---|---|
| Health | battito a riposo, HRV della notte, respiro nel sonno, stress medio |
| Recovery | readiness, ore di sonno, punteggio del sonno, body battery alta e bassa |
| Load | carico acuto, carico cronico, ACWR, i tre carichi per intensita' |
| Fitness | VO2max, endurance score, hill score |
| Training | minuti per intensita' e distanza delle sedute |

## La finestra: due estremi e un cursore

L'intervallo e' **due parametri**, non uno: `from` e `to`. Il nome non e'
nuovo — i report si riscrivono gia' cosi' (`make backfill_reports FROM=...
TO=...`, todo 50), e il Trend usa lo stesso vocabolario invece di
inventarne un altro.

Di partenza: **`to` e' oggi, `from` e' oggi meno 28**. Il cursore muove
l'ampiezza, **da 5 a 365 giorni**, e ricalcola `from` tenendo fermo `to`.

Una finestra sola per tutti e cinque i pannelli: due scale temporali nella
stessa schermata si leggono male.

Il cursore risolve da solo la tensione su Fitness, che si muove lento: il
VO2max fa tre o quattro gradini in ventotto giorni (41.5 il 15/10, 41.9 il
19, 42.2 il 22) e dice poco, ma a 180 giorni si vede la salita intera.
Invece di decidere noi una finestra per misura, si tira il cursore.

**`to` non e' per forza oggi.** Sono due parametri proprio perche' si possa
anche spostare la finestra indietro e guardare un mese di settembre senza
trascinarsi dietro ottobre. Il cursore cambia l'ampiezza; il giorno scelto
in cima alla pagina fissa l'estremo destro.

Su ogni serie va la **fascia della finestra scelta** calcolata da `_band`
— media piu' e meno uno scarto tipo — come banda sullo sfondo: e' il modo
di vedere subito se la linea sta dove deve. La banda si muove col cursore,
perche' si muove la serie su cui e' calcolata. Dove `_band` non puo' (meno
di `MIN_BAND_DAYS` valori) non si disegna, e basta.

## Work

### 1. I dati — `src/training/interface/daily_data.py`

Serve una funzione che renda **una serie di giorni**, non un giorno solo:
le colonne di `health_daily` gia' lette da `fitness_on` e dalle card, per
una finestra che finisce nel giorno chiesto. Il DataFrame `health` passa gia'
di qui intero: e' una fetta, non una query nuova.

Si riusano `_window` e `_band`, non si copiano.

### 2. L'API — `GET /api/daily/trend?from=&to=`

Oggi `/api/daily/{day}` rende **un giorno**: non c'e' niente che renda un
intervallo. La rotta nuova prende i due estremi come date, non un giorno e
un conteggio: e' quello che la pagina ha in mano, e non costringe nessuno a
fare sottrazioni di calendario in due posti diversi.

Rende 422, come fa gia' `build_weekly_data` col lunedi', se `from` viene
dopo `to` o se l'ampiezza sta **fuori da 5-365 giorni**.

Piu' `GET /api/daily/trend/chart/vega` con la specifica gia' pronta, sullo
stampo di `/api/weekly/{monday}/chart/vega`.

### 3. I grafici — `src/training/interface/run_chart.py`

Li disegna **Altair**, come `week_sports_chart`, e l'API li rende come
specifica Vega-Lite. Niente conti e niente disegno nel frontend: e' la
regola che vale dal todo 52.

Cinque pannelli separati, **non un `facet`**: il todo 52 ci ha gia' sbattuto
la testa — dentro una vista composta `width: "container"` viene largo zero.
Un grafico per pannello, ognuno con la sua richiesta.

### 4. Il menu su due righe — `frontend/src/components/TopBar.tsx`

Prima riga Day e Week, seconda riga Report e Trend. Activities esce dalla
griglia e va a destra, staccata: non e' un periodo.

**Niente voci grigie nella riga due.** Month e Year non esistono: si
aggiungono quando ci saranno.

### 5. Il cursore — `frontend/src/components/DayPage.tsx`

Un `<input type="range">` da 5 a 365 sopra i pannelli, con l'ampiezza e le
due date scritte accanto ("28 days  27 Sep - 25 Oct"): il cursore dice
quanto, l'etichetta dice da quando a quando.

Due cose che non sono gratis:

- **l'ampiezza sta nell'URL** (`?days=90`), come il giorno: cosi' un link
  porta anche la finestra. Nell'URL va l'ampiezza, non `from`, perche' e'
  quella che resta vera quando cambi giorno;
- **la richiesta aspetta che il cursore si fermi.** Trascinandolo passa per
  decine di valori: senza una pausa prima di chiedere sono decine di
  richieste e cinque grafici ridisegnati ogni volta.

### 6. L'URL — `frontend/src/navigation.ts`

`?page=week` diventa `?period=week&view=report`. Due regole:

- **il periodo resta quando cambi vista**: da Day/Report clicchi Trend e
  resti sul giorno che stavi guardando;
- **i link vecchi continuano a valere**: `?page=week` apre Week/Report,
  `?day=2026-10-07` apre quel giorno, come adesso.

### 7. La pagina — `frontend/src/components/DayPage.tsx`

Con `view=trend` al posto delle card vanno i cinque pannelli. Intestazione
e scelta del giorno restano quelle, che il giorno serve a tutte e due le
viste.

## Vincoli

- Nessuna dipendenza nuova: Altair e vega-embed ci sono gia'.
- `_band`, `_window`, `DayHeader`, `DatePick` si riusano.
- Niente conti nel frontend.
- Commenti in italiano senza accenti, testi a schermo in inglese.
- vega-embed si carica solo dove serve, come in `RunChart` e `WeekChart`.

## Rischi

- **Cinque grafici in una pagina sono pesanti.** vega-embed e' la parte piu'
  grossa dell'app e qui va istanziato cinque volte. Se la pagina rallenta,
  la via d'uscita e' una specifica sola con i pannelli impilati, non cinque
  richieste.
- **Sotto i 14 giorni la fascia sparisce.** `MIN_BAND_DAYS = 14`
  (`daily_data.py:92`): da 5 a 13 giorni le bande non si disegnano e
  restano le linee nude. E' giusto cosi', ma chi tira il cursore al minimo
  vede sparire meta' del grafico senza sapere perche': va detto a schermo.
- **A 365 giorni i buchi diventano il grafico.** Gli ultimi 28 giorni sono
  pieni, ma indietro no: tra dicembre 2024 e agosto 2026 `health_daily` e'
  quasi vuota. Tirando il cursore in fondo si attraversano quei mesi, e la
  linea deve **spezzarsi** dove i dati mancano, non unire due punti lontani
  mesi con una retta che non e' mai esistita.
- **Trecentosessantacinque punti per serie, per cinque pannelli.** A
  finestra piena sono migliaia di punti disegnati insieme: se vega-embed
  arranca, la via d'uscita e' assottigliare la serie lato Python (un punto
  ogni N giorni oltre una certa ampiezza), non lato browser.

## Verifica

1. `GET /api/daily/trend?from=2026-09-28&to=2026-10-25` rende 28 giorni, e
   i valori dell'ultimo coincidono con quelli di `GET /api/daily/2026-10-25`.
2. Gli estremi: ampiezza 4 e 366 rispondono 422, come `from` dopo `to`. A 5
   giorni i grafici si disegnano senza fasce; a 365 la linea si spezza sui
   mesi vuoti del 2025.
3. Trascinando il cursore parte **una** richiesta per pannello quando ci si
   ferma, non una per valore attraversato.
4. Da Day/Report si clicca Trend e il giorno non cambia; dal tasto indietro
   del browser si torna al Report, stesso giorno.
5. `?page=week` e `?day=2026-10-07` aprono ancora quello che aprivano prima.
6. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless nei due temi: un giorno pieno, un giorno di maggio
   2026 senza dati, e il giorno piu' vecchio che c'e'.

## Come e' andata

Fatto, con una deviazione dalla specifica che vale la pena spiegare.

**Un grafico per misura, non per pannello.** La specifica diceva "un grafico
per pannello", ma dentro un pannello le unita' non sono le stesse: il VO2max
sta a 42 e il punteggio di resistenza a 5000, il carico acuto a 500 e il
rapporto acuto/cronico a 1,1. Su un asse solo la misura piccola viene una
riga piatta. Si poteva normalizzare ogni serie sul suo minimo e massimo, ma
allora la fascia di `_band` non si sarebbe potuta disegnare, e la fascia e'
meta' del motivo per cui il Trend esiste.

La via d'uscita e' stata guardare meglio il vincolo del todo 52. Li' a non
funzionare era il `facet`: `width: "container"` non vale **nelle viste
composte** (`facet`, `vconcat`, `repeat`). Ma `layer` non e' una di quelle —
le barre della settimana sono gia' un `layer` con `width: "container"` e
stanno nel riquadro. Quindi ogni misura e' un grafico a strati (le due
fasce sotto, la linea sopra), con il suo asse nei numeri veri. Sono 22
grafici invece di 5; la richiesta pero' resta **una per pannello**, come
chiedeva la verifica, perche' la rotta rende tutte le specifiche del
pannello in un colpo.

Altre cose decise per strada:

- **Il riposo e' zero, non "non misurato".** Nel pannello Training un giorno
  senza sedute vale 0: e' un dato, al contrario di una notte che l'orologio
  non ha registrato. Per lo stesso motivo li' non c'e' la fascia: fra i
  giorni a zero media e scarto tipo direbbero poco.
- **Le fasce hanno il pavimento a zero.** A 365 giorni il carico acuto sta a
  zero per meta' finestra, e due scarti tipo sotto la media portavano la
  fascia a -200: l'asse si allungava su numeri che non esistono. Stesso
  rimedio di `MORNING_LIMITS` (todo 46), applicato a tutte le misure che non
  possono essere negative.
- **Month e' sparito dalla barra**, invece di restare grigio: il todo dice
  che si aggiunge quando ci sara'. Activities resta, staccata a destra,
  perche' il todo la mette li' esplicitamente.
- **L'ampiezza nell'URL con `replaceState`, non `pushState`.** Il cursore ne
  attraversa decine, e con una voce di cronologia per valore il tasto
  indietro non sarebbe piu' tornato al giorno di prima.
- **La vista non viaggia dove non esiste.** Il collegamento alla Week non si
  porta dietro `view=trend`: la Week il Trend non ce l'ha, e nell'URL sarebbe
  rimasta una vista che quella pagina ignora.
- **L'API prende `from` e `to`, l'URL porta `days`.** Le due date sono quello
  che la pagina ha in mano quando chiede; l'ampiezza e' quello che resta vero
  quando si cambia giorno.
- **La rotta del Trend sta scritta prima di `/api/daily/{day}`**, che le
  prova nell'ordine in cui sono scritte: "trend" sarebbe finito dentro
  `{day}` come data non valida.

Due inciampi, trovati provando:

- `daysFromUrl` partiva da **5 giorni invece di 28**: senza il parametro
  `days`, `Number(null)` e' `0`, che e' un numero finito, e passava il
  controllo per finire schiacciato sul minimo.
- A 365 giorni l'etichetta diceva "26 Oct - 25 Oct", che sembra un giorno.
  Adesso l'anno compare sul primo estremo quando la finestra lo scavalca.

**Un avviso resta in console**, gia' presente prima di questo todo: `WARN
Conflicting legend property "disable"`. Si vede anche sul Report, dove i
grafici sono quelli di sempre: non viene dal Trend e non l'ho inseguito.

**Il tema scuro e' verificato a meta'.** I grafici si': la palette cambia
davvero (`rgb(74,58,167)` chiaro, `rgb(144,133,233)` scuro). Il resto della
pagina no: lo snap di Firefox non lascia aprire una seconda istanza con un
profilo diverso, e `prefers-color-scheme` da BiDi non si falsifica. Non c'e'
niente di nuovo da rompere comunque: le regole CSS aggiunte usano solo le
variabili del tema che c'erano gia'.

### Rifiniture, dopo il merge

Quattro cose chieste guardando la pagina vera, tutte nel commit `5006f8d`
(branch `rifiniture_trend`), fuori da questo todo perche' arrivate dopo.

- **I colori delle card.** Ogni pannello prende quelli della sua card del
  Report, letti da `styles.css`: l'indaco di Health, il cremisi di
  Recovery, il turchese di Load, il blu di Fitness. I tre livelli delle
  barre delle fasce sono riprodotti uno a uno — la linea e' la tinta piena
  dell'icona, la banda stretta il `--range-fill`, quella larga il
  `--range-wide-fill` con la sua opacita'. L'unico numero scelto invece che
  copiato e' l'opacita' della banda stretta (0.38 chiaro, 0.32 scuro): sulla
  barra alta otto pixel e' una tinta piena, stesa su mezza area di grafico
  coprirebbe la linea. Training non ha un colore solo perche' non ce l'ha
  nemmeno la sua card: le serie prendono i colori dei rispettivi effetti.
- **L'icona di sezione su ogni pannello**, dal campo `icon` di `TrendPanel`.
  Non e' una mappa nuova nel frontend: la calcola l'API con
  `report_text.section_icon()`, la stessa che da' l'icona alle card. Una
  fonte sola, cosi' Report e Trend non possono divergere. Load mostra
  `trend.png` come la sua card, perche' nella mappa `"load"` e `"trend"`
  puntano allo stesso file.
- **Nome e unita' in due posti.** Il nome della misura e' il titolo del
  grafico, orizzontale in alto a sinistra; l'unita' e' il titolo dell'asse
  y, in grigio sopra i numeri a cui si riferisce. Prima stavano insieme
  ("Resting HR (bpm)") girati lungo l'asse, e con venti grafici bassi uno
  sotto l'altro un titolo verticale si legge uno alla volta. Le misure
  senza unita' lasciano l'asse muto.
- **Il dislivello in Training**, da `total_ascent_m`, nel verde della salita
  (`up`), lo stesso che ha nel grafico della seduta. Due righe: la serie in
  `TREND_TRAINING` e il colore in `TREND_TRAINING_COLORS`.

- **Un clic apre il Report di quel giorno.** Non si guarda su quale segno
  si e' cliccato: a 365 giorni la linea e' spessa due pixel e i pallini non
  ci sono, e colpirli sarebbe un gioco di mira. Si prende la x del clic e si
  chiede alla scala che giorno sia (`scale.invert`), cosi' vale tutta
  l'altezza della colonna di quel giorno a qualunque ampiezza. Un clic fuori
  dall'area disegnata — sui numeri dell'asse, nel margine — non fa niente.
  Sta nel commit a parte del clic, non in `5006f8d`.

Una nota qui sopra invecchia: la prova del tema scuro cita
`rgb(74,58,167)` e `rgb(144,133,233)`, che adesso sono i colori del solo
pannello Health. Gli altri quattro hanno i loro, e cambiano col tema allo
stesso modo.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_55'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Il Trend legge e basta: niente scritture in
`summary/`, nessuna colonna nuova in `activities.db`, nessuna chiamata a
Garmin. `LOGIC_VERSION` non si muove, quindi il revert non fa rileggere i
file FIT.

Dopo il revert, rifare il merge di `todo_55` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
