---
status: todo
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

1. Con "12 weeks" i punti di settembre stanno fra 39.4 e 40.2; una settimana
   senza corse non ha punto; l'asse y non parte da zero.
2. Con "All" la serie va da gennaio 2025 a settembre 2026, fra 36.6 e 44.6.
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
