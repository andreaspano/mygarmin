---
status: todo
---

# Lo storico nella forma nuova: dal 1 agosto a oggi

Dal todo 44 il report e' fatto di sezioni, una per card, e da allora le card
sono cambiate molto: Fitness ha un testo e le barre, Load ha le soglie di
Garmin, il verdetto del giorno e' in due pezzi, e i prompt sono stati
riscritti per parlare di oggi invece che del trend.

Ma **quasi tutto lo storico e' fermo alla forma vecchia**. Degli 82 giorni
fra il 1 agosto e il 21 ottobre:

- **77** hanno il report a file unico con cinque sezioni — Training,
  Recovery, Health, Load, Next. Niente Fitness, niente Summary.
- **3** sono gia' a sezioni (15, 20 e 21 ottobre).
- **5** non hanno niente (1-4 agosto e 12 ottobre).

Aprire un giorno di settembre oggi vuol dire vedere due card senza testo e
tre scritte con regole che non valgono piu'.

## Decisioni

Prese con Andrea il 2026-10-21:

- **Tutte e otto le sezioni** per ogni giorno, Next e sole compresi: lo
  storico diventa identico a oggi. Il sole non e' un consiglio ma una
  fotografia — "quella mattina stavi bene" — quindi regge anche a
  posteriori, e Next lo avevano gia' i report vecchi.
- **Tutti i giorni**, i 33 di riposo compresi: hanno salute, recupero,
  carico e forma, e sono i giorni in cui la card Training dice "Rest day" e
  le altre quattro raccontano come stavi.

**Circa 630 agenti, cinque ore in fila.** E' il costo, ed e' il motivo per
cui il comando dev'essere interrompibile e ripetibile.

## Work

### 1. Il comando — `src/training/api/refresh.py`

`training-daily-report` guadagna `--from GIORNO` (e `--to`, di default
oggi), che cicla sull'intervallo invece di fare un giorno solo.

**Tre giri per giorno, non uno**, perche' il momento non e' lo stesso per
tutte le sezioni:

| giro | momento | sezioni |
|---|---|---|
| 1 | evening | health, recovery, load, fitness, training, next |
| 2 | morning | summary_morning |
| 3 | evening | summary_evening |

Otto agenti in tutto, nessuno sprecato. L'ordine conta per due ragioni: i
verdetti leggono i frammenti delle card, e **la luna legge il sole** (todo
49), quindi il sole va scritto prima di lei.

Perche' `evening` per Next: su un giorno finito il consiglio e' per il
giorno dopo, ed e' quello che dicevano i report vecchi ("Tomorrow, ...").

**Salta le sezioni che esistono gia'**, non i giorni: cosi' un backfill
interrotto riprende esattamente da dove si era fermato, e rilanciarlo su un
periodo gia' fatto non costa niente. Per rifare un giorno da capo restano
`--day` e `--section`.

**Niente scaricamento**: `--from` impone `update=False`. I dati storici sono
gia' su disco, e 79 chiamate a Garmin sarebbero sbagliate. Se manca
qualcosa e' `make backfill` il posto giusto, e lo lancia Andrea.

**Se il lock e' occupato il ciclo si ferma** e lo dice: il giro delle 22 ha
la precedenza, e il backfill si rilancia dopo. Stampa un riepilogo — giorni
fatti, sezioni saltate perche' c'erano gia', sezioni fallite.

### 2. Il Makefile

```makefile
make backfill_reports FROM=2026-08-01        # TO di default oggi
```

Con un avviso in testa al target: sono ore di agenti, e si lancia quando non
c'e' altro in corso.

### 3. Quello che non va toccato

I 77 file unici `summary/01.daily/<giorno>.md` **restano dove sono**. Appena
la cartella di un giorno esiste, l'API compone da li' e il file unico non si
legge piu' (`app.get_daily_report`), ma resta come copia di sicurezza: se il
backfill va storto, basta cancellare le cartelle nuove per riavere tutto.
Cancellarli e' una decisione successiva, e non e' di questo lavoro.

## Vincoli

- Nessuna dipendenza nuova; il modello dell'API non cambia.
- `make update_activity` non si chiama mai, nemmeno indirettamente.
- Non si scrive in `summary/` a mano: ci scrivono solo gli agenti.
- **Il backfill completo non lo lancia il todo**: sono cinque ore. Il todo
  implementa il comando e fa la prova di una settimana; il resto lo lancia
  Andrea quando gli fa comodo.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Il giro delle 22 e il backfill si contendono il lock.** Chi arriva
  secondo si ferma. Va lanciato quando non c'e' altro in corso, e in caso
  rilanciato.
- **I dati di agosto sono piu' poveri**: niente endurance score, niente hill
  score, nessuna soglia del lattato (verificato sul 5 agosto). Le card
  mostreranno dei trattini e gli agenti devono dirlo invece di inventare —
  le regole ci sono gia', ma su una stagione intera qualche riga storta e'
  probabile.
- **Alcuni giorni avranno testi quasi identici**: in un periodo di carico
  piatto le sezioni Load e Fitness hanno poco da dire. E' il rischio gia'
  noto dei prompt riscritti, qui moltiplicato per settantanove.

## Verifica

1. `uv run python -c "from training.api import refresh"`.
2. **Una settimana per prova**: `make backfill_reports FROM=2026-09-01
   TO=2026-09-07` — sette giorni, 56 agenti, una ventina di minuti. Ogni
   cartella deve avere otto file, il sole e la luna devono essere diversi
   fra loro, e Next deve parlare del giorno dopo.
3. Rilanciare lo stesso comando: deve saltare tutto e finire in un secondo.
4. La pagina di uno di quei giorni in Firefox headless: otto sezioni al loro
   posto, le barre, le due parti del Summary, nessun errore in console.
5. Un giorno di riposo e un giorno con allenamento, per vedere che la card
   Training si comporta nei due modi.
6. Il periodo intero **non** si lancia: si lascia ad Andrea.
