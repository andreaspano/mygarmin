---
status: done
---

# Pagina Day: tabella delle attivita' piu' stretta

Nella pagina **Day** (`app_pages/activities.py`) la tabella delle attivita'
occupa tutta la larghezza della pagina e ha nove colonne: icona, ID, Date,
Name, Sport, km, Min, D+, Eq km/h. Sotto, la scheda di dettaglio sta in un
riquadro largo tre quinti della pagina. Per scelta di Andrea:

- via le colonne **ID**, **Sport** e **Eq km/h**. Lo sport lo dice gia'
  l'icona; l'ID a chi legge non dice niente; la velocita' equivalente sta nel
  grafico della scheda (todo 28);
- la tabella diventa larga quanto il riquadro della scheda sotto di lei.

La tabella e' la stessa delle pagine Week e Month (`activity_table.py`):
le tre colonne spariscono anche li', sempre per scelta di Andrea, cosi' le
tabelle restano uguali dappertutto. La larghezza cambia solo nella Day,
l'unica pagina con il riquadro sotto.

## Work

- **`activity_table.py`**:
  - togliere `activity_id`, `sport` e `equiv_speed_kmh` da
    `ACTIVITY_COLUMNS` e le loro voci da `ACTIVITY_COLUMN_CONFIG`;
  - aggiornare il commento sopra `ACTIVITY_COLUMNS`, che cita ancora la
    velocita' equivalente del todo 26 come colonna voluta: ora le colonne
    sono icona, data, nome, distanza, durata e dislivello, e il perche' delle
    tre tolte (vedi sopra);
  - in `activity_table()` la conversione di `sport` con `sport_label` serviva
    solo alla colonna Sport: va tolta. I dati restano con le chiavi degli
    sport, che servono ai filtri e all'icona.
- **`app_pages/activities.py`**: didascalia "Click a row to see the details."
  e tabella dentro la prima di due colonne `st.columns([3, 2])`, le stesse
  proporzioni del riquadro di `activity_detail.show_activity_detail`, cosi'
  la tabella ha esattamente la sua larghezza. La seconda colonna resta vuota.
- Niente cambia nei dati: `equiv_speed_kmh` resta in `activities.db` e nel
  dataframe, perche' la usano il grafico della scheda e le pagine Week e
  Month.

## Vincoli

- Nessuna dipendenza nuova.
- Commenti in italiano senza accenti, UI in inglese.
- Week e Month perdono le stesse tre colonne e per il resto non cambiano.
- Selezionare una riga apre ancora la scheda, nella Day come nella Week e
  nella Month; alla prima apertura della Day la prima riga e' gia'
  selezionata come oggi.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Import: `uv run python -c "from training.interface import activity_table, activity_detail"`.
2. AppTest di `app_pages/activities.py`, `week.py` e `month.py`: nessuna
   eccezione, e la tabella ha le colonne icona, Date, Name, km, Min, D+.
3. Server headless (`streamlit run ... --server.headless true`): parte
   senza traceback. Se il browser e' disponibile, a 1440 px tabella e
   riquadro della scheda hanno gli stessi bordi a sinistra e a destra.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_29'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_29` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
