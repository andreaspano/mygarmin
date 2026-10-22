---
status: todo
---

# I numeri della settimana, e i suoi grafici

Il todo 51 ha costruito la pagina Week: intestazione, striscia dei giorni e
le sedute. Mancano i numeri — le quattro card con le loro misure — e i due
grafici della card Training.

## Le fasce: dodici settimane, non ventotto giorni

Il punto che decide tutto il resto. Le barre della Day confrontano il valore
di un giorno con i 28 giorni prima: **attorno a una media settimanale quella
fascia non direbbe niente**, perche' una media di sette giorni oscilla molto
meno di un singolo giorno e cadrebbe quasi sempre dentro.

La settimana ha quindi le sue fasce: **il valore della settimana contro i
valori delle 12 settimane precedenti**. Stesso conto di `_band` in
`daily_data.py` — media piu' e meno uno scarto tipo, e piu' e meno due in
tinta chiara — ma su una serie di dodici numeri settimanali invece che di
ventotto giornalieri.

Dodici settimane sono tre mesi: abbastanza da contenere un blocco di lavoro
intero, abbastanza poche da seguirti se cambi passo. I dati reggono: nelle
12 settimane prima del 19 ottobre la readiness ha 84 giorni misurati su 84,
il battito a riposo 77, il sonno e l'HRV 74.

**Minimo sei settimane misurate**, l'analogo di `MIN_BAND_DAYS`: sotto, la
barra non si disegna e resta il numero.

## Decisioni

Prese con Andrea il 2026-10-22:

| card | cosa mostra | fascia |
|---|---|---|
| Health | **medie**: battito a riposo, HRV, respiro, stress | 12 settimane |
| Recovery | **medie**: readiness, sonno, le due body battery | 12 settimane |
| Load | **fine settimana**: i carichi e il rapporto | bersagli Garmin |
| Fitness | **fine settimana**: punteggi, soglia, acclimatamenti | 12 settimane |

Health e Recovery medie, Load e Fitness finali: il carico e la forma sono
stati di quel momento, non cose da mediare su sette giorni.

## Work

### 1. I dati — `src/training/interface/weekly_data.py`

C'e' gia' quasi tutto: `week`, `days`, `activities`, `training.by_sport`,
`load` (lo stesso blocco del giornaliero), `coverage`, e perfino
`four_weeks`, le quattro settimane precedenti **con le medie di recupero
gia' calcolate**. Serve:

- portare la serie delle settimane precedenti a **dodici**, e ricavarne le
  fasce riusando `_band` di `daily_data` (che dal todo 48 prende anche i
  decimali della misura e dei limiti, utili qui per i punteggi interi);
- le medie settimanali delle quattro misure di Health, che oggi non ci sono
  tutte;
- i valori di fine settimana per Fitness, da `fitness_on` sull'ultimo giorno
  della settimana;
- **i minuti per zona** della settimana.

### 2. I minuti per zona: da scrivere

Oggi sappiamo i minuti per **effetto** (basso aerobico, alto aerobico,
anaerobico) con `run_chart.effects()`, non per **zona**. Il conto si fa con
`zone_of()` sui campioni, che stanno nella tabella `records`, usando le zone
in vigore quel giorno (`run_chart.zone_settings` sulla riga dell'attivita',
che cambiano nel tempo: dall'8 agosto al 20 ottobre la soglia e' passata per
sei valori).

**Costa**: vuol dire rileggere i campioni di tutte le sedute di una
settimana. Una volta a settimana va bene; a ogni apertura della pagina no.
Se la lentezza si vede, il posto giusto per tenerli e' una colonna in
`activities`, con il salto di `LOGIC_VERSION` che ne consegue — ma prima si
misura.

### 3. L'API — `GET /api/weekly/{monday}`

Come `/api/daily/{day}`: un endpoint che rende i fatti della settimana con
le fasce, tipato nei modelli. 422 se il giorno non e' un lunedi, come fa
gia' `build_weekly_data`.

### 4. Le card — `frontend/src/components/WeekPage.tsx`

Health, Recovery, Load e Fitness, **riusando i componenti della Day**:
`Stat`, `RangeBar` e `MeasureBar` stanno gia' in `Stat.tsx` e prendono
valore e fascia senza sapere se vengono da un giorno o da una settimana.

I colori delle barre seguono le icone come nella Day (todo 46-48).

### 5. I due grafici di Training

Due, non uno: tre informazioni in un disegno solo non ci stanno.

1. **Barre per sport**: il tempo e la distanza di ogni sport della
   settimana, con il numero di sedute nell'etichetta. La distanza **salta
   gli sport che non ne hanno** (il tapis roulant, todo 45): li' solo il
   tempo.
2. **La torta delle zone**: quanto tempo in Z1, Z2, Z3, Z4 e Z5 sommando
   tutte le sedute.

Li disegna Altair come il grafico della scheda (`run_chart.py`), e l'API li
rende come specifica Vega-Lite gia' pronta, come fa
`/api/activities/{id}/chart/vega`.

## Vincoli

- Nessuna dipendenza nuova: Altair e Vega-Lite ci sono gia'.
- `_band`, `_window`, `Stat`, `RangeBar` si riusano, non si copiano.
- Niente conti nel frontend: le medie e le fasce le fa l'API, come per la
  Day.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Le fasce a dodici settimane sono poche.** Con sei settimane misurate
  come minimo lo scarto tipo e' ancora rumoroso: le prime barre vanno
  guardate con sospetto.
- **Una settimana a meta' falsa le medie**: la settimana in corso ha tre
  giorni e la sua media non si confronta con dodici settimane piene.
  `build_weekly_data` sa gia' se la settimana e' `partial`: o la fascia non
  si disegna, o lo si dice a schermo.
- **Il tempo per zona sulle sedute in bici**: il profilo Bici non salva la
  soglia e le zone sono calcolate sulla frequenza massima (vedi
  `_fill_missing_thresholds`). Le zone di una pedalata e di una corsa non
  sono la stessa scala, e sommarle in una torta sola va spiegato o evitato.
- **La torta con cinque spicchi** e' il grafico che si legge peggio. Se non
  funziona, una barra unica divisa in cinque dice la stessa cosa meglio.

## Verifica

1. `uv run python -c "from training.interface import weekly_data"` e i fatti
   di una settimana: dodici settimane di storia, nessuna fascia dove le
   settimane misurate sono meno di sei.
2. Le medie di Health e Recovery della settimana contro la media a mano dei
   sette giorni di `days`: stessi numeri.
3. I minuti per zona di una settimana contro la somma dei minuti per effetto
   delle stesse sedute: devono raccontare la stessa storia.
4. La distanza per sport salta il tapis roulant e ne mostra solo il tempo.
5. Quanto ci mette `/api/weekly/{monday}` la prima volta, con i campioni da
   rileggere: se supera il paio di secondi, va detto nel report finale.
6. `make frontend_types` (`schema.ts` cambia una volta e si committa),
   `npm run typecheck`, `npm run build`, e la pagina in Firefox headless nei
   due temi: una settimana piena, una a meta' e una senza dati.
