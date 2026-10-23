---
status: todo
---

# Il report della settimana

Con il todo 51 la pagina Week esiste, con il 52 ha i suoi numeri, le fasce a
dodici settimane e i due grafici. Manca il testo: sette sezioni, una per
card, come la Day.

Oggi un report settimanale c'e' gia', ma e' un'altra cosa: un agente solo
(`weekly-report`) che scrive tre sezioni — Training, Recovery, Trend — in
`summary/02.weekly/<lunedi>.md`. Ne esistono tre file in tutto.

## Decisioni

Prese con Andrea il 2026-10-22:

- **Sette sezioni, non otto**: Health, Load, Recovery, Fitness, Training,
  Next e **un solo Summary**. Il sole e la luna sono del giorno (todo 49):
  una settimana ha un verdetto solo.
- **Next guarda alla settimana dopo**: non la prossima seduta, ma la forma
  del lavoro dei sette giorni che vengono.
- Il vecchio `weekly-report` e il suo formato a tre sezioni **spariscono**,
  come e' sparito `fitness-status` col todo 44. I tre file gia' scritti
  restano dove sono: nessuno li legge piu'.

## Work

### 1. Il registro — `src/training/api/sections.py`

`WEEK_SECTIONS` accanto a `SECTIONS`, con lo stesso `Section`: sette voci,
le cinque delle card che leggono i numeri e poi Next e Summary che leggono i
frammenti delle altre. Vale la stessa `assert`: i verdetti per ultimi.

I frammenti vanno in `summary/02.weekly/<lunedi>/`, una cartella per
settimana, come `01.daily/<giorno>/`.

### 2. L'orchestratore — `src/training/api/refresh.py`

Oggi e' scritto sul giorno: `day`, `daily_payload`, `01.daily`. Va
generalizzato, non duplicato — **un ciclo solo per tutti e due**:

- i fatti vengono da `daily_payload` o dal nuovo `weekly_payload`;
- la cartella e il registro dipendono da cosa si sta scrivendo;
- il lock su file, lo stato per sezione, il controllo dell'`mtime` e la
  tolleranza ai fallimenti parziali restano identici.

Il **momento** (`morning`/`evening`) non si applica alla settimana: e' una
cosa del giorno. Il prompt della settimana non lo riceve.

### 3. Gli agenti — `.claude/agents/`

Sette prompt nuovi, `w1_health` … `w7_summary`: quelli del giorno sono
scritti sul giorno (*"this morning"*, *"today's session"*) e non si possono
riusare. Ereditano `_style.md`, con due aggiunte:

- **le fasce sono a dodici settimane**, e dicono se la settimana sta dove
  stanno le ultime dodici;
- **il soggetto e' la settimana**, non il giorno: non "ieri hai corso" ma
  "tre uscite in sette giorni, due facili e una dura".

Dal giornaliero si eredita quello che ha funzionato: il verdetto in
apertura senza numeri, ogni sezione che giudica solo le proprie misure, e la
liberta' di essere brevi quando non e' successo niente.

### 4. L'API e la pagina

- `POST /api/reports/weekly/{monday}/refresh` e la versione per sezione,
  come per il giorno;
- `GET /api/reports/weekly/{monday}` che compone le sette sezioni dai
  frammenti;
- nella `WeekPage`, il testo sotto ogni card con la sua ora e il suo tasto,
  esattamente come nella Day (todo 44 e 47).

### 5. Quando si scrive

**Il lunedi mattina**, per la settimana appena chiusa, agganciato al giro
delle 10 di `deploy/crontab`: sette agenti una volta a settimana, in coda ai
sei del giorno. Il lunedi diventa il giro piu' lungo, una decina di minuti.

La settimana **in corso** mostra i numeri, che sono sempre freschi, e al
posto del testo il tasto per scriverlo a mano.

## La striscia diventa un selettore di settimane

Chiesto da Andrea il 2026-10-23, guardando la Week. Oggi in alto a destra
c'e' la striscia dei **giorni**, riusata dalla Day cosi' com'era (todo 51):
mostra i sette giorni della settimana e un clic ne apre uno. Ma su una
pagina che parla di settimane il navigatore giusto e' fatto di settimane,
non di giorni.

**Ogni bottone porta tre cose**: il numero della settimana, la data del
lunedi e quella della domenica.

```
┌────────┐ ┌────────┐ ┌────────┐
│  W41   │ │  W42   │ │  W43   │
│  5 Oct │ │ 12 Oct │ │ 19 Oct │
│ 11 Oct │ │ 18 Oct │ │ 25 Oct │
└────────┘ └────────┘ └────────┘
```

Un componente nuovo (`WeekPicker`), non una variante di `WeekStrip`: le due
strisce mostrano cose diverse e mescolarle con una proprieta' le
complicherebbe tutte e due. `WeekStrip` resta alla Day, intatta.

- **Otto settimane**, come gli otto giorni della striscia della Day, e con
  la stessa regola: finiscono con la settimana corrente finche' quella
  scelta ci sta dentro, altrimenti qualche settimana dopo quella scelta,
  cosi' si vede anche cosa e' venuto dopo.
- La settimana aperta e' in un riquadro; quella corrente tratteggiata, come
  "oggi" nella Day.
- I tasti freccia restano: fanno la stessa cosa, un passo alla volta.

**Cosa si perde**: oggi un clic su un giorno della striscia apre la Day di
quel giorno. Con il selettore di settimane quella strada sparisce, ma resta
quella che conta — le sedute nella card Training sono gia' cliccabili e
aprono la Day del loro giorno.

**Da decidere a occhio, quando si vede**: se sotto le date serva anche un
numero che dia il peso della settimana (le sedute, o le ore), come la
striscia della Day mette i chilometri sotto ogni giorno. Tre righe per
bottone potrebbero gia' bastare.

## Vincoli

- Nessuna dipendenza nuova.
- Non si scrive in `summary/` a mano.
- `make update_activity` non si chiama: il settimanale usa i dati che ci
  sono.
- L'orchestratore si **generalizza**, non si copia: due cicli quasi uguali
  che divergono nel tempo sono il modo sicuro di avere due difetti diversi.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Sette prompt nuovi sono sette tarature.** Quelli del giorno hanno
  richiesto parecchi giri per smettere di ripetersi e di sconfinare: qui
  succedera' di nuovo, e la prova costa sette agenti per volta.
- **Il confine con il giornaliero si sfuoca**: la sezione Training della
  settimana rischia di raccontare le singole sedute, che sono della Day. Il
  prompt deve dirlo per nome.
- **Generalizzare l'orchestratore tocca codice che gira due volte al
  giorno.** Se si rompe, si rompono anche i report giornalieri: va provato
  prima su un giorno e poi su una settimana.
- **Un settimanale a settimana e' poco materiale per accorgersi che un
  prompt non va.** Si puo' scrivere a mano qualche settimana passata per
  vedere piu' testi in fretta — il costo e' sette agenti per settimana.

## Verifica

1. `uv run python -c "from training.api import sections, refresh"`, e un
   report **giornaliero** rifatto per intero: l'orchestratore generalizzato
   non deve cambiare niente per la Day.
2. Un report settimanale da terminale su una settimana chiusa: sette
   frammenti in `summary/02.weekly/<lunedi>/`, Next che parla della
   settimana dopo e Summary che non ripete le altre sezioni.
3. Il refresh di una sola sezione: cambia solo quel frammento.
4. Due settimane diverse, una carica e una di scarico: i testi devono
   essere diversi fra loro, non la stessa frase con altri numeri.
5. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless nei due temi.
6. Il giro del lunedi provato per intero, con il `--moment morning` del
   giorno piu' la settimana: deve finire senza che il lock si pesti i piedi
   da solo.
7. Il selettore di settimane: otto bottoni con numero, lunedi e domenica;
   un clic cambia settimana e l'URL; la settimana corrente e' segnata;
   la striscia dei giorni della Day non e' cambiata.
