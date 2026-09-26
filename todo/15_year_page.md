---
status: todo
---

# Year: una pagina annuale speculare a Week e Month

Dopo il todo 09 la macchina di Week e Month sta in `period_page.py`, e ogni
pagina e' solo una `PeriodSpec`. Una pagina **Year** costa quindi poco:
un'altra `PeriodSpec`, piu' due punti in cui il codice condiviso da' per
scontato qualcosa che per l'anno non vale.

**Da sapere prima di partire**: le attivita' vanno da gennaio 2025 a settembre
2026, quindi **oggi gli anni sono due**. La tabella dei totali e le schede per
sport servono gia' ("quanto ho corso nel 2025 contro il 2026"). I grafici a due
punti servono poco, e se valga la pena mostrarli e' una decisione del todo (vedi
Rischi).

## Work

- `app_pages/year.py` con `YEAR = PeriodSpec(...)`, sul modello di `month.py`:
  - `bucket`: `start_time.dt.to_period("Y").dt.start_time`;
  - `bucket_end`: `starts + pd.offsets.YearEnd(0)`;
  - `freq="YS"`, `label` "2025", `axis_format="%Y"`, `axis_interval="year"`;
  - `column_header="Year"`, `column_format="YYYY"`.
- **Annotazioni.** Sopra l'anno non c'e' un livello da disegnare. Oggi
  `boundary_freq` e `boundary_format` sono `str` obbligatori, e
  `_boundary_layers()` li usa senza controlli (`pd.date_range(...,
  freq=spec.boundary_freq)`). Vanno resi opzionali (`str | None`), e con `None`
  `_boundary_layers()` non disegna niente. Week e Month non devono cambiare.
- **Scorciatoie.** `filters._PRESET_SETS` ha solo `"weeks"` e `"months"`, e
  `_preset_range()` sceglie fra `timedelta(weeks=)` e `DateOffset(months=)` con
  un `if` a due rami. Aggiungere `"years"` (per esempio `{"3 years": 3,
  "All": None}`, default "All"), e il ramo `DateOffset(years=)`.
- Voce **Year** nella navigazione di `app.py` dopo Month, icona
  `:material/calendar_today:`.
- Il `name` della spec (`"year"`) fa da prefisso alle chiavi di sessione: basta
  che sia diverso da `"week"` e `"month"` perche' le tre pagine non si pestino.

## Vincoli

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Se per l'anno servisse una condizione dentro `period_page.py` del tipo "se
  e' l'anno fai cosi'", e' il segnale che manca un campo in `PeriodSpec`:
  aggiungere il campo, non la condizione (vedi la docstring di `PeriodSpec`).
- Week e Month devono restare identiche, anche nei grafici.

## Rischi

- **Due punti per grafico.** Con due anni le linee e le aree del grafico
  cumulato sono un segmento. Due opzioni: (a) lasciarli, e diventeranno utili
  con gli anni; (b) una soglia in `PeriodSpec` (`min_chart_periods`) sotto la
  quale la sezione dei grafici non compare. La (b) e' un campo generico, non
  una condizione sull'anno. Scegliere e scriverlo nel commento.
- Il 2026 e' un anno in corso: il confronto con il 2025 intero e' ingannevole.
  Aggiungere alla tabella l'help "Current year: partial". Uno "stesso periodo
  dell'anno scorso" sarebbe utile, ma e' un altro todo.
- Le barre di un grafico con `axis_interval="year"` possono uscire molto
  larghe: controllare nel browser.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. La tabella ha due righe, 2025 e 2026. La somma dei km di corsa del 2025 e'
   uguale alla somma dei mesi del 2025 nella pagina Month.
2. Scegliere il 2025 nella tabella aggiorna le schede per sport e l'elenco
   delle attivita'.
3. Week e Month sono identiche a prima: stessi grafici, stesse annotazioni dei
   mesi e degli anni, stesse scorciatoie.
4. Nei grafici della Year non ci sono annotazioni e non ci sono eccezioni.
5. `AppTest` su tutte le pagine piu' un giro nel browser, a 1440px con la
   sidebar aperta.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
