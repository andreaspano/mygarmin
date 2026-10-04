---
status: done
---

# Week: l'andamento del VO2max

Dopo il todo 07 il VO2max dell'orologio sta nella cache (`activities.vo2max`) e
si vede attivita' per attivita' nella pagina Day. Qui lo si guarda nel tempo,
sulla pagina Week, accanto ai volumi: e' li' che si vede se sale, scende o sta
fermo mentre cambiano i chilometri e le ore.

**Dipende dal todo 07**: non partire se quello non e' fatto e unito a `main`
(senza la colonna `vo2max` non c'e' niente da disegnare).

**Dipende anche dal todo 09, che viene prima.** Quello sposta la macchina della
pagina Week in un modulo condiviso (`period_page.py`) e aggiunge la pagina
Month: la riga nuova va aggiunta **li'**, non in `week.py`, e cosi' comparira'
su tutte e due le pagine senza lavoro in piu'. Due conseguenze su cio' che sta
scritto qui sotto: i numeri di riga di `week.py` non valgono piu', e i nomi
`_week_rows_closed` e `week_row_` diventano `spec.key("rows_closed")` e
`spec.key("row", ...)`. Il punto mensile e' l'ultimo VO2max delle corse del
mese, con la stessa regola del punto settimanale (niente punto se nel periodo
non si e' corso).

Da ricordare su cosa significa il numero (i dettagli e le verifiche stanno nel
todo 07): e' la stima corrente dell'orologio alla fine dell'attivita'. Le corse
che si qualificano la aggiornano, tutte le altre attivita' se la portano
dietro. Per questo qui si guardano **solo le corse**.

Work:

- Una quinta sezione richiudibile, **VO2max**, sotto le quattro che ci sono,
  con lo stesso meccanismo: chiave propria, stato iniziale scritto nella chiave
  e non passato con `expanded=` (altrimenti servono due click, gia' successo),
  `on_change="rerun"`, memoria `_week_rows_closed`.
- Un pannello solo, non la coppia settimanale + cumulato: il cumulato di un
  VO2max non vuol dire niente. Largo quanto la riga intera.
- Un punto per settimana: l'**ultimo valore delle corse** di quella settimana
  (`sport == "running"`), cioe' la stima dell'orologio a fine settimana.
- **Le settimane senza corse non hanno punto**, e non vanno a zero: qui lo zero
  non e' "nessun allenamento", e' un numero falso. E' il contrario di quello
  che fa `_weekly_sum()` per i volumi, quindi non passare di li'. La linea
  unisce i punti che ci sono.
- Asse y in `ml/kg/min` e **non da zero** (`zero=False`): i valori stanno fra
  36 e 45, e partendo da zero la linea sarebbe piatta.
- Segue il periodo scelto come gli altri grafici. **Non** segue le pills degli
  sport: non e' una grandezza per sport, e' una sola.
- Tiene le stesse cose degli altri pannelli dove hanno senso: etichette w26...
  e titolo dell'asse, verticali e nomi dei mesi, crosshair, tooltip (settimana,
  data, valore con un decimale), e il click che sceglie la settimana, letto da
  `_clicked_week()` come per le altre righe.
- Meglio una funzione sua che piegare `_chart()`: quella ragiona per serie
  sommate per sport, con area del totale e riempimento a zero.
- Le regole del todo 04 valgono anche qui: nome `VO2max`, unita' sull'asse.

Vincoli:

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Non toccare le quattro righe esistenti, `CHART_ROWS`, ne' la larghezza fissa
  (`CHARTS_TOTAL_WIDTH`): il pannello nuovo deve starci dentro.
- Non toccare `fit.py`, `db.py` e la tabella: sono il todo 07.

Rischi:

- Il pannello e' una vista Vega a se', come le altre righe: il crosshair non e'
  condiviso con loro. E' gia' cosi' fra le righe, non e' una regressione.
- Con periodi corti e poche corse i punti sono due o tre: il grafico deve
  reggere anche un punto solo (niente linea) e nessun punto (un messaggio, non
  un pannello vuoto o un errore).
- Un pannello largo il doppio degli altri ha un rapporto larghezza/altezza
  diverso: controllare che non risulti schiacciato, ed eventualmente dargli
  un'altezza sua.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. Con "12 weeks" i punti di settembre sono 39.4 (w36), 40.1 (w37), 40.2
   (w38) e 40.8 (w39, con le corse del 25 e del 26 settembre); una settimana
   senza corse non ha punto; l'asse y non parte da zero. Dati al 2026-09-26:
   corse scaricate piu' tardi possono cambiare l'ultima settimana.
2. Con "All" la serie va da aprile 2025 (w18) a settembre 2026, fra 36.7 e
   41.2: 11 settimane con un punto nella Week, 6 mesi nella Month. Sono i
   numeri delle sole corse; quelli di tutte le attivita' (da gennaio 2025, fino
   a 44.6 per un giro in bici) sarebbero il segno che il filtro non funziona.
3. La sezione si apre e si chiude **con un click solo**, resta chiusa cambiando
   pagina e tornando, e il click su un punto sceglie la settimana.
4. Spegnere sport nelle pills non cambia il grafico del VO2max.
5. Un periodo senza corse mostra un messaggio invece del grafico, senza
   eccezioni.
6. A 1440px con la sidebar aperta il pannello sta nel contenitore, come le
   altre righe.
7. Nessuna eccezione: `AppTest` sulle tre pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

## Chiuso (2026-09-27)

Tutte e sette le verifiche passano. Il browser che mancava il 26 settembre
(estensione Chrome non connessa) e' stato sostituito da Selenium sul Firefox di
sistema, pilotato via geckodriver: l'app girava su http://localhost:8501 a
1440x1000, con la sidebar aperta.

**La verifica 6 ha trovato un difetto vero, ed e' stata la sola a cambiare il
codice.** `VO2MAX_WIDTH` era `CHARTS_TOTAL_WIDTH - _AXIS_WIDTH - _VEGA_PADDING
// 2` = 812, scritto pensando che Vega aggiungesse assi e margini a `width`
come fa per le altre righe. Misurato: l'`<svg>` del pannello veniva fuori largo
**esattamente 812px**, contro i 912px delle righe dei volumi. Cento pixel piu'
stretto, con un buco a destra dentro un contenitore largo come gli altri.

Il motivo e' l'`autosize` di Vega-Lite, che si applica a una vista sola ma non
ai `concat`: questo pannello e' un `layer`, quindi `width` e' la larghezza
**totale** (assi e margini dentro), mentre le quattro righe sopra sono un
`hconcat`, dove `width` resta la sola area di disegno. Ora `VO2MAX_WIDTH =
CHARTS_TOTAL_WIDTH`: rende 914px contro i 912px delle righe (i 2px sono
l'arrotondamento di `CHART_WIDTH`). Verificato cambiando il valore e
rimisurando: 812 -> 812, 914 -> 914. `CHARTS_TOTAL_WIDTH`, `CHART_ROWS` e le
quattro righe esistenti non sono state toccate, come chiedevano i vincoli.

Esiti, uno per uno:

1. **Passa.** w36 39.4, w37 40.1, w38 40.2, w39 40.8; le settimane senza corse
   (w29-w35) non hanno punto; l'asse y va da 39.5 a 40.5, non da zero. Il
   tooltip del primo punto legge "Week w36 / Starting 31 Aug 2026 / VO2max
   39.4".
2. **Passa.** Con "All": 11 settimane con un punto, da w18 (2025-04-28) a w39
   (2026), fra 36.7 e 41.2; 6 mesi nella Month. Sono i numeri delle sole corse,
   come deciso il 26 settembre con l'opzione (a).
3. **Passa.** Un click solo apre e un click solo richiude (`open` true -> false
   -> true). Chiusa sulla Week, si va sulla Month e si torna: e' ancora chiusa.
   Il click su un punto sceglie la settimana: cliccato il punto della w36, la
   sezione sotto e' passata da "By sport - 21 Sep 2026 - 27 Sep 2026" a "By
   sport - 31 Aug 2026 - 06 Sep 2026".
4. **Passa.** Spegnendo prima Cycling e poi Running, i quattro punti del VO2max
   restano agli stessi pixel, mentre le righe dei volumi passano da 8 a 6 linee:
   la pill funziona, e il pannello non la ascolta.
5. **Passa.** Dal 2026-07-01 al 2026-08-20 (attivita' sì, corse no) compare
   "No run with a VO2max in the selected weeks." al posto del grafico, senza
   eccezioni.
6. **Passa, dopo la correzione di sopra.** A 1440px con la sidebar aperta: il
   pannello sta nel contenitore (914 su 914), la pagina non scorre in
   orizzontale (1440 su 1440), e ora e' largo come le righe dei volumi (914
   contro 912).
7. **Passa.** `AppTest` sulle tre pagine (Day, Week, Month): nessuna eccezione.
   Piu' il giro nel browser di cui sopra.

Nota su `AppTest`: non raggiunge i widget dentro le sezioni richiudibili, quindi
le verifiche 3 e 4 sono state fatte nel browser e non li'. La 5 e la 7 passano
anche da `AppTest`.

## Needs decision (atodo, 2026-09-26) — risolto

**Verifiche 1 e 2: decise il 2026-09-26.** La 2 con l'opzione (a); la 1
aggiornata con la w39 a 40.8. Tutte e due sono gia' corrette sopra; il testo qui
sotto resta per memoria. Il controllo nel browser (verifiche 3 e 6) e' stato
fatto il 2026-09-27: vedi la sezione qui sopra.

**Expected-result change**, verifica 2: "da gennaio 2025 a settembre 2026, fra
36.6 e 44.6" -> con la regola del Work ("solo le corse") la serie va **da
aprile 2025 (w18) a settembre 2026, fra 36.7 e 41.2**, 11 settimane con un
punto (6 mesi nella Month).

I numeri attesi sono quelli di *tutte* le attivita', non delle corse: 44.6 e'
un giro in bici del 2025-06-16 (la bici ha una stima sua), e gennaio 2025 e' lo
sci di fondo. La prima corsa in cache e' del 2025-04-28. L'implementazione
segue il Work; la verifica, cosi' com'e' scritta, non puo' tornare.

Anche la verifica 1 ("settembre fra 39.4 e 40.2") oggi non torna del tutto:
la w39 (dal 21 settembre) vale 40.8, perche' le corse del 25 e del 26 settembre
(VO2max 41) sono arrivate dopo che il todo era stato scritto. Le altre
settimane di settembre sono 39.4, 40.1 e 40.2, come previsto.

Opzioni:
- (a) correggere la verifica 2 con i numeri delle corse (raccomandato: la
  regola "solo corse" e' motivata nel todo, e il 44.6 della bici lo conferma);
- (b) tornare a tutte le attivita', contro quanto scritto nel Work.

Non fatto per mancanza del browser (estensione Chrome non connessa): verifica
3 (un click solo per aprire/chiudere nel browser vero, click su un punto che
sceglie la settimana) e verifica 6 (a 1440px con la sidebar aperta il pannello
sta nel contenitore; `VO2MAX_WIDTH` = 812 e' una stima, non misurata).

**Fatte il 2026-09-27.** Il sospetto sui 812px era fondato: misurati, erano
cento pixel di meno delle altre righe. Vedi "Chiuso" qui sopra.

## Revert

Il todo 08 non ha un merge: i tre commit sono andati direttamente su
`main` (`0f20642`, `9429960`, `bba4b40`), e il revert li annulla tutti e tre.

```bash
git revert --no-edit bba4b40 9429960 0f20642
```

Effetti fuori dal repo: nessuno.
