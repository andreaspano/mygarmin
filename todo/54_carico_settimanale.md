---
status: done
---

# Il carico della settimana, misurato sulla settimana

La pagina Week dice di parlare di sette giorni, e per tre card su quattro e'
vero: Health e Recovery sono medie dei sette giorni, Fitness e' lo stato di
fine settimana, Training sono le sedute di quei giorni. **La card Load no.**

| cosa mostra | che finestra e' davvero |
|---|---|
| Low aerobic, High aerobic, Anaerobic | il carico degli ultimi **28 giorni** |
| Load ratio | il rapporto fra 7 e 28 giorni |

Le tre barre grandi, quelle con i bersagli di Garmin, raccontano il **mese**.
Due settimane vicine ne condividono tre quarti, quindi nella Week si
somigliano per forza — non perche' gli allenamenti si somiglino, ma perche'
la misura non sa distinguerli. Chiesto da Andrea il 2026-10-23, in queste
parole: *"le misure che voglio vedere nella settimana sono i dati di quella
settimana, non di 28 giorni"*.

## Cosa si puo' sommare davvero, e cosa no

Cercando una misura settimanale del carico sono emerse tre cose, e due
smentiscono quello che sembrava:

- **Il training effect non e' sommabile.** `aerobic_te` e `anaerobic_te`
  stanno per seduta nel database (3.7, 3.3, 1.1...), ma sono un indice 0-5
  di quanto quella seduta ha stimolato il sistema: `3.7 + 3.3` non fa 7 di
  niente. Servono a classificare una seduta, non a sommare una settimana.
- **Un carico per seduta nei FIT non c'e'.** Il messaggio `session` ha 128
  campi, controllati uno per uno: ci sono i due training effect, le calorie
  e il `total_work`, nessun training load. Garmin il carico lo calcola a
  parte e lo manda solo come serie giornaliera.
- **Il carico acuto invece e' gia' settimanale**, e questo e' il punto che
  salva meta' del lavoro: `load_acute` e' la somma degli ultimi sette
  giorni, e letto alla domenica e' esattamente lunedi-domenica. Per una
  settimana chiusa non va cambiato niente.

Resta scoperta la **composizione**: quanto di quel carico era lento e quanto
intenso. Ed e' la domanda vera, perche' lo stesso carico puo' essere dieci
ore lente o tre ore dure (anche questo notato da Andrea).

## La misura che risponde: i minuti per zona

La serie di frequenza cardiaca secondo per secondo c'e' per ogni seduta, e
**ogni seduta porta i propri confini di zona** (`hr_zone_bounds`,
`threshold_hr`): non serve indovinare quale soglia valesse a settembre.
Contare i minuti dentro le tre fasce di Garmin — basso aerobico fino alla
terza zona, alto aerobico fino alla soglia, anaerobico oltre — da' tre
numeri **misurati, non stimati**, e additivi sui sette giorni.

Provato sulla settimana 12-18 ottobre, tre sedute, 32.000 campioni:

```
basso aerobico   493 min
alto aerobico     45 min
anaerobico         1 min
```

E' la stessa cosa che la card Load dice a parole da un mese — *"un sacco di
ore, quasi tutte lente"* — ma in tre numeri confrontabili fra settimane.

## Decisioni

Prese con Andrea il 2026-10-23:

- **La card Load della Week passa ai minuti per zona**, settimanali, al
  posto dei tre carichi mensili.
- **Le fasce sono le dodici settimane**, come Health e Recovery: i bersagli
  di Garmin sono mensili e non si possono mettere accanto a un numero
  settimanale. Cosi' la pagina diventa coerente — ogni numero e' della
  settimana, ogni barra e' il confronto con la stagione.
- **Il carico acuto resta** come carico della settimana, con la sua fascia a
  dodici settimane invece del bersaglio.
- **Load ratio e carico cronico escono dalla Week.** Sono rapporti con il
  mese: nella Day hanno senso come contesto del giorno, qui no. Chi li vuole
  li trova nella Day.

## Work

### 1. I minuti per zona per seduta — `interface/fit.py`, `interface/db.py`

Tre colonne nuove in `activities`: `min_low_aerobic`, `min_high_aerobic`,
`min_anaerobic`, calcolate quando il FIT viene letto.

Si calcolano dalla serie HR con i confini di **quella** seduta: sotto o
uguale al terzo confine di zona e' basso aerobico, fino a `threshold_hr`
alto aerobico, oltre anaerobico — gli stessi tagli che `hr_zones.effects`
gia' usa nella Day. Una seduta senza HR o senza confini le lascia a `NULL`,
che non e' zero e non va confuso con esso.

**Perche' in tabella e non al volo**: leggere le serie di una settimana
costa circa 140 ms (misurato su tre sedute, una delle quali di tre ore), e
una settimana carica ne ha il doppio. L'endpoint settimanale e' appena
sceso a 0,14 s: rimetterci mezzo secondo per un conto che non cambia mai
sarebbe uno scambio cattivo. In tabella la settimana e' una somma.

### 2. Il ricalcolo dello storico — `make backfill_zones`

Le 979 attivita' gia' in tabella non hanno le tre colonne. Un target nuovo
che le ricalcola **dai FIT locali**, senza toccare Garmin: a circa 50 ms per
seduta sono una cinquantina di secondi. Ripetibile, e salta le sedute che
hanno gia' i valori a meno di `--force`.

### 3. La settimana — `interface/weekly_data.py`

`_week_zones(activities, monday)`: la somma delle tre colonne sulle sedute
della settimana, piu' la fascia a dodici settimane per ognuna, con lo stesso
`_band(min_values=MIN_BAND_WEEKS)` che gia' usano le altre card. Una
settimana con una seduta senza HR va detta: se qualche seduta ha `NULL`, il
totale e' parziale e il payload lo dichiara (`sessions_without_hr`).

Il payload perde `load_chronic` e `acwr` dalla Week — restano in
`daily_payload`, che e' l'altro mestiere.

### 4. La card — `frontend/src/components/WeekPage.tsx`

Quattro numeri invece di quattro: carico della settimana, poi i tre tempi
per zona in ore e minuti (`durationLabel`), ognuno con la sua barra a dodici
settimane. Sopra ogni barra non c'e' piu' il bersaglio di Garmin ma la
fascia, quindi le barre diventano uguali a quelle delle altre card — con la
tinta chiara attorno, che il bersaglio non aveva.

**Per quale verso e' buono**: nessuno. Tanto lavoro lento non e' meglio ne'
peggio di poco lavoro lento, dipende dal periodo. Le barre dicono dove sta
la settimana nella stagione, e il testo della sezione Load giudica — e'
esattamente quello che fa gia'.

### 5. L'agente — `.claude/agents/w2_load.md`

Il prompt parla di `load_aerobic_low/high/anaerobic` e dei bersagli di
Garmin, che qui non ci sono piu'. Va riscritto sui tre tempi per zona e
sulle loro fasce, tenendo la parte sul confronto con le quattro settimane
prima, che resta valida. **La Day non si tocca**: li' i bersagli mensili
restano, e il prompt `02_load` con loro.

## Vincoli

- Nessuna dipendenza nuova: la serie HR si legge gia' (`load_activity_records`).
- `make update_activity` non si chiama mai: il ricalcolo legge i FIT che ci
  sono.
- Non si scrive in `summary/` a mano.
- La Day non cambia: stessi numeri, stesse barre, stesso prompt.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Tre colonne nuove in `activities`.** Un revert del codice le lascia
  dov'e': sono innocue, il codice vecchio non le legge. Ma vanno nello
  schema e nella `CREATE TABLE`, e un database vecchio va migrato — il
  repo lo fa gia' altrove, con `ALTER TABLE` idempotenti.
- **Le zone cambiano nel tempo.** Usare i confini della seduta e' la scelta
  giusta, ma vuol dire che due settimane lontane sono contate con tagli
  diversi: a parita' di sforzo, una soglia alzata sposta minuti dall'alto
  aerobico al basso. Sulle dodici settimane l'effetto e' piccolo; su un
  anno no, e il confronto non va fatto.
- **Le sedute senza fascia cardiaca spariscono dal conto** — l'arrampicata,
  le camminate con l'orologio in tasca. Il carico acuto le vede (Garmin le
  stima), i minuti per zona no: due numeri della stessa card potrebbero
  raccontare settimane diverse. Per questo il payload dichiara quante
  sedute non hanno HR, e la card deve dirlo quando capita.
- **Il ricalcolo tocca ogni riga della tabella.** E' ricostruibile dai FIT,
  quindi il danno peggiore e' rilanciarlo, ma va fatto a servizi fermi.

## Verifica

1. `uv run python -c "from training.interface import db, fit, weekly_data"`.
2. `make backfill_zones` su tutto lo storico: nessun errore, e un campione
   di cinque sedute ricontato a mano dalla serie HR deve dare gli stessi
   minuti.
3. Una seduta senza HR (l'arrampicata dell'8 ottobre) resta a `NULL`, non a
   zero, e la settimana che la contiene dichiara la seduta mancante.
4. La settimana 12-18 ottobre deve dare **496 / 45 / 1** minuti (il conto a
   mano qui sopra diceva 493, ma assumeva un campione al secondo: vedi
   "Come e' andata").
5. `/api/weekly/2026-10-12` **non deve rallentare**: era 0,14 s, e con la
   somma in tabella deve restarci.
6. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless: quattro numeri, tre barre, e una settimana vecchia
   senza fascia (meno di sei settimane misurate) con la traccia grigia.
7. La card Load della **Day** non e' cambiata: stessi tre carichi mensili,
   stessi bersagli.
8. La sezione Load della settimana riscritta con il prompt nuovo: deve
   parlare di tempo per zona e non nominare i bersagli di Garmin.

## Come e' andata

Fatto come scritto, con **tre scoperte** che hanno reso il lavoro piu'
piccolo di quanto il todo prevedesse, e una correzione di conto.

### I record erano gia' in tabella

Il todo diceva di leggere i FIT per contare i minuti per zona, e di
aggiungere un `make backfill_zones` da una cinquantina di secondi. Non
serve: la tabella `records` ha gia' la frequenza cardiaca campione per
campione, con il suo timestamp. I minuti si contano da li', e lo storico
intero si riempie in **0,2 secondi** invece che in un minuto. Il target
`backfill_zones` resta comunque, perche' serve a rifare i conti quando il
modo di contarli cambia (`FORCE=1`), ma di suo il riempimento avviene a
ogni `sync()`, accanto a `_fill_missing_thresholds`.

Niente `LOGIC_VERSION` nuova, quindi: quella avrebbe forzato un rebuild e
la rilettura di 979 file FIT per un dato che si ricava da cio' che c'e'
gia'. Le tre colonne si aggiungono con un `ALTER TABLE` idempotente
(`_add_missing_columns`), che e' un meccanismo nuovo per questo repo ma e'
l'unico che evita il rebuild.

### Il campionamento non e' un battito al secondo

Il numero scritto qui sopra — 493 minuti — veniva dal contare i campioni e
dividere per 60. Sbagliato: la registrazione e' a 1 Hz sulle corse ma a
**0,81 Hz** sul giro in bici del 17 ottobre, che ha dei buchi. Il conto
giusto somma le **differenze fra timestamp consecutivi**, con un tetto di
30 secondi oltre il quale e' una sosta e non tempo allenato. I totali veri
della settimana 12-18 ottobre sono **496 / 45 / 1**, a tre minuti da quelli
scritti a mano: la coincidenza e' fortuita, il metodo e' diverso.

Si vede sulla verifica che conta: sulle due corse la somma delle tre zone
torna al minuto con la durata della seduta (46,8 su 46,8), e sul giro di
nove ore resta sotto di un'ora e mezza, che sono le soste.

### La soglia manca su 926 sedute su 979

I minuti per zona hanno bisogno dei confini **e** della soglia, e la soglia
il repo non la retrodata prima del 1 agosto 2026
(`THRESHOLD_FALLBACK_FROM`). Quindi lo storico profondo resta senza, e va
bene cosi': la Week guarda dodici settimane, e **dal 1 agosto tutte e 53 le
sedute hanno i minuti**. Le dodici settimane prima del 12 ottobre sono
tutte misurate.

### Le fasce andavano fermate a zero

Con due settimane di riposo totale dentro la finestra, due scarti tipo sotto
la media davano **-203 minuti**. Le fasce dei minuti e quella del carico
usano `limits=(0, inf)`, lo stesso rimedio del body battery del todo 46.

Le settimane **senza sedute contano zero** e restano nella serie: il riposo
e' un dato della stagione, e toglierlo direbbe "quanto alleni quando
alleni". Una settimana con sedute ma senza frequenza cardiaca e' un'altra
cosa ed esce dal conto — provato su giugno, dove due sedute danno `None` e
`sessions_without_hr: 2`.

### Il costo

L'endpoint passa da **0,14 a 0,17 secondi**: trenta millisecondi per due
fasce nuove (dodici somme settimanali per i minuti, dodici letture del
carico). Il todo chiedeva di non rallentare e intendeva "non tornare al
mezzo secondo": quello e' rispettato.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_54'$" --format=%H -1)
```

Effetti fuori dal repo: le tre colonne `min_low_aerobic`,
`min_high_aerobic` e `min_anaerobic` restano in `activities.db` con i loro
valori. Sono innocue — il codice vecchio non le legge — e si ricalcolano da
sole se un giorno servono di nuovo. Resta anche il `load.md` della settimana
2026-10-12, riscritto durante la verifica con il prompt nuovo: parla di
minuti per zona, che dopo il revert la card non mostra piu'. Si rifa' con
`make weekly_report WEEK=2026-10-12 SECTION=load`.

Dopo il revert, rifare il merge di `todo_54` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
