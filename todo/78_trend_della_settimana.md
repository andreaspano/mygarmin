---
status: done
---

# Il Trend della Week: la fila delle settimane

Dal todo 59 la Week ha tre viste — Snap, Trend, Plan — ma il Trend e' una
casella vuota: `VIEWS.week` lo elenca (`navigation.ts:46`), il menu lo
disegna, l'URL `?period=week&view=trend` funziona, e sotto l'intestazione non
c'e' niente. Era voluto: «la riga del menu e il vocabolario dell'URL si fanno
una volta, il contenuto arriva quando arriva».

Questo e' il contenuto, e il todo 55 lo aveva gia' scritto: «"Day" qui vuol
dire granularita' giornaliera, non "un giorno solo": un punto per giorno.
Quando ci sara' il Trend della Week sara' un punto per settimana, e la griglia
restera' coerente».

Stessi cinque pannelli della Day, stessa griglia, stesso cursore. Cambia
l'unita' della riga: **un punto per settimana ISO**.

Serve a due cose che a 28 giorni non si vedono. Le misure lente mostrano la
salita intera invece di tre gradini. E la media dei sette giorni toglie il
rumore del singolo giorno, che su una serie lunga e' quasi tutto quello che si
vede.

## Cosa si disegna

Gli stessi pannelli e le stesse serie del Trend della Day, nello stesso ordine,
che e' quello delle card:

| pannello | come si aggrega |
|---|---|
| Health | media dei giorni misurati |
| Recovery | media dei giorni misurati |
| Load | media dei giorni misurati |
| Fitness | media dei giorni misurati |
| Training | **somma** dei giorni, e a **barre** invece che a linea |

## Una regola sola: la media

Lo Snap della Week non fa cosi'. Per il carico legge `_load` (l'ultimo giorno
con un valore) e per la forma `_at_end_of`: «Non si media: sono stati, non cose
che succedono nei sette giorni» (`weekly_data.py`). Quella regola e' giusta
dove sta — una card dice a che punto sei arrivato.

Qui no, e la divergenza e' voluta. Una linea i cui punti fossero "lo stato di
domenica" su un pannello e "la media dei sette giorni" su un altro non si
confronta fra pannelli. E la fascia che si vuole disegnare e' l'errore di una
media: sotto ci vuole una media.

Il Training somma, che i minuti e i chilometri di una settimana sono la loro
somma e non la loro media. E una somma e' una quantita', quindi si disegna a
**barre verticali**. Le barre risolvono da se' due cose che sulla linea erano
scomode: una settimana di riposo e' uno zero vero — `_trend_training` lo dice
gia' per i giorni, «il riposo e' un dato» — e una barra alta zero si legge come
zero invece che come un avvallamento fra due punti; e una settimana senza
sedute non ha niente da spezzare, semplicemente non disegna.

Il Trend della Day resta a linee anche nel suo Training: li' un punto e' un
giorno, non la somma di sette.

## La fascia: l'errore della media, non dove sta la misura

**E' la differenza vera da tutto il resto dell'app, e va detta.**

Ogni fascia che c'e' oggi — `_band` della Day, le barre a dodici settimane
dello Snap — risponde a «dove sta di solito questa misura». Questa risponde a
un'altra domanda: **quanto bene si conosce la media di quella settimana**.

    sterr = scarto tipo dei giorni / radice dei giorni

La fascia e' la media piu' e meno uno e due errori standard. Due conseguenze da
sapere prima di guardarla:

- **e' di ogni punto, non della finestra.** Nel Trend della Day `_band` da' una
  fascia sola per tutta la finestra, disegnata come due rettangoli larghi
  quanto il grafico. Qui ogni settimana ha la sua: una settimana con giorni
  sparsi porta una fascia larga, una con giorni vicini una stretta, ed e'
  esattamente quello che si vuole leggere;
- **non contiene i giorni della settimana.** Con sette giorni `se` e' lo scarto
  tipo diviso 2,65, quindi due errori standard sono circa un scarto tipo e
  mezzo e dentro ci finisce circa meta' dei giorni. Resta monotona nello scarto
  tipo — una settimana sballottata ha comunque la fascia larga — ma a schermo
  va scritto cosa dice, o si legge per quello che non e'.

Due cose non hanno fascia: il pannello **Training**, come nella Day («fra i
giorni a zero media e scarto tipo direbbero poco», e di una somma l'errore
standard non e' definito), e l'**ACWR**, che e' gia' escluso da `TREND_NO_BAND`.

Sotto **tre** giorni misurati la settimana non porta fascia. Due sarebbero il
minimo perche' uno scarto tipo campionario esista, ma su due valori l'errore
standard e' un caso, e la scala y e' condivisa fra gli strati: **una** settimana
con una fascia assurda allarga l'asse e appiattisce le altre cinquantuno.

## La finestra

Un cursore come quello della Day, ma in settimane: **da 4 a 52, di partenza
12**, nell'URL come `?weeks=`. Dodici sono le settimane su cui lo Snap misura
gia' le sue fasce (`BAND_WEEKS`), cosi' il Trend si apre sugli stessi tre mesi
di cui le card parlano.

L'estremo destro e' **la settimana scelta in cima alla pagina**, anche quando e'
in corso. Ogni altra vista della Week parla di quella settimana; un Trend che si
ferma una settimana prima renderebbe l'intestazione una bugia. Si paga che il
Training mostra l'ultimo punto parziale sei giorni su sette: si paga dicendolo,
con `days` nel tooltip («4 of 7») e una didascalia quando la settimana e' aperta.

## Work

### 1. I dati — `weekly_data.py` e `daily_data.py`

In `weekly_data.py`, `_week_stats`: settimana per settimana, la media dei giorni
misurati, quanti erano, e l'errore standard. Raggruppamento per lunedi' in una
passata sola — `_week_mean` settimana per settimana vorrebbe un `reindex` per
ognuna, cinquantadue per colonna e venti colonne.

`sterr` e' `sem()` di pandas, **che e' gia' lo scarto tipo campionario diviso la
radice dei valori**: non si scrive la formula, e i due casi limite vengono
gratis — `NaN` a un giorno solo, media `NaN` a zero giorni.

In `daily_data.py` due estrazioni e un blocco nuovo:

- `_band_edges(centre, spread, limits, digits)` esce da `_band`, che si riduce a
  tre righe. Una funzione sa la **forma** della fascia, due sanno la sua
  **larghezza**: la Day passa lo scarto tipo, la Week l'errore standard;
- `_training_daily` esce da `_trend_training`, che per il resto non cambia;
- il blocco settimanale: `_week_trend_points`, `_week_trend_training`,
  `week_trend_data`, sulla struttura di `trend_data`.

Le settimane senza nemmeno un giorno misurato restano a `None` e **non si
tolgono**, per lo stesso motivo dei giorni in `_trend_points`: la linea si
spezza nel buco invece di attraversarlo.

### 2. L'API — `GET /api/weekly/trend` e `/api/weekly/trend/chart/vega`

Parametri `to` (un lunedi') e `weeks`, non `from`/`to` come la Day: sono 1:1 con
lo stato della pagina e con l'URL, quindi non c'e' un `from` derivato che possa
divergere, e `Query(ge=, le=)` fa da se' la guardia sull'ampiezza.

**Le due rotte vanno scritte prima di `/api/weekly/{monday}`**, per il motivo
gia' imparato col todo 55: le rotte si provano nell'ordine in cui sono scritte, e
"trend" finirebbe dentro `{monday}` come data non valida.

Le due guardie che `get_weekly` ha gia' (lunedi', non futuro) escono in
`_week_monday`, cosi' le tre rotte non divergono.

Quattro modelli paralleli `WeekTrend*`, non un `band` opzionale dentro
`TrendPoint`: pydantic serializza il default, e su 365 giorni per 19 serie
sarebbero settemila `"band": null` in piu' sulla risposta gia' piu' pesante. E
un punto settimanale porta davvero due campi che uno giornaliero non ha, `days`
e il numero ISO della settimana.

### 3. I grafici — `run_chart.py`

I pezzi condivisi escono da `trend_chart`: il tooltip gia' formattato, la barra
del passaggio col `nearest`, la linea, il telaio. Sono l'85% del codice, e
`trend_chart` si ricompone con quelli tenendo intatto il suo ramo `un_livello`.

Poi due strati nuovi:

- **le aree.** La fascia di qui cambia settimana per settimana, e i due
  rettangoli senza `x` della Day non la possono dire: sono due `mark_area` con
  la `x` sui lunedi', nelle stesse due tinte e opacita';
- **le barre.** `mark_bar` per il solo pannello Training. L'unica differenza che
  conta e' la scala: la linea usa `zero=False`, perche' una misura che oscilla
  fra 49 e 52 schiacciata sullo zero sarebbe piatta; una barra invece **deve**
  partire da zero, o la sua altezza mente.

Il ramo guarda il nome del pannello, ed e' lo stesso punto dove Training e' gia'
l'eccezione per la fascia: eccezione una volta sola, non due.

La barra grigia del passaggio resta anche sul Training: e' lei a portare il
tooltip, e serve proprio con le barre basse — su una settimana di riposo la
barra e' alta zero e non ci sarebbe niente da toccare, ma il numero va letto lo
stesso.

### 4. Il frontend

`TrendPanels` diventa riusabile con tre modifiche additive: `OneChart` prende
`onPick` invece di avere `pushUrl({day})` cablato dentro, `Panel` prende
`period` e sceglie la chiamata, e il cursore col suo ritardo di 250 ms esce in
`TrendWindow` — e' il pezzo non ovvio e deve esistere una volta sola. Poi
`WeekTrendPanels`, che tiene la copia: l'etichetta in settimane e le due
didascalie.

In `WeekPage`: il tema (la pagina non ce l'ha), lo stato `weeks` con
`replaceState` e non `pushState` — il cursore attraversa decine di valori e
seppellirebbe la settimana precedente nella cronologia — il `popstate` che
rilegge anche `weeks`, e il ramo che riempie il buco.

Niente CSS: tutte e sette le regole `.trend-*` sono agnostiche al periodo.

**Un bug da correggere di passaggio.** `WeekPage.tsx:224` fa `view === "trend" ?
"Trend" : "Plan"`, quindi la vista Training si intitola "Plan". Va a
`ETICHETTE[view]`, come fa gia' la Day.

## Vincoli

- Nessuna dipendenza nuova: Altair e vega-embed ci sono gia'.
- Niente conti nel frontend: serie, fasce e specifiche arrivano pronte
  dall'API, la regola del todo 52.
- `_band`, `_value`, `_window`, `section_icon` si riusano, non si copiano. Il
  percorso della Day non cambia di un byte.
- I pavimenti restano: `(0, 100)` sui punteggi, `(0, inf)` su carichi e minuti.
  Una fascia non puo' promettere un valore che la misura non puo' avere.
- Vista **a strati**, mai composta: `width: "container"` dentro un `facet` o un
  `vconcat` viene largo zero (todo 52).
- La scala y la dichiara **un solo strato**: in un `layer` e' condivisa.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **L'arrotondamento schiaccia la fascia.** `_band` arrotonda i bordi ai
  decimali della misura. Su uno scarto tipo a 28 giorni va bene perche' e'
  grande; un errore standard e' radice di sette volte piu' piccolo e cade sotto
  il passo. Misurato: VO2max a un decimale, settimana del 5 ottobre, crudo
  `[41.2803, 41.3483]`, arrotondato `[41.3, 41.3]` — un'area di altezza zero.
  I bordi della fascia vogliono due decimali in piu' del valore.
- **Il pannello Load potrebbe venire piatto.** `load_chronic` e' gia' una media
  mobile a 28 giorni: la sua media settimanale e' un lisciamento di un
  lisciamento, e settimane vicine condividono tre quarti della finestra. E'
  esattamente quello che `models.py:506-512` dice quando lo toglie dalla Week.
  Lo si tiene perche' su 52 settimane la deriva lenta e' il punto; se risulta
  una riga dritta, toglierlo e' una tupla di tre righe.
- **La copertura non e' uniforme, e a 52 settimane si vede.** `resting_hr`,
  `stress_avg`, `vo2max` e `sleep_hours` vanno indietro al 2018; i carichi
  all'agosto 2025; readiness, HRV, respiro e punteggio del sonno al settembre
  2025; il body battery al marzo 2026; **endurance score e hill score hanno
  quaranta giorni in tutto**, dal 19 settembre 2026. A finestra piena quei due
  disegnano sei punti su cinquantadue. Non e' un difetto: e' il motivo per cui
  le settimane vuote devono spezzare e non sparire.
- **Il clic deve arrotondare al lunedi' piu' vicino.** `dayAt` arrotonda al
  giorno vicino per stare con la barra grigia; qui i punti sono lunedi' distanti
  sette giorni, e `mondayOf` del giorno cliccato aprirebbe la settimana **prima**
  di quella evidenziata ogni volta che si clicca da giovedi' in poi.

## Verifica

Le estrazioni di `_band`, `_training_daily` e `trend_chart` toccano codice vivo.
Prima di cominciare si salva la risposta della Day, e dopo ognuna si rifa' e si
confronta: **il diff deve essere vuoto**.

```bash
curl -s '.../api/daily/trend?from=2026-08-01&to=2026-10-28' > /tmp/day-before.json
curl -s '.../api/daily/trend/chart/vega?from=2026-08-01&to=2026-10-28&panel=recovery&theme=dark' > /tmp/day-chart-before.json
```

1. I numeri, presi dal database e non stimati. Readiness, `to=2026-10-26`,
   `weeks=12`: la settimana del **19 ottobre** fa `value 62`, `days 7`, fascia
   `60.35 / 64.22` ed esterna `58.41 / 66.16`. Quella del **26 ottobre** e' in
   corso: `week 44` e `days` sotto sette, e il valore cambia ogni giorno che
   passa - non si fissa. La settimana del **12 ottobre** ha
   la fascia **quattro volte e mezzo piu' larga** di quella del 19: se a schermo
   non si vede, le aree stanno leggendo una fascia di finestra ed e' rotta.
2. Gli estremi: `to` che non e' un lunedi' e `to` nel futuro rispondono 422,
   come `weeks` a 3 e a 53; un pannello che non esiste 404. E
   `/api/weekly/2026-10-26` rende ancora lo Snap — se rispondesse 422 dicendo
   `invalid date: trend`, le rotte nuove sono finite sotto `{monday}`.
3. I punteggi restano fra 0 e 100 anche a finestra piena; `acwr` non ha mai
   fascia; il Training ha `band` nullo e `days` 7 poi 4.
4. I grafici: Recovery rende quattro strati `area, area, rule, line` con
   `scale.zero` falso; **Training ne rende due, `rule, bar`, con `scale.zero`
   vero**. Un solo strato dichiara la scala y, e la specifica non e' una vista
   composta.
5. A 52 settimane linea e aree si **spezzano** sui mesi vuoti invece di fare un
   ponte dritto, e l'endurance score disegna sei punti e basta.
6. Il clic fra giovedi' e domenica di una cella apre la settimana che la barra
   grigia evidenzia, non quella prima.
7. Il cursore da 4 a 52 fa **una** richiesta per pannello quando si ferma,
   scrive `?weeks=` nell'URL, e il tasto indietro torna alla settimana
   precedente e non alla posizione precedente del cursore.
8. Da Day/Trend a Week/Trend si portano dietro sia `days` sia `weeks`.
9. Il titolo della scheda su Week/Training dice "Training", non piu' "Plan".
10. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina nei
    due temi. Il `git diff` su `schema.ts` deve essere di sole aggiunte: i tipi
    `Trend*` esistenti non si muovono.

## Come e' andata

Fatto. Due cose trovate per strada vale la pena scriverle.

**L'arrotondamento schiaccia davvero la fascia**, ed era scritto nei rischi ma
senza la misura. `_band` arrotonda i bordi ai decimali della misura: sullo
scarto tipo dei 28 giorni va bene, su un errore standard no. Il VO2max ha un
decimale e la settimana del 5 ottobre ha la fascia a `[41.2803, 41.3483]`, che
arrotondata e' `[41.3, 41.3]` - un'area di altezza zero, cioe' niente. Con
`BAND_DIGITS = 2` l'altezza torna vera (0.06-0.12) e la fascia si vede. Il
valore del punto tiene i suoi decimali: cambiano solo i bordi.

**Un baco vecchio, trovato e lasciato dov'era.** `_trend_text` nasce estraendo
il codice del tooltip, e scrivendola come funzione a se' l'avevo corretta senza
accorgermene: l'originale fa `"-" if v is None`, ma `v` arriva da una colonna
di pandas, dove il mancante e' `NaN` e non `None`, e `NaN is None` e' falso.
Quindi il tooltip di un giorno non misurato scrive `"nan"`, e il ramo `"-"` non
e' mai stato raggiunto. Il diff di regressione l'ha visto subito. Siccome qui
sopra c'e' scritto che il percorso della Day non cambia di un byte, ho
ripristinato il comportamento di prima e lasciato il baco: si corregge in un
todo suo, dove si vede. Il Trend della Week passa invece la lista dei valori,
dove il nullo e' nullo davvero, e li' il tooltip dice "-".

Altre cose decise per strada:

- **La fascia della Week non e' quella della Day, e si e' visto nel codice.**
  `_band` sapeva due cose: la forma della fascia e da dove viene la sua
  larghezza. Separarle (`_band_edges`) e' stato il modo di avere due fasce
  diverse senza due funzioni gemelle: una sa la forma, due sanno la larghezza -
  lo scarto tipo per la Day, l'errore standard per la Week.
- **`sem()` di pandas e' gia' `std(ddof=1)/sqrt(n)`.** Il todo diceva che la
  formula era codice nuovo; non lo era. Scritta cosi' i due casi limite vengono
  gratis: `NaN` a un giorno solo (niente fascia) e media `NaN` a zero giorni (il
  punto resta nullo e la linea si spezza).
- **Il parametro e' `to` + `weeks`**, non `from`/`to` come la Day. E' 1:1 con lo
  stato della pagina, quindi non c'e' un `from` derivato che possa divergere, e
  `Query(ge=, le=)` fa la guardia sull'ampiezza da sola.
- **`TrendPanels` e' diventato riusabile, non duplicato.** `OneChart`, `Panel`,
  `PANELS` e il cursore (`TrendWindow`, col suo ritardo) servono tutti e due i
  periodi; `WeekTrendPanels` tiene solo quello che cambia, che sono le parole e
  il bersaglio del clic. `Panel` prende `period` come **stringa** e non una
  funzione di carico: una callback cambierebbe identita' a ogni render e
  rifarebbe la richiesta ogni volta.
- **Corretto il titolo della scheda della Week**, che su Training diceva "Plan":
  il ternario aveva due rami per tre viste. Adesso legge `ETICHETTE`, come la
  Day, cosi' una vista nuova non puo' restare senza nome.

**La verifica a schermo e' stata fatta rendendo le specifiche, non con uno
snap della pagina.** `firefox --headless --screenshot` scatta prima che le
richieste tornino: la pagina esce con cinque "Loading..." - e lo fa anche il
Trend della **Day**, che qui non e' stato toccato, quindi e' il metodo e non il
codice. Al suo posto le specifiche sono state compilate con `vega-lite` e rese
in SVG con `vega` (gli stessi che usa il browser), e gli SVG - che sono statici
- fotografati. Si vede quello che si doveva vedere: la fascia che **cambia
larghezza** settimana per settimana, i due livelli con l'esterno piu' chiaro, la
linea sopra, le barre del Training che partono da zero con l'ultima bassa
perche' la settimana e' aperta, e a 52 settimane linea e aree **spezzate** sul
vuoto di agosto.

Due cose restano da guardare nella pagina vera, che da qui non si provano: il
clic che deve aprire la settimana evidenziata (la trappola di `nearestMonday`)
e il tasto indietro dopo aver mosso il cursore.

### L'errore standard rifatto, dopo il merge

Chiesto da Andrea guardando la pagina vera, e fuori da questo todo perche'
arrivato dopo. La fascia c'era, ma la larghezza veniva da **quella settimana**:
`sem()` di pandas, cioe' lo scarto tipo dei suoi giorni diviso la radice di
quanti erano. Adesso la varianza e' **aggregata su tutta la finestra**:

1. la varianza dentro ogni settimana;
2. la media di quelle varianze, `varianza_media`;
3. lo scarto tipo, `radice(varianza_media)` - **uno solo per la finestra**;
4. per ogni settimana, `sterr = scarto_tipo / radice(n)`, con `n` i giorni
   misurati di quella settimana.

`_week_stats` quindi rende la **varianza** e non piu' l'errore standard, che
una settimana alla volta non si puo' calcolare; l'aggregazione la fa
`_week_trend_points`, che ha la finestra intera sotto gli occhi.

**La conseguenza e' grossa e va saputa leggendo il grafico.** La larghezza
della fascia adesso dipende **solo da quanti giorni ha la settimana**, non da
quanto quei giorni erano sparsi. Due settimane piene hanno la stessa fascia:
sul readiness delle dodici settimane fino al 26 ottobre tutte le settimane da
sette giorni misurano 11.61 di larghezza, e solo quella in corso, con quattro
giorni, arriva a 15.36. A schermo non e' piu' un profilo che si gonfia e si
sgonfia, e' un nastro di spessore costante che si allarga dove la media sta su
meno misure. Non si legge piu' "che settimana sballottata e' stata"; si legge
"quanto e' solida questa media". I testi che dicevano il contrario - il
commento del blocco, la descrizione del modello, le docstring delle rotte, la
didascalia a schermo e il README - sono stati riscritti tutti.

Verificato contro il conto a mano, passo per passo: `varianza_media` 235.8780,
scarto tipo 15.3583, `sterr` 5.8049 con sette giorni e 7.6792 con quattro - gli
stessi numeri che rende il codice.

**`MIN_WEEK_DAYS` resta tre, ma per un altro motivo.** Valeva perche' su due
valori l'errore standard della singola settimana era un caso; con la varianza
aggregata non lo e' piu', e una settimana di un giorno solo avrebbe una fascia
definita - la piu' larga di tutte. Il minimo resta perche' una media fatta su
uno o due giorni e' un punto debole, e disegnarle attorno una fascia regolare
la farebbe sembrare una misura come le altre. Se si vuole, adesso puo'
scendere a uno senza rompere niente.

### La fascia centrata, e la linea centrale

Sempre su richiesta di Andrea, subito dopo. La fascia era costruita attorno
**alla media di ogni settimana**, e cosi' accompagnava la linea: il punto
stava dentro la sua fascia per costruzione, sempre, e non c'era niente da
leggere. Adesso e' costruita attorno a **x-bar-bar**, la media delle medie
settimanali, che e' una sola per la finestra; e x-bar-bar si disegna, come
**riga tratteggiata**.

Con questo le tre richieste messe in fila si rivelano una cosa sola, e ha un
nome: **e' una carta di controllo x-bar**. La settimana e' il sottogruppo,
x-bar-bar e' la linea centrale, i limiti sono a uno e due errori standard, la
varianza e' aggregata dentro i sottogruppi e ogni settimana divide per la
radice dei suoi giorni. Separate, le tre scelte sembravano tre dettagli
statistici; insieme sono il disegno standard, e il grafico si legge come si
leggono quelli: **dove sta la settimana rispetto a dove di solito sta il
corpo**, non rispetto a se stessa.

Si vede subito. Sul readiness delle dodici settimane fino al 26 ottobre il
centro e' a 63.2 e i limiti stanno a 57.39 / 69: le settimane di inizio agosto
(42, 48, 53) cadono **sotto**, il picco di inizio settembre (86) sta **sopra**,
e sono esattamente le settimane in cui era successo qualcosa. Prima, con la
fascia attaccata a ogni punto, quelle cinque settimane sembravano identiche a
tutte le altre.

Il `centre` e' un campo della serie e non del punto, che e' uno solo per la
finestra, ed e' nullo dove la fascia non c'e': l'ACWR e tutto il pannello
Training.

**Una cosa da decidere, che adesso si vede.** Con la fascia costante il minimo
di `MIN_WEEK_DAYS` lascia un **buco** nel rettangolo dove una settimana ha meno
di tre giorni misurati - sul battito a riposo succede a fine agosto, e la riga
centrale prosegue mentre la fascia si interrompe. In una carta di controllo
vera i limiti con un sottogruppo piccolo non spariscono: si **allargano**, ed
e' il tipico profilo a scalini. Il minimo e' rimasto a tre perche' nessuno ha
chiesto di toglierlo, ma la sua ragione originale era caduta gia' col passo
prima, e adesso si paga anche a vedersi. Portarlo a uno e' cambiare una
costante.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_78'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Il Trend della Week legge e basta: niente
scritture in `summary/`, nessuna colonna nuova in `activities.db`, nessuna
chiamata a Garmin. `LOGIC_VERSION` e `HEALTH_LOGIC_VERSION` non si muovono,
quindi il revert non fa rileggere i file FIT ne' i JSON della salute.

Dopo il revert, rifare il merge di `todo_78` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
