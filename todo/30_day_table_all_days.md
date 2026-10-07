---
status: todo
---

# Pagina Day: una riga per ogni giorno, anche senza attivita'

Nella pagina **Day** (`app_pages/activities.py`) la tabella ha una riga per
attivita': i giorni senza allenamento non compaiono, e dalla tabella non si
vede quanti giorni di riposo ci sono stati fra un'uscita e l'altra. Per
scelta di Andrea la tabella deve contenere **tutti i giorni** dell'intervallo
scelto con i filtri: un giorno senza attivita' ha una riga vuota, con solo la
data.

## Decisioni

- **Una riga per attivita', piu' una riga vuota per ogni giorno senza.** Un
  giorno con due attivita' (es. corsa e camminata il 02/10/2026) resta su due
  righe, come oggi.
- **Fino a oggi.** Oggi il "To" del filtro si ferma all'ultima attivita':
  nella Day arriva invece fino alla data di oggi, cosi' i giorni di riposo
  piu' recenti si vedono (stesso principio della settimana corrente nella
  Week). La Week, la Month e la Recovery non cambiano.
- **Data e ora separate.** Una riga vuota con "7 Oct 2026, 00:00" farebbe
  pensare a un'attivita' a mezzanotte. La colonna **Date** mostra solo il
  giorno, con il giorno della settimana ("Wed 7 Oct 2026"), e l'ora va in una
  colonna nuova **Time** ("12:28"), vuota nelle righe senza attivita'. La
  tabella e' condivisa (`activity_table.py`): il cambio vale anche per Week
  e Month, che restano uguali alla Day come dal todo 29, ma senza righe
  vuote.
- **Filtro per sport.** Con uno sport scelto, i giorni senza attivita' di
  quello sport sono righe vuote: la tabella dice quando si e' fatto quello
  sport e quando no.
- **Selezione.** Alla prima apertura (e a ogni cambio di filtro) e'
  selezionata la riga dell'attivita' piu' recente, non la prima riga, che
  sarebbe spesso un giorno vuoto. Cliccando una riga vuota, sotto la tabella
  compare "No activity on this day." al posto della scheda.

## Work

- **`filters.py`**: `date_range` prende un parametro opzionale (es.
  `latest: date | None`) che alza il massimo dei due calendari e il valore di
  partenza di "To" fino a quella data. Senza, il comportamento e' quello di
  oggi: le altre pagine non lo passano.
- **`activity_table.py`**:
  - una funzione che, dalle attivita' filtrate e dall'intervallo, costruisce
    le righe della Day: le attivita' piu' una riga vuota per ogni giorno
    senza, ordinate dalla piu' recente. Le righe vuote hanno la data e
    nient'altro (niente icona, nome, numeri);
  - colonne `day` (Date, solo giorno con giorno della settimana) e `time`
    (Time) al posto di `start_time` in `ACTIVITY_COLUMNS` e
    `ACTIVITY_COLUMN_CONFIG`, calcolate in `activity_table()` dalla
    `start_time` dove c'e'.
- **`app_pages/activities.py`**: passa `latest=` oggi a `date_range`, usa la
  funzione sopra per le righe, preseleziona la riga dell'attivita' piu'
  recente, e per una riga vuota mostra il messaggio invece di
  `show_activity_detail`.

## Vincoli

- Nessuna dipendenza nuova.
- Commenti in italiano senza accenti, UI in inglese.
- Nessun cambio ai dati: le righe vuote esistono solo nella tabella.
- Week e Month: stessa tabella con Date e Time separati, nessuna riga vuota,
  la selezione apre la scheda come oggi.
- Con tutto lo storico (dal 16/11/2014) sono circa 4.300 righe: la pagina
  deve restare reattiva.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Import di `training`, `filters`, `activity_table` e della pagina.
2. AppTest della Day con "From" 28/09/2026 e "To" 07/10/2026: 11 righe (10
   giorni, piu' una per la seconda attivita' del 02/10); vuote il 28/09, il
   01/10, il 05/10 e il 06/10; selezionata di partenza la corsa del 07/10.
3. Stesso intervallo con il filtro "Cycling": una riga per ogni giorno, tutte
   vuote tranne quelle con un'uscita in bici.
4. Selezionando una riga vuota: il messaggio, nessuna eccezione.
5. AppTest di Week e Month: nessuna eccezione, nessuna riga vuota, colonne
   Date e Time.
6. Server headless: parte senza traceback.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_30'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_30` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
