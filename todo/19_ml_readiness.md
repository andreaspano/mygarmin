---
status: todo
---

# ML: prevedere la readiness di domani, e capire cosa la muove

Con carico, sonno, HRV e FC a riposo di oggi, prevedere la readiness (e l'HRV)
di domattina. Il numero previsto conta poco; conta capire **cosa** pesa sul
recupero: il sonno piu' del carico? Il carico di due giorni fa piu' di quello
di ieri?

E' il primo dei todo di analisi (19-25): crea anche la base comune che gli
altri riusano.

## Dati, verificato

- `health_daily` (todo 16): un giorno per riga dal 2023-01-01, con
  `readiness`, `hrv_last_night`, `hrv_weekly_avg`, `resting_hr`,
  `sleep_hours`, `sleep_score`, `stress_avg`, `body_battery_low/high`,
  `load_acute`, `load_chronic`.
- `activities` + `records`: le sedute dal 2016, con la FC al secondo.
- Il sonno di una data e' la notte che finisce quella mattina.

## Work

- **Pacchetto nuovo** `src/training/analysis/`, con `dataset.py`, la base
  comune dei todo 19-25:
  - `session_trimp(records, hr_rest, hr_max)`: il TRIMP di Banister di una
    seduta dalla FC al secondo (pause oltre 10 s escluse, come nel todo 12);
  - `daily_frame(data_dir) -> DataFrame`: un giorno per riga, dal primo
    giorno con dati di salute, con le colonne di `health_daily` piu'
    `trimp` (somma del giorno, 0 nei giorni senza sedute), `minutes`,
    `sessions`. `hr_rest` e' la mediana di `resting_hr` degli ultimi 30
    giorni, `hr_max` la FC piu' alta registrata nei 12 mesi prima;
  - i TRIMP per seduta si calcolano in SQL o a blocchi, non caricando tutti i
    `records` in memoria.
- `analysis/readiness_model.py`:
  - obiettivo: `readiness` del giorno dopo (e, con la stessa funzione,
    `hrv_last_night` del giorno dopo);
  - variabili: TRIMP di oggi e dei 2-3 giorni prima, carico dei 7 e 28
    giorni, sonno (ore e punteggio), HRV e FC a riposo di oggi, stress, giorno
    della settimana;
  - modello: `HistGradientBoostingRegressor` di scikit-learn (accetta i
    valori mancanti), piu' una regressione lineare per confronto;
  - validazione **temporale** (`TimeSeriesSplit`), mai mescolando passato e
    futuro; confronto con la previsione ingenua "domani come oggi";
  - importanza delle variabili con `permutation_importance`.
- CLI `training-readiness-model` e target `make readiness_model`: stampa
  l'errore (MAE) del modello e della previsione ingenua, e le variabili in
  ordine di importanza; salva un report breve in
  `summary/06.analysis/readiness.md` (in inglese, per l'atleta: cosa pesa sul
  recupero, con parole semplici).
- **Dipendenza nuova**: `scikit-learn` (via `uv add`).

## Vincoli

- Niente chiamate a Garmin: solo dati locali.
- Niente pagine nuove nell'app: la visualizzazione e' un todo a parte.
- `random_state` fisso: due giri danno gli stessi numeri.
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Pochi dati**: circa 1.370 giorni, meno quelli senza orologio. Un modello
  complesso impara il rumore: per questo il confronto con la previsione
  ingenua e' obbligatorio. Se il modello non la batte, lo si dice.
- **La readiness di Garmin e' gia' un modello** (usa sonno, HRV, carico):
  prevederla in parte vuol dire ricostruire la sua formula. L'HRV, che e' una
  misura, e' l'obiettivo piu' onesto: vanno fatti tutti e due.
- **Cambi di orologio**: HRV e readiness non esistono per tutti i modelli; i
  periodi senza restano fuori, non diventano zero.

## Verifica

1. `daily_frame()`: un giorno per riga, nessun buco nel calendario, TRIMP 0
   nei giorni senza sedute e mai negativo.
2. Una seduta a mano: il suo TRIMP ricalcolato a parte coincide.
3. `make readiness_model` due volte: stessi numeri.
4. Il report dice se il modello batte la previsione ingenua, con i due MAE.
5. Nessun giorno futuro nelle variabili di un giorno (controllo sulle date
   delle colonne ritardate).
