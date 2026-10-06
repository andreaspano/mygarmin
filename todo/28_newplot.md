---
status: todo
---

# Grafico di analisi della corsa a tre fasce

Nella pagina **Day** (`app_pages/activities.py`), la scheda di dettaglio
di un'attivita' (`activity_detail.py`) ha sei grafici separati: Heart rate,
Speed, Altitude, Speed vs HR e i due istogrammi di velocita' e battiti. Le
zone cardiache non si vedono da nessuna parte. Qui quei sei grafici si
tolgono e al loro posto va un grafico unico, con il tempo in ascissa e tre
fasce allineate:

| Fascia | Contenuto | Forma |
|---|---|---|
| Alta (~25%) | Battiti | Barre ogni 30 s, colore secondo l'effetto stimato |
| Centrale (~50%) | Velocita' reale e velocita' equivalente in piano | Due linee |
| Bassa (~20%) | Pendenza in gradi, in valore assoluto | Barre ogni 30 s, verdi in salita e rosse in discesa |

Dietro le tre fasce, a tutta altezza, le **zone cardiache** come bande
verticali in un solo colore (viola) che si scurisce con la zona, con sopra
la zona e la media dei battiti del tratto. Le **pause** restano senza colore,
con la sola etichetta "pause". Sopra il grafico, un **riepilogo**: minuti per
effetto stimato e i due Training Effect di Garmin.

Il grafico e' stato messo a punto fuori dal progetto, su un HTML con
Chart.js, sulla corsa del 03/10/2026 (7 km, +286 m, `activity_id`
24588452569). Da quel lavoro vengono i parametri e i valori attesi qui
sotto. Il codice era uno script a parte con `fitdecode`: non si porta, si
rifa' con gli strumenti dell'app.

## Decisioni

- **Dove**: nella pagina Day, al posto di tutti e sei i grafici della
  scheda di dettaglio. Restano le metriche in cima, il commento e la mappa
  del percorso (che non e' un grafico).
- **Per tutti gli sport**, visto che e' l'unico grafico rimasto: ogni
  pannello c'e' solo se c'e' il suo dato. Battiti se c'e' la FC, velocita'
  se c'e' la velocita', pendenza se ci sono quota e distanza. La linea
  della velocita' equivalente solo per gli sport in `EQUIV_SPEED_SPORTS`
  (corsa, escursionismo, camminata): per la bici Minetti non vale. Una
  palestra mostra solo il pannello dei battiti con le zone.
- **Una pendenza sola**: il metodo a finestra in metri (sotto) sostituisce
  quello di `grade.slope_pct`, e vale per tutto: tabella (todo 26), curva
  del grafico Speed (todo 27) e grafico nuovo. Due pendenze darebbero due
  velocita' equivalenti diverse per la stessa corsa.
- **Altair, non Chart.js**: tre pannelli in `vconcat` con l'asse del tempo
  in comune e il crosshair sincronizzato, come gli altri grafici dell'app.
  Niente assi "gonfiati" per far stare tre fasce su un canvas e
  niente disegni a mano.
- **L'effetto dell'allenamento e' una stima** sui battiti e va detto in
  pagina ("estimated"): Garmin lo calcola con un algoritmo suo e nel file
  salva solo i totali della sessione, che il riepilogo mostra accanto.
- **Assi ricavati dai dati**, non fissi: velocita' da 0 al massimo
  arrotondato per eccesso, pendenza da 0 al massimo in gradi arrotondato per
  eccesso, battiti dal minimo al massimo arrotondati alla decina.

## Parametri

| Parametro | Valore | Uso |
|---|---|---|
| Intervallo del grafico | 30 s | Barre e punti delle linee |
| Buco che fa una pausa | > 5 s | Divisione in segmenti |
| Lisciatura della quota | media mobile centrata, 15 s | Prima della pendenza |
| Finestra della pendenza | 30 m prima e 30 m dopo | Pendenza punto per punto |
| Distanza minima della finestra | 20 m | Sotto, pendenza NaN |
| Lisciatura della velocita' | media mobile centrata, 30 s | Linea della velocita' |
| Lisciatura della pendenza per le barre | media mobile centrata, 20 s | Barre |
| Lisciatura della pendenza per la normalizzazione | media mobile centrata, 90 s | Velocita' equivalente |
| Lisciatura dei battiti per le zone | media mobile centrata, 45 s | Bande delle zone |
| Durata minima di una banda | 60 s | Bande delle zone |
| Campioni minimi per intervallo | 10 | Sotto, l'intervallo si scarta |

Ogni tratto continuo fra due pause e' un **segmento**: tutte le medie mobili
si calcolano dentro il segmento, mai a cavallo di una pausa. Il tempo in
ascissa e' quello trascorso dalla partenza, pause comprese.

## Work

- **`grade.py`**:
  - `slope_pct(records)` diventa: quota lisciata a 15 s; per ogni campione,
    il primo punto a non piu' di 30 m indietro e l'ultimo a non piu' di 30 m
    avanti lungo `distance_km`; pendenza = dislivello / distanza x 100, NaN
    se la finestra e' sotto i 20 m. La finestra e' in metri perche' nei
    tratti lenti pochi secondi coprono pochi metri e il rapporto impazzisce.
  - `_cost_factor` usa la pendenza lisciata a 90 s, dentro i segmenti, con
    la clip a ±45% che c'e' gia'. Il resto (`minetti_cost`,
    `equivalent_speed_series`, `equivalent_speed_kmh`) non cambia.
  - una funzione per i segmenti (buco > 5 s), usata da qui e dal grafico.
- **`fit.py`** / **`db.py`**:
  - dalla sessione, `total_training_effect` e
    `total_anaerobic_training_effect`; dal messaggio `time_in_zone` con
    `reference_mesg = session`, `hr_zone_high_boundary` (sei valori: il
    primo e' il tetto della "zona 0", i tetti di Z1-Z4 sono i quattro dopo)
    e `threshold_heart_rate`. Se mancano (file vecchi), `NULL`;
  - colonne nuove in `activities`: `aerobic_te REAL`, `anaerobic_te REAL`,
    `threshold_hr INTEGER`, `hr_zone_bounds TEXT` (i quattro tetti Z1-Z4 in
    JSON);
  - `LOGIC_VERSION` passa da "6" a "7", con la nota nello storico: colonne
    nuove e pendenza nuova, quindi `equiv_speed_kmh` cambia in entrambe le
    tabelle. Il rebuild lo fa `sync()` da solo.
- **Modulo nuovo `run_chart.py`** in `src/training/interface/`, con i
  calcoli separati dal disegno:
  - `zone_bands(records, bounds)`: battiti lisciati a 45 s nel segmento;
    zona = 1 + tetti superati; tratti consecutivi nella stessa zona; ogni
    tratto sotto i 60 s si accorpa al vicino piu' lungo, poi si uniscono i
    vicini uguali, finche' non restano tratti corti. Per ogni banda: inizio,
    fine, zona, media dei battiti grezzi. Senza lisciatura e accorpamento i
    battiti che oscillano intorno a una soglia fanno tante strisce sottili;
  - `effects(records, bounds, threshold_hr)`: basso aerobico fino al tetto
    di Z3, alto aerobico fino a `threshold_hr`, anaerobico sopra; secondi
    per effetto contati sui record al secondo;
  - `bins(records)`: una riga per intervallo di 30 s con minuto centrale,
    velocita', velocita' equivalente, pendenza (% e gradi, `atan(p/100)`) e
    battiti medi;
  - `run_analysis_chart(...)`: i tre pannelli in `vconcat`, con le bande
    delle zone come `mark_rect` in ogni pannello (stesse x, cosi' sembrano
    una banda sola), le due soglie degli effetti tratteggiate nel pannello
    dei battiti, le linee interrotte sulle pause, un tooltip unico con
    tempo, battiti (zona ed effetto), le due velocita' e la pendenza in
    gradi e in %.
- **`activity_detail.py`**:
  - via i sei grafici (Heart rate, Speed, Altitude, Speed vs HR, Speed
    distribution, HR distribution) e il codice che serve solo a loro:
    `_synced_series_chart`, la lisciatura a 5 minuti, gli istogrammi, lo
    scatter, e `_with_gap_breaks` se non lo usa piu' nessuno;
  - al loro posto il riepilogo (minuti per effetto, Training Effect) e il
    grafico nuovo a tutta larghezza, sopra la mappa;
  - senza tetti delle zone nel DB il grafico c'e' lo stesso, senza bande e
    senza effetti; senza Training Effect il riepilogo mostra solo i minuti,
    o sparisce se mancano anche quelli;
  - `records.equiv_speed_kmh` (todo 27) resta: e' la curva della velocita'
    equivalente del grafico nuovo, lisciata a 30 s.

## Colori

| Elemento | Colore |
|---|---|
| Velocita' reale | colore del testo del tema (sul viola il blu si stacca poco) |
| Velocita' equivalente | arancione `#eb6834`, tratteggio 5-3 |
| Salita / discesa | verde `#008300` / rosso `#e34948`, opacita' 0,8 |
| Zone e battiti | viola `rgb(74,58,167)`; bande Z1-Z5 con opacita' 0,03 · 0,10 · 0,22 · 0,40 · 0,56 |
| Battiti per effetto | viola al 50% (basso aerobico), viola pieno (alto aerobico), rosa `#e87ba4` (anaerobico) |

Le zone hanno un solo colore a intensita' crescente perche' verde e rosso
sono gia' della pendenza. Fra una banda e l'altra nessun separatore. Il
grafico deve leggersi anche con il tema scuro di Streamlit: provarlo in
entrambi e schiarire il viola se serve.

## Vincoli

- Nessuna dipendenza nuova: `fitparse` e Altair, niente `fitdecode` e niente
  Chart.js. Niente CSS e niente HTML.
- Commenti in italiano senza accenti, UI in inglese.
- Il crosshair e il tooltip si muovono insieme sui tre pannelli.
- Le altre pagine (Week, Month, Recovery) non cambiano.

## Rischi

- **Cambiano i numeri dei todo 26 e 27.** Con la pendenza nuova la
  velocita' equivalente in tabella e nel grafico Speed si sposta. Riportare
  nel report il prima e dopo su qualche corsa (media e massimo).
- **Il primo avvio rifa' tutta la cache**: circa 19 minuti (todo 26), con
  la pagina che sembra ferma. Una volta sola, da scrivere nel report.
- **File vecchi senza `time_in_zone`** o senza Training Effect: il grafico
  deve funzionare lo stesso, senza bande, effetti o riepilogo.
- **Pendenza sui tratti lenti e ripidi**: dipende molto dalla finestra, e la
  distanza dell'orologio e' trattata come orizzontale. I valori sono una
  stima.
- **Minetti premia troppo le discese**: la curva arancione in discesa sta
  sotto la velocita'. E' il modello, non un errore.
- **Due pannelli, due scale**: velocita' e pendenza non si confrontano in
  altezza, e i battiti non partono da zero.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Corsa del 03/10/2026 (`activity_id` 24588452569), valori attesi dal
   lavoro di riferimento:

   | Grandezza | Valore |
   |---|---|
   | Record | 3.417 |
   | Pausa | dal minuto 15,33 al 19,07 |
   | Intervalli di 30 s | 115 |
   | Bande | Z1 0-1,15 · Z2 1,15-6,70 · Z3 6,70-15,33 · Z2 19,07-21,38 · Z3 21,38-26,22 · Z2 26,22-27,53 · Z3 27,53-29,47 · Z4 29,47-30,53 · Z3 30,53-60,68 |
   | Velocita' reale media sugli intervalli | 7,35 km/h (± qualche decimo) |
   | Velocita' equivalente media / massima | 7,69 / 9,93 km/h |
   | Battiti per intervallo | da 89 a 150 bpm |
   | Basso / alto aerobico / anaerobico | 3.342 s / 75 s / 0 s |
   | Tetti Z1-Z4 / soglia | 106, 121, 141, 157 / 155 |
   | Training Effect | 3,0 aerobico, 0,2 anaerobico |

   Bande, effetti e velocita' equivalente devono coincidere; velocita' e
   pendenza possono differire di qualche decimo.
2. Dopo il rebuild, il conteggio per sport delle attivita' con
   `equiv_speed_kmh` non nullo e' lo stesso di prima (249 corse, 186
   escursioni, 68 camminate).
3. Nella pagina Day non resta nessuno dei sei grafici di prima; la mappa
   c'e' ancora.
4. Un'uscita in bici: tre pannelli, senza la linea della velocita'
   equivalente.
5. Una corsa senza quota (2014-2015): niente pannello della pendenza, niente
   linea equivalente, nessun errore.
6. Un'attivita' di palestra: solo il pannello dei battiti.
7. Una corsa senza `time_in_zone`: grafico senza bande e senza effetti.
8. Tema chiaro e scuro: zone, linee e barre leggibili in entrambi.
9. Le pagine si caricano senza eccezioni (AppTest o server headless).

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_28'$" --format=%H -1)
```

Effetti fuori dal repo: le colonne nuove restano in `activities.db` fino al
prossimo rebuild. Sono innocue: al primo avvio dopo il revert
`LOGIC_VERSION` torna a "6", non combacia con il "7" salvato e `sync()`
ricostruisce la cache da solo (circa 19 minuti), con la pendenza di prima.
