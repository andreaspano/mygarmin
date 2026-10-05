---
status: todo
---

# Velocita' equivalente nel grafico Speed, salvata nei record

Il todo 26 ha messo la velocita' equivalente in piano in tabella, come un
numero per attivita' (`activities.equiv_speed_kmh`). Nel grafico **Speed**
della scheda di dettaglio (`activity_detail.py`) si vede la velocita' istante
per istante, ma non quanto vale una volta tolta la pendenza: in salita la
curva crolla anche se lo sforzo e' lo stesso. Qui la velocita' equivalente si
calcola **campione per campione**, si salva nella tabella `records` di
`activities.db` e il grafico la legge da li', come seconda curva.

Per scelta di Andrea il dato sta nel database e non si calcola al volo nella
scheda: cosi' la scheda legge solo dati salvati, come per le altre curve.

## Work

- **`grade.py`**: una funzione `equivalent_speed_series(records) -> pd.Series`
  con la velocita' equivalente campione per campione:
  `speed_kmh * minetti_cost(i) / C(0)`, con `i` da `slope_pct` (clip a ±45%,
  come per il valore in tabella). Dove la pendenza non si sa, il fattore vale
  1, come in `equivalent_speed_kmh`. Le due funzioni condividono il calcolo
  del fattore, senza duplicarlo. Il valore salvato e' grezzo, non lisciato:
  la lisciatura e' una scelta di visualizzazione e la fa il grafico.
- **`db.py`**:
  - colonna `equiv_speed_kmh REAL` nella tabella `records` (`_SCHEMA`) e in
    `_RECORD_COLUMNS`;
  - in `_parse_and_store` la colonna si riempie sui `records` gia' letti dal
    FIT, prima di `_insert_records`, solo se lo sport e' in
    `EQUIV_SPEED_SPORTS` e c'e' la quota. Negli altri casi resta `NULL`;
  - `LOGIC_VERSION` passa da "5" a "6", con la nota nello storico delle
    versioni. Il rebuild lo fa `sync()` da solo al primo avvio: niente
    migrazioni a parte e niente modifiche a mano a `activities.db`.
- **`activity_detail.py`**, nel grafico Speed:
  - la curva c'e' solo se `records["equiv_speed_kmh"]` ha almeno un valore.
    Altrimenti il grafico resta com'e' oggi;
  - si liscia con la stessa media mobile di 5 minuti di `speed_kmh_smooth`
    (nel ciclo che gia' fa `heart_rate` e `speed_kmh`). Istante per istante
    e' troppo rumorosa, perche' il rumore dell'altimetro passa nel fattore.
    Passa da `_with_gap_breaks` come le altre, cosi' si interrompe nelle
    pause;
  - colore distinto dalla velocita' (azzurro) e dalla sua media (rosso), per
    esempio verde `#16a34a`, linea continua di spessore 2 come la media;
  - `_synced_series_chart` prende un parametro opzionale per una curva in
    piu', con il suo campo e il suo colore, senza toccare gli altri grafici
    che la usano;
  - una legenda o un sottotitolo che dica cosa sono le curve ("5-min
    average" in rosso, "Grade-adjusted (5-min)" in verde): oggi la linea
    rossa non ha spiegazione, e con tre curve serve;
  - il tooltip del crosshair mostra anche la velocita' equivalente
    dell'istante (lisciata), con un decimale.

## Vincoli

- Nessuna dipendenza nuova. Niente CSS e niente HTML.
- Commenti in italiano senza accenti, UI in inglese.
- `load_activity_records` legge gia' `SELECT *`: la colonna nuova arriva
  da sola, ma controllare che chi usa i record (`activity_report.py`, lo
  scatter, gli istogrammi) non si rompa per una colonna in piu'.
- Il crosshair condiviso fra FC, velocita' e altimetria deve continuare a
  funzionare.

## Rischi

- **Il primo avvio rifa' tutta la cache**: circa 19 minuti con 968
  attivita' (misurato nel todo 26), in cui la pagina sembra ferma. Succede
  una volta sola e va scritto nel report.
- **`activities.db` cresce**: una colonna REAL in piu' su tutti i record
  delle attivita' a piedi. Riportare la dimensione prima e dopo.
- **Lo sport puo' cambiare dopo il parsing**: `sync()` aggiorna lo sport
  quando un'attivita' viene riclassificata su Garmin Connect, ma i record non
  si ricalcolano. Una bici riclassificata come corsa resterebbe senza curva
  fino al prossimo rebuild. E' lo stesso limite di
  `activities.equiv_speed_kmh`: va scritto nel commento, senza risolverlo
  qui.
- **La media della curva non e' il numero della tabella.** La tabella
  pesa i tratti per la distanza e parte dalla velocita' media di Garmin; la
  curva e' una media nel tempo. Saranno vicine ma non uguali, e va scritto
  nel commento.
- **Discese ripide**: il fattore scende fino a 0,5 intorno al -20%, quindi
  in discesa la curva verde sta sotto quella della velocita'. E' il modello,
  non un errore.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Dopo il rebuild, il conteggio per sport delle attivita' con almeno un
   record `equiv_speed_kmh` non nullo combacia con quello di
   `activities.equiv_speed_kmh` (todo 26: 249 corse, 186 escursioni, 68
   camminate).
2. La corsa del 04/10/2026 (10 km, +238 m): la curva verde sta sopra la
   velocita' nelle salite e sotto nelle discese.
3. Una corsa quasi piatta: la curva verde si sovrappone a quella rossa.
4. Un'uscita in bici: il grafico Speed e' identico a prima, senza curva
   verde.
5. Una corsa senza quota (2014-2015): nessuna curva verde e nessun errore.
6. Passando il mouse su un grafico qualsiasi, il crosshair si muove ancora
   su tutti e tre.
7. Le pagine si caricano senza eccezioni (AppTest o server headless).
