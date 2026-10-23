---
status: todo
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
4. La settimana 12-18 ottobre deve dare 493 / 45 / 1 minuti, che e' il conto
   gia' fatto a mano qui sopra.
5. `/api/weekly/2026-10-12` **non deve rallentare**: era 0,14 s, e con la
   somma in tabella deve restarci.
6. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless: quattro numeri, tre barre, e una settimana vecchia
   senza fascia (meno di sei settimane misurate) con la traccia grigia.
7. La card Load della **Day** non e' cambiata: stessi tre carichi mensili,
   stessi bersagli.
8. La sezione Load della settimana riscritta con il prompt nuovo: deve
   parlare di tempo per zona e non nominare i bersagli di Garmin.
