---
status: todo
---

# La settimana, nella forma della Day

Il report della settimana oggi e' un'altra cosa rispetto a quello del
giorno: tre sezioni (Training, Recovery, Trend) scritte da un agente solo in
`summary/02.weekly/<lunedi>.md`, e **nessuna pagina** — la barra in alto
elenca Week, ma l'unica pagina costruita e' Day (todo 40). Di settimanali ne
esistono tre in tutto.

La Day invece ha otto sezioni, un agente ciascuna, le card con le barre e i
due giri al giorno. La settimana deve ricalcare quella forma: stesse card,
stesso impianto, stessi tasti.

**La settimana e' ISO 8601**: comincia il lunedi e finisce la domenica.
Titolo `Week 43 · October 2026` — il numero della settimana ISO, e il mese
**del giovedi**, che e' la regola ISO per decidere a chi appartiene una
settimana a cavallo di due mesi.

## Le fasce: dodici settimane, non ventotto giorni

Il nodo che il primo abbozzo non risolveva. Le barre della Day confrontano
il valore di un giorno con i 28 giorni prima: **attorno a una media
settimanale quella fascia non direbbe niente**, perche' una media di sette
giorni oscilla molto meno di un singolo giorno e cadrebbe quasi sempre
dentro.

Quindi la settimana ha le sue fasce: **il valore della settimana contro i
valori delle 12 settimane precedenti**, stesso conto di `_band` (media piu'
e meno uno scarto tipo, e piu' e meno due in tinta chiara) ma su una serie
di dodici numeri settimanali invece che di ventotto giornalieri.

Dodici settimane sono tre mesi: abbastanza da contenere un blocco di lavoro
intero, abbastanza poche da seguirti se cambi passo. I dati ci sono: nelle
12 settimane prima del 19 ottobre la readiness ha 84 giorni misurati su 84,
il battito a riposo 77, il sonno e l'HRV 74.

**Minimo sei settimane misurate**, l'analogo di `MIN_BAND_DAYS`: sotto, la
barra non si disegna e resta il numero.

## Le card

Come la Day, con la stessa regola di lettura delle barre.

| card | cosa mostra | fascia |
|---|---|---|
| Health | **medie**: battito a riposo, HRV, respiro, stress | 12 settimane |
| Recovery | **medie**: readiness, sonno, le due body battery | 12 settimane |
| Load | **fine settimana**: i tre carichi e il rapporto | i bersagli di Garmin |
| Fitness | **fine settimana**: i tre punteggi, soglia, acclimatamenti | 12 settimane (i punteggi) |
| Training | nessun numero grande: i grafici qui sotto | — |
| Next | gli allenamenti per la settimana **dopo** | — |
| Summary | **uno solo**: com'e' andata la settimana | — |

Health e Recovery medie, Load e Fitness finali: il carico e la forma sono
stati, non cose da mediare.

## I grafici di Training

Due, non uno: tre informazioni in un disegno solo non ci stanno.

1. **Barre per sport**, due misure affiancate: il tempo e la distanza di
   ogni sport della settimana, con il numero di sedute nell'etichetta.
   La distanza **salta gli sport che non ne hanno** (il tapis roulant, todo
   45): li' si mostra solo il tempo.
2. **La torta delle zone**: quanto tempo in Z1, Z2, Z3, Z4, Z5 sommando
   tutte le sedute della settimana.

Il tempo per zona **non esiste ancora**: oggi sappiamo i minuti per
*effetto* (basso aerobico, alto aerobico, anaerobico) con
`run_chart.effects()`, non per zona. Il conto si fa con `zone_of()` sui
campioni, che sono in `records`, usando le zone in vigore quel giorno
(`zone_settings`); va scritto e va fatto una volta per settimana, non a ogni
apertura della pagina.

## Work

### 1. I dati — `src/training/interface/weekly_data.py`

C'e' gia' quasi tutto: `week`, `days`, `activities`, `training.by_sport`,
`load` (identico a quello giornaliero), `coverage` e perfino `four_weeks`,
le quattro settimane precedenti con le medie di recupero. Serve:

- portare `four_weeks` a **dodici** (o affiancargliene una versione lunga) e
  ricavarne le fasce con `_band` di `daily_data`;
- le medie settimanali delle misure di Health, che oggi non ci sono tutte;
- i valori di fine settimana per Fitness, da `fitness_on` sull'ultimo giorno
  della settimana;
- i minuti per zona della settimana.

### 2. L'API — `src/training/api/`

- `GET /api/weekly/{monday}` con i fatti della settimana, come
  `/api/daily/{day}`;
- `GET /api/reports/weekly/{monday}` che compone le sezioni dai frammenti;
- il refresh, intero e per sezione, come per il giorno;
- un registro `WEEK_SECTIONS` accanto a `SECTIONS`: sette sezioni, sette
  agenti.

### 3. Gli agenti — `.claude/agents/`

Sette prompt nuovi (`w1_health` … `w7_summary`), perche' quelli del giorno
sono scritti sul giorno e non si possono riusare. Ereditano `_style.md`, con
l'aggiunta della regola delle fasce a dodici settimane.

L'agente `weekly-report` e il formato a tre sezioni **spariscono**, come e'
sparito `fitness-status` col todo 44. I tre file gia' scritti in
`summary/02.weekly/` restano dove sono.

### 4. La pagina — `frontend/src/`

La prima pagina oltre la Day: serve il routing (oggi la Day legge il giorno
dall'URL e basta), una `WeekPage` che riusa le card esistenti, e la striscia
in alto che diventa una scelta di settimane.

### 5. Quando si scrive

Il **lunedi mattina**, per la settimana appena chiusa, agganciato al giro
delle 10: sette agenti una volta a settimana. La settimana in corso mostra i
numeri, che sono sempre freschi, e al posto del testo il tasto per
scriverlo.

## Vincoli

- Nessuna dipendenza nuova.
- Non si scrive in `summary/` a mano.
- `make update_activity` non si chiama: il settimanale usa i dati che ci
  sono.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **E' grande.** Dati, API, sette prompt, una pagina nuova e due grafici: e'
  il lavoro piu' esteso dal todo 44. Conviene spezzarlo — 51 i dati e il
  report, 52 la pagina — e la prima meta' si prova da terminale senza che la
  pagina esista.
- **Le fasce a dodici settimane sono poche.** Con sei settimane misurate
  come minimo, lo scarto tipo e' ancora rumoroso: le prime barre andranno
  guardate con sospetto.
- **Il tempo per zona costa**: rileggere i campioni di tutte le sedute di
  una settimana. Una volta a settimana va bene, a ogni apertura della pagina
  no.
- **Sette agenti a settimana** sono pochi in confronto agli undici al
  giorno, ma vanno aggiunti al giro del lunedi, che diventa il piu' lungo.

## Verifica

1. `uv run python -c "from training.interface import weekly_data"`, e i
   fatti di una settimana con le fasce: dodici settimane di storia, nessuna
   fascia dove le settimane misurate sono meno di sei.
2. Il numero e il titolo ISO su una settimana a cavallo di due mesi
   (26 gennaio - 1 febbraio 2026 e' la settimana 5, mese **gennaio** per via
   del giovedi).
3. I minuti per zona di una settimana contro la somma a mano dei minuti per
   effetto delle stesse sedute: devono raccontare la stessa storia.
4. La distanza per sport salta il tapis roulant e ne mostra solo il tempo.
5. Un report settimanale scritto da terminale, prima che la pagina esista.
6. `make frontend_types`, `npm run typecheck`, `npm run build`, e la pagina
   in Firefox headless nei due temi.
