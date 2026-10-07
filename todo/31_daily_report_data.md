---
status: todo
---

# Report giornaliero: i numeri da uno script, il testo dall'agente

Il report giornaliero (`summary/01.daily/<data>.md`) lo scrive l'agente
`.claude/agents/fitness-status.md`, partendo da `training-fitness-status`
(`src/training/garmin/fitness_status.py`, `make fitness_status`). Il
problema e' quello che l'agente riceve:

- **Troppi dati grezzi.** Lo snapshot sono i JSON di Garmin dei 14 giorni,
  circa 2,3 milioni di caratteri (~585.000 token; il solo `sleep` ~400.000).
  Il modello non li puo' leggere tutti: se li estrae da solo con script
  improvvisati, e quali numeri finiscono nel report cambia da un giorno
  all'altro.
- **I conti li fa il modello.** Medie, conteggi e confronti sono calcolati
  dal modello sui dati grezzi: un errore e' facile e non si vede. Il report
  settimanale ha gia' la soluzione giusta: `weekly_data.py` prepara i numeri,
  l'agente `weekly-report` scrive il testo.
- **Ignora il database.** `activities.db` ha gia' tutto pulito: in
  `health_daily` FC a riposo, HRV, respirazione nel sonno, sonno, stress,
  body battery, carico e readiness; in `activities` Training Effect e zone
  (todo 28), con i minuti per effetto calcolati da `run_chart.effects`.
- **E' un riassunto di 14 giorni, non un report del giorno.** Manca l'analisi
  della seduta di ieri e un consiglio chiaro per oggi; il primo paragrafo
  elenca tutte le uscite delle due settimane.
- **14 giorni sono pochi per una base di confronto**: un allarme su FC a
  riposo o respirazione ha senso contro ~28 giorni.

Qui si copia l'impianto del settimanale: uno script `daily_data.py` che
produce un JSON piccolo da soli dati locali, e l'agente riscritto per
leggere solo quello.

## Decisioni

- **Solo dati locali nello script**, come `weekly_data.py`: nessuna chiamata
  a Garmin. I dati freschi li porta `make update_activity` (attivita' e
  salute degli ultimi tre giorni, oggi compreso), che l'agente lancia per
  primo.
- **Base di confronto: 7 e 28 giorni** prima del giorno del report (esclusi
  i giorni senza dato), con quanti giorni ci sono dentro, come fa
  `weekly_data.py` ("ogni media dice su quanti giorni e' fatta").
- **Gli allarmi li calcola lo script**, con soglie scritte nel codice, e il
  modello li racconta: FC a riposo di 3+ bpm sopra la media di 28 giorni per
  2+ giorni di fila; respirazione nel sonno di 1+ atti/min sopra la media di
  28 giorni; HRV media settimanale sotto il minimo del baseline Garmin; 3+
  notti sotto le 7 h negli ultimi 7 giorni.
- **Il report del giorno D parla di**: la mattina di D (readiness, notte
  appena passata), la seduta del giorno prima (o il riposo), le eventuali
  attivita' di D gia' fatte, e un consiglio per D.
- **`fitness_status.py` e `make fitness_status` restano** come sono:
  l'agente non li usa piu', ma toglierli e' un'altra scelta.
- **Il nome dell'agente resta `fitness-status`** (si chiama gia' cosi'
  nelle richieste), ma il titolo del report diventa
  `# Daily report — <YYYY-MM-DD>`.

## Work

- **`src/training/interface/daily_data.py`** (nuovo), sul modello di
  `weekly_data.py` (stesse convenzioni: `None` e mai `0` per una media su
  zero giorni, numeri arrotondati, progressi su stderr). Argomento
  `--day YYYY-MM-DD`, di default oggi. Legge `load_health_db` e
  `list_activities`/`load_activity_records`. Il JSON ha:
  - `day`;
  - `morning`: per readiness, FC a riposo, HRV della notte, HRV media
    settimanale e stato, respirazione nel sonno, ore e punteggio del sonno,
    stress medio del giorno prima, body battery (massimo e minimo), SpO2:
    il valore di D, la media e il numero di giorni a 7 e a 28 giorni, la
    differenza dalla media a 28;
  - `sleep_last_7`: ore notte per notte e quante sotto le 7 h;
  - `alerts`: la lista degli allarmi accesi (vedi Decisioni), ognuno con il
    suo numero;
  - `load`: carico acuto e cronico, rapporto e suo stato, training status,
    bilancio del carico (le tre voci e la frase di Garmin), di D e di 7
    giorni prima per dire la direzione; VO2max solo se in 28 giorni e'
    cambiato di 0,5 o piu';
  - `sessions`: le attivita' del giorno prima e quelle di D gia' fatte. Per
    ognuna: nome, sport, ora, distanza, durata, dislivello, FC media e
    massima, Training Effect aerobico e anaerobico, velocita' equivalente
    se c'e', e i minuti per effetto (`run_chart.effects`, con
    `has_effects`) se ci sono zone e soglia;
  - `recent`: giorni dall'ultima attivita', giorni dall'ultima seduta
    impegnativa (10+ minuti sopra il tetto di Z3), giorni di riposo negli
    ultimi 7, e le attivita' dei 14 giorni in una riga ciascuna (data,
    sport, km, minuti, Training Effect);
  - `missing`: le misure che mancano in D.
- **`pyproject.toml`**: entry point `training-daily-data`.
- **`Makefile`**: target `daily_data` con `DAY=` facoltativo, come
  `weekly_data` con `WEEK=`.
- **`.claude/agents/fitness-status.md`** riscritto sul modello di
  `weekly-report.md`:
  - Step 1: `make update_activity`, poi `make daily_data` (con `DAY=` se si
    chiede un altro giorno); se il primo fallisce (rete, login), si va
    avanti con i dati locali e lo si dice nel report;
  - Step 2: cinque paragrafi brevi, ognuno con la sua etichetta in
    grassetto, in quest'ordine: **Yesterday.** (la seduta o il riposo, i
    minuti per effetto, cosa ha allenato), **Recovery.** (readiness e cosa
    la muove), **Health.** (quello aggiunto oggi: FC a riposo, HRV,
    respirazione, sonno, stress e body battery, SpO2, contro la propria
    base; "no warning signs" se niente si muove), **Load.** (rapporto,
    bilancio, VO2max solo se cambia), **Today.** (un consiglio concreto:
    seduta impegnativa, facile o riposo, con il perche' e un esempio di
    seduta). Ogni numero viene dal JSON: il modello non calcola niente.
    Al massimo ~80 parole per paragrafo;
  - Step 3: come oggi (un file per giorno, sovrascritto), con il titolo
    nuovo e la riga `Data: local cache, health up to <ultimo giorno>`.
- **Il report nella pagina Day**, a destra (scelta di Andrea), come il report
  settimanale nella Week:
  - in `app_pages/activities.py` la seconda colonna accanto alla tabella
    (`st.columns([3, 2])`, oggi vuota) mostra il report del giorno della
    riga selezionata: `summary/01.daily/<YYYY-MM-DD>.md`. Anche una riga
    vuota (giorno senza attivita', todo 30) ha il suo report: il riposo e'
    proprio il giorno in cui serve;
  - stesso aspetto del report settimanale: riquadro grigio chiaro, altezza
    fissa uguale a quella della tabella (che prende un'altezza esplicita
    per questo), testo che scorre dentro. La parte di
    `period_page._show_report` che legge il file e disegna il riquadro
    diventa una funzione condivisa (es. in un modulo `report_view.py`),
    usata da Week, Month e Day, invece di una copia;
  - del file si tolgono il titolo `# ...` e le righe `Window: ...` e
    `Data: ...`, che ripetono quello che la pagina dice gia'. Vale anche per
    i report vecchi (formato "Fitness status" con `## Summary`), che si
    mostrano cosi' come sono;
  - senza file per quel giorno: una riga "No daily report for this day."
    al posto del riquadro;
  - il file letto e' solo quello con il nome esatto del giorno: file come
    `2026-10-01_since-2026-08-01.md` non si mostrano.

## Vincoli

- Nessuna dipendenza nuova.
- Commenti in italiano senza accenti; il report e la UI in inglese.
- Il JSON di un giorno resta piccolo: sotto i 20.000 caratteri.
- Nessuna chiamata a Garmin da `daily_data.py`.
- Il report settimanale nella Week e nella Month si vede come prima; per il resto le pagine non cambiano, a parte la colonna destra della Day.

## Verifica

Non esiste una suite di test; non si lancia `make update_activity` (e' di
Andrea) e non si scrive in `summary/`.

1. Import di `training` e di `daily_data`; `make daily_data` e
   `make daily_data DAY=2026-10-07` girano senza errori.
2. `DAY=2026-10-07`:
   - `sessions`: niente il 06/10 (riposo), e la corsa "Canegrate - Rip_3x5"
     del 07/10 alle 12:28 con 31,4 / 14,3 / 0,5 minuti per effetto e
     Training Effect 3,5 / 0,4;
   - `recent`: l'ultima attivita' prima di D e' il 04/10;
   - i valori di `morning` coincidono con `health_daily` del 07/10, e le
     medie a 7 e 28 giorni con una query a mano sulla tabella.
3. Un giorno senza dati di salute (es. `DAY=2021-06-01`, nel buco
   2020-2022): nessun errore, le misure in `missing`, medie `null`.
4. Dimensione del JSON sotto i 20.000 caratteri.
5. L'agente: il file e' coerente con lo script (comandi, chiavi del JSON,
   cinque etichette). Non lo si lancia: scriverebbe in `summary/`.
6. AppTest della Day con il 07/10 selezionato: a destra il report di
   `summary/01.daily/2026-10-07.md` senza titolo ne' riga `Window:`; con il
   06/10 (riga vuota) nessun report e la riga "No daily report for this
   day."; con il 05/10 il report di quel giorno.
7. AppTest di Week e Month: il report settimanale si vede come prima.
8. Server headless: parte senza traceback.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_31'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno (i report gia' scritti in
`summary/01.daily/` restano come sono).

Dopo il revert, rifare il merge di `todo_31` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
