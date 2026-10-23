---
status: done
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

- **Otto sezioni**: Health, Load, Recovery, Fitness, Training, Next e il
  **Summary in due parti**, come il sole e la luna del giorno (todo 49).
- **Next e' solo la strategia della settimana**: quante sedute, di che
  tipo, dove va l'intensita' e dove il lungo. Non lo stato con cui arrivi e
  non il verdetto: quelli sono del Summary. Una sezione che dice una cosa
  sola e' anche l'unico modo perche' non finisca per ripetere l'altra.
- **Next si scrive la domenica alle 22 e vale per la settimana dopo.** Sta
  nella pagina della settimana che si chiude, come il Next del giorno sta
  nella pagina di oggi e parla di domani: la domenica sera si guarda il
  riepilogo di quello che e' appena finito e li' si legge cosa fare dal
  giorno dopo.
- Il vecchio `weekly-report` e il suo formato a tre sezioni **spariscono**,
  come e' sparito `fitness-status` col todo 44. I tre file gia' scritti
  restano dove sono: nessuno li legge piu'.

Deciso con Andrea il 2026-10-23, dopo che i numeri della Week erano in
piedi:

- **Il Summary d'inizio e quello di fine**, e il secondo legge il primo:
  "lunedi dicevo di tenerla bassa, e l'hai tenuta bassa" e' la frase che
  nessun'altra sezione puo' scrivere, ed e' la stessa ragione per cui la
  luna legge il sole.
- **Lunedi alle 10 e domenica alle 22**, agganciate ai due giri che gia'
  esistono (`deploy/crontab`): nessuna riga di cron nuova. Mezzanotte del
  lunedi era il primo pensiero, ma li' la settimana ha zero giorni e manca
  la notte — readiness, HRV e sonno del lunedi arrivano col sonno, e sono
  proprio il dato che dice come cominci. Le 23:50 della domenica volevano
  un terzo giro per guadagnare un'ora e cinquanta in cui cambia solo il
  sonno della notte dopo, che e' della settimana nuova.
## Work

### 1. Il registro — `src/training/api/sections.py`

`WEEK_SECTIONS` accanto a `SECTIONS`, con lo stesso `Section`: otto voci,
le cinque delle card che leggono i numeri e poi Next e i due Summary, che
leggono i frammenti delle altre. Vale la stessa `assert`: i verdetti per
ultimi, e `summary_start` prima di `summary_end` perche' il secondo legge
il primo.

Come nel giorno, i due Summary sono **due chiavi e un agente solo**
(`w7_summary`, due rami), e un momento per giro:

| | sezioni |
|---|---|
| lunedi, 10 | health, recovery, load, fitness, training, **summary_start** |
| domenica, 22 | load, fitness, training, **next**, **summary_end** |

Next gira solo la domenica, e prima di `summary_end`: la chiusura puo'
tenerne conto senza ripeterla.

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

Due momenti, tutti e due su giri che gia' girano:

- **lunedi alle 10**, in coda ai sei agenti del giorno: apre la settimana
  che comincia, con la notte appena finita e la settimana chiusa alle
  spalle. Sei sezioni, una decina di minuti.
- **domenica alle 22**, in coda ai cinque della sera: chiude la settimana
  leggendo quello che il lunedi aveva detto, e scrive la strategia per la
  settimana che comincia il giorno dopo.

Nei giorni in mezzo la settimana **in corso** mostra i numeri, che sono
sempre freschi, e il testo resta quello di lunedi, con la sua ora accanto
come nella Day. Il tasto per riscrivere una sezione a mano c'e' comunque.

Da decidere quando il testo esistera': se il Next vada riscritto ogni sera
invece che solo il lunedi. In corsa saprebbe cosa e' gia' successo ("manca
una seduta dura per restare in linea"), e costerebbe un agente al giorno.
Non si decide a tavolino: prima si legge qualche Next scritto il lunedi.

## La striscia dei giorni e' gia' diventata un selettore di settimane

Chiesto da Andrea il 2026-10-23 e **fatto subito, fuori da questo todo**:
era un pezzo di interfaccia e non aveva bisogno del report per stare in
piedi. `WeekPicker` mostra otto settimane, ognuna con il numero ISO e le
date del lunedi' e della domenica; la Day tiene la sua `WeekStrip`.

Resta qui come appunto: quando il report arrivera', il selettore c'e' gia'.

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
- **Next e Summary d'inizio parlano della stessa settimana a dodici ore di
  distanza**, uno la domenica sera e l'altro il lunedi mattina. Il confine
  regge solo se uno dice il lavoro e l'altro lo stato con cui ci arrivi; se
  i testi si somigliano, il ripiego e' fondere Next nel Summary d'inizio e
  restare a sette sezioni — e' successo nel giornaliero, dove Load e
  Fitness hanno smesso di ripetersi solo quando i prompt sono stati
  separati a mano.
- **Da decidere quando il testo esistera': se il Summary d'inizio debba
  leggere il Next della domenica prima.** Sta in un'altra cartella (la
  settimana che si e' chiusa), quindi non arriva da solo. Leggerlo
  chiuderebbe il cerchio fra settimane — "la strategia era tre uscite con
  un lungo" — ma e' anche il modo piu' facile perche' lunedi riscriva
  domenica. Si prova prima senza.
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
2. Un report settimanale da terminale su una settimana chiusa: otto
   frammenti in `summary/02.weekly/<lunedi>/`, Next che dice solo la
   strategia della settimana **dopo** e i due Summary che non ripetono le
   altre sezioni ne' se stessi.
3. I due momenti separati, come nel todo 49: il giro del lunedi scrive
   `summary_start` e **non** tocca `summary_end`; quello della domenica
   scrive la chiusura, che si riferisce all'apertura senza ricopiarla.
4. Il refresh di una sola sezione: cambia solo quel frammento.
5. Due settimane diverse, una carica e una di scarico: i testi devono
   essere diversi fra loro, non la stessa frase con altri numeri.
6. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless nei due temi.
7. Il giro del lunedi provato per intero, con il `--moment morning` del
   giorno piu' la settimana: deve finire senza che il lock si pesti i piedi
   da solo. Lo stesso per la domenica sera.
8. La striscia dei giorni della Day non e' cambiata dal selettore di
   settimane della Week.

## Come e' andata

Fatto come scritto, con **una correzione all'impianto dei due giri** e un
difetto trovato per strada.

### Il lunedi scrive una sezione sola, non sei

La tabella qui sopra dava al giro del lunedi sei sezioni: health, recovery,
load, fitness, training e `summary_start`. Non sta in piedi, e si vede
guardando i numeri invece del disegno: **il lunedi la settimana ha un giorno
di vita**. Le medie di Health e Recovery starebbero su una notte sola, il
carico su un giorno, Training su zero sedute. Provato sui dati veri: la
settimana del 19 ottobre, chiesta a meta' settimana, dichiara
`health_days: 5` su sette e tre sedute — al primo giorno sarebbe stata uno e
zero.

Delle due letture possibili — il lunedi scrive la settimana *appena chiusa*,
oppure quella che *comincia* — vale la seconda, perche' e' quella delle
parole con cui il lavoro e' stato chiesto: *"lunedi spiego come e' cominciata
la settimana, domenica come e' finita"*. Allora l'apertura sta nella cartella
della settimana che apre, e le sezioni numeriche si scrivono quando i numeri
ci sono:

| | quando | sezioni |
|---|---|---|
| apertura | lunedi, 10 | summary_start |
| chiusura | domenica, 22 | health, recovery, load, fitness, training, next, summary_end |

**Chi apre non ha frammenti suoi da leggere** — la sua cartella e' vuota — e
il prompt glielo dice: gli passa la cartella della **settimana precedente**,
dove c'e' tutto, Next compreso. E' lo stesso meccanismo della luna che legge
il sole, allungato di una settimana. Otto agenti in tutto, come previsto:
sette la domenica e uno il lunedi.

### Il `sed` di `install_cron` sostituiva una occorrenza per riga

Le righe del lunedi e della domenica nominano `uv` **due volte** (il giorno e
poi la settimana), e `sed 's|__UV__|...|'` senza `g` lasciava il secondo
segnaposto intatto: cron avrebbe trovato `__UV__ run training-weekly-report`
e il settimanale non sarebbe mai partito. Aggiunto `g` a tutte e quattro le
sostituzioni. E' lo stesso tipo di guasto del todo 47 (`uv: not found`), che
allora si vide solo dopo due giri automatici.

### Altre due cose decise per strada

- **Il tipo di report sta nello stato** (`RefreshStatus.kind`). Giorno e
  settimana condividono un lavoro alla volta e un solo `_state`, ma le
  chiavi delle sezioni sono diverse: senza, la Day avrebbe visto girare un
  lavoro con chiavi che non conosce. Ogni pagina ignora i lavori dell'altro
  tipo.
- **`_run` si prepara lo stato da solo.** Il comando da terminale non passa
  da `start()`, e il primo giro settimanale e' morto su
  `KeyError: 'summary_end'` perche' lo stato aveva ancora le chiavi del
  giorno.

### I testi

Due settimane scritte per intero (5-11 e 12-18 ottobre) e l'apertura della
terza. Parlano della settimana e non dei giorni, usano le fasce a dodici
settimane, e si confrontano con le settimane prima: *"il tuo mese piu' lungo
di orologio e il piu' leggero di carico"*, *"una settimana grande, tutta
schiacciata nella seconda meta'"*. La chiusura del 12-18 nomina il
disaccordo fra le sezioni senza addolcirlo — il corpo calmo tutta la
settimana e il recupero che crolla nel fine settimana — ed e' esattamente
quello che il prompt chiedeva.

**Una cosa da tenere d'occhio**: le due chiusure scritte finiscono tutte e
due con la stessa formula (*"Good work, paid for late"*, *"Strong week, paid
for late"*). Due settimane sono poche per dirlo, ma se la cosa si ripete e'
il prompt del Summary che va stretto. Il rischio era previsto qui sopra, in
un'altra forma.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_53'$" --format=%H -1)
```

Effetti fuori dal repo: restano i frammenti scritti durante la verifica —
`summary/02.weekly/2026-10-05/` e `2026-10-12/` con sette file ciascuna, e
`2026-10-19/summary_start.md` — piu' il `health.md` del 2026-10-22 rifatto
per provare che il giornaliero non fosse cambiato. Dopo il revert nessuno li
legge piu' (l'endpoint della settimana sparisce) e sono innocui; i tre
vecchi report settimanali a file unico (`2026-08-31.md`, `2026-09-21.md`,
`2026-09-28.md`) non sono stati toccati e tornerebbero a essere gli unici.
Il crontab installato non cambia da solo: `make install_cron` va rilanciato
per tornare a due righe.

Dopo il revert, rifare il merge di `todo_53` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
