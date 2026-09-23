---
status: todo
---

# Month: una pagina mensile speculare alla Week

L'app ha tre pagine: Profile, Day, Week. La Week risponde bene a "come e'
andata questa settimana", ma non a "come sta andando l'anno": con "All" il
grafico mette 55 punti settimanali in 355px, e il volume di un mese si legge
solo sommando a mente quattro o cinque righe della tabella.

Qui si aggiunge una pagina **Month** che e' la stessa cosa con un'unita' piu'
larga: stessa disposizione (tabella dei totali, schede per sport, elenco
attivita', grafici in fondo), stessi comandi, stesso aspetto. Solo il periodo
cambia.

**Non si fa copiando `week.py`.** Quel file e' 1.020 righe, il 42% di tutta
l'interfaccia, ma solo 80-100 righe riguardano davvero la settimana: il resto e'
macchina generica, e buona parte del suo valore sta nei commenti che
documentano decisioni costate fatica (i segnali Vega vanno condivisi dentro
una sola vista, L318-320; un `hconcat` non si adatta al contenitore e da li'
viene la larghezza fissa misurata nel browser, L160-174; lo stato di un widget
si scrive solo prima di crearlo, L654-658; la riconciliazione "ultimo tocco
vince", L866-882). Una copia duplicherebbe quel ragionamento e condannerebbe
ogni correzione futura a essere fatta due volte, commenti compresi.

Si estrae invece la macchina in un modulo parametrico sul periodo, e le due
pagine diventano due configurazioni.

Decisioni gia' prese (non rimetterle in discussione):

- **Modulo condiviso parametrico**, non una copia di `week.py` e non una Month
  senza grafici.
- Le annotazioni dei grafici salgono di un livello: dove oggi l'asse a
  settimane porta linee e nomi dei **mesi**, l'asse a mesi porta linee e nomi
  degli **anni**.
- Questo todo viene **prima del 08** (andamento VO2max nella Week). Quando il
  08 arrivera', la sua riga andra' aggiunta una volta sola nel modulo
  condiviso e comparira' su tutte e due le pagine.

## Cosa e' legato alla settimana, verificato

Contato riga per riga su `week.py` (1.020 righe):

| dove | righe | cosa |
|---|---|---|
| L584-587 | 4 | il solo punto in cui si raggruppa: `week_start` dal lunedi' |
| L74-79 | 6 | `_week_label()`, "01 Sep 2025 – 07 Sep 2025" |
| L626-627 | 2 | filtro di sovrapposizione, `+ Timedelta(days=6)` |
| L34-69 | ~8 | intestazione "Week", `format`, e quattro `help` "of the week" |
| L759 | 1 | `freq="W-MON"` |
| L321-337, L433-438 | ~20 | `week_no`, asse `w%V`, tooltip |
| L359-409 + L235-241 | ~50 | linee e nomi dei mesi sovrapposti all'asse |
| L151, L489, L569 | 3 | i letterali `"week_start"` e `"week_key"` |
| sparse | ~15 | stringhe di interfaccia |
| L641-651, 688-751, 797-836 | ~14 | nomi di chiavi di sessione |

Tutto il resto, circa 900 righe, non sa che unita' di tempo sta guardando.
`_totals()` prende gia' un parametro `key` (ed e' gia' chiamata con `"sport"`
a L942), `CHART_ROWS` e' dati, `date_range()` accetta gia' `key`, e i
58 righe di riconciliazione grafico/tabella (L840-897) toccano solo un indice e
quattro nomi di chiave.

Work:

- **`src/training/interface/period_page.py`** (nuovo): il modulo condiviso,
  accanto a `filters.py` e `activity_table.py`, che e' gia' dove sta la roba
  divisa fra pagine (vedi il docstring di `activity_table.py` L3-4: stesso
  argomento, un livello piu' su). Non in `app_pages/`, dove ogni file e' una
  pagina registrata in `app.py`. Un modulo solo, non due: il codice e' lo
  stesso codice, e spezzarlo adesso aggiungerebbe un secondo confine da
  azzeccare durante un trasloco che e' gia' la parte rischiosa.
- **Superficie pubblica: `PeriodSpec` e `render(spec)`**, niente altro. Tutto
  il resto privato (`_chart`, `_pair`, `_row_spec`, `_totals`, `_hm`,
  `_by_period`, `_period_total`, `_clicked_period`, `_boundary_layers`,
  `CHART_ROWS`, le costanti di geometria e di colore).
- **`PeriodSpec` e' una dataclass congelata**, non un dizionario: i campi sono
  una ventina, e ognuno vuole il suo commento. Campi per gruppi: identita'
  (`name`, `title`, `unit`, `adjective`), raggruppamento (`bucket`,
  `bucket_end`, `freq`, `label`), asse e tooltip (`axis_format`,
  `axis_interval`, `point_label`, `tooltip_start_format`), annotazioni
  (`boundary_freq`, `boundary_format`, `boundary_min_share`), tabella
  (`column_header`, `column_format`, `column_width`, `column_help`), filtro
  (`presets`).
- **Le funzioni che definiscono il periodo stanno nel file della pagina**, non
  nel modulo: `bucket`, `bucket_end`, `label`, `point_label` arrivano dentro la
  spec. Cosi' `period_page.py` non contiene **nessun** `if spec.name ==
  "week"`, ed e' questo che lo rende un modulo parametrico invece che un
  modulo bicefalo. Se durante il lavoro serve un `if` sul nome della pagina,
  vuol dire che manca un campo alla spec.
- **`spec.key(*parts)`**: un metodo da cui passa **ogni** chiave di sessione
  della pagina, che antepone `name`. Nessuna chiave costruita con un letterale.
- **Le quattro `help` della tabella si derivano da `unit`**
  (`f"Number of activities in the {spec.unit}."` e compagne): solo quella della
  prima colonna resta testo libero, perche' "Monday that opens the week
  (Mon-Sun)." non ha un corrispettivo mensile. `WEEK_COLUMN_CONFIG` (L36-69)
  diventa `_column_config(spec)`; `WEEK_TABLE_COLUMNS` (L34) diventa
  `TABLE_COLUMNS` con `"period_start"` al posto di `"week_start"`.
- **Tre rinomine portanti**: la colonna `week_start` diventa `period_start`; il
  campo Vega `week_key` (L321, L569, L766, L773) diventa `period_key`; e la
  variabile locale `period_key` (L641), che e' il **suffisso dell'intervallo di
  date** e non un periodo, diventa `range_key`. Senza la terza, i due nomi si
  scambiano di posto ed e' una trappola per chi legge dopo.
- **`week.py` si riduce a ~60 righe di sola configurazione**, e `month.py`
  altrettanto. I commenti che oggi stanno accanto al codice spostato vanno con
  lui: quelli sul lunedi' (L582-583) e sul trattino medio (L75-77) finiscono
  nel file della pagina, gli altri nel modulo.
- **`month.py`**: `bucket` e' `start_time.dt.to_period("M").dt.start_time`;
  `bucket_end` e' `+ pd.offsets.MonthEnd(0)` e non una somma di giorni, perche'
  i mesi non sono lunghi uguali (`MonthEnd(0)` su un primo del mese porta alla
  fine di **quel** mese, non del successivo); `label` e' `f"{start:%B %Y}"`, non
  un intervallo, perche' "September 2025" e' gia' il nome del mese;
  `point_label` e' `%b %Y`; `tooltip_start_format` e' `None`, perche' con
  l'anno gia' nel nome del punto una riga "Starting 01 Sep 2026" non
  aggiungerebbe niente.
- **`app.py`**: una riga dopo L27, `st.Page("app_pages/month.py", title="Month",
  icon=":material/calendar_view_month:")`. E il commento a L14-19 che dice "La
  barra laterale porta solo tre voci di navigazione" va corretto: le voci
  diventano quattro, e i 200px bastano ancora (la ragione dei 200px resta
  valida, cambia solo il conteggio).

Le annotazioni dei grafici:

- **`_boundary_layers(index, x, spec)`**, estratta da L359-409. Variano **tre
  cose sole**: la `freq` di `pd.date_range` (L372, `"MS"` sulla Week, `"YS"`
  sulla Month — e' tutta qui l'idea del "livello sopra"), il formato
  dell'etichetta (L402), e la soglia `boundary_min_share` (L396).
- **Il formato non puo' restare una f-string.** `f"{mid:%b}"` non prende il
  formato da una variabile: diventa `mid.strftime(spec.boundary_format)`. E'
  l'unico punto dove un letterale non si limita a diventare un campo, ed e'
  anche per questo che l'estrazione delle annotazioni e' il secondo passo piu'
  rischioso dopo il trasloco.
- **La soglia, con i numeri.** `CHART_WIDTH` vale oggi `(914 - 94) // 2 - 55 =
  355` (L182-189). A `fontSize=11`, "Sep" occupa ~20px e "2026" ~25px. Lo 0.04
  della Week e' `0.04 x 355 = 14px`; per quattro cifre la stessa aritmetica da'
  **0.07** (`= 25px`). Nota che il commento a L241 dice "~15px su un pannello da
  375": e' rimasto indietro di una revisione di `CHARTS_TOTAL_WIDTH`, il numero
  giusto e' 355. Correggerlo mentre si passa di li'.
- **Non varia nient'altro, e il codice deve continuare a dirlo**: il filtro
  "strettamente interno" (L373 — una linea sul bordo allarga l'asse, e un layer
  vuoto fa protestare Vega con "Infinite extent"); la linea come **primo** layer
  perche' stia dietro a tutto; la colonna chiamata come quella dei dati
  (L367-370) perche' Vega condivida l'asse invece di fondere i titoli;
  `edges = [primo, *confini, ultimo]` e il centraggio sul punto medio
  (L391-404); l'etichetta agganciata al bordo alto con `y=alt.value(0)`,
  `dy=-4`, `baseline="bottom"` invece che con un secondo asse (L382-386 — un
  asse opposto obbligherebbe a risolvere gli assi in modo indipendente).
  Le costanti L235-241 diventano `BOUNDARY_LINE_COLOR`, `BOUNDARY_LINE_WIDTH`,
  `BOUNDARY_LABEL_COLOR`, e il commento "cambi di mese" si allarga a "cambi di
  mese (di anno sulla pagina Month)".
- **Due proprieta' del caso mensile da scrivere nel codice**, tutte e due
  verificate sui dati: sull'asse a settimane il primo del mese cade **fra** due
  lunedi', su quello a mesi il primo di gennaio cade **esattamente su** un punto
  (non si rompe niente, la linea finisce sotto il punto); e il filtro
  "strettamente interno" fa si' che un periodo che **comincia** a gennaio non
  abbia la linea di quell'anno. Con "All" (gen 2025 - set 2026) le linee sono
  percio' **una sola**, al 2026-01-01, ma le etichette restano **due**, perche'
  `edges` include sempre i due estremi.
- Il resto di `_chart` prende gli altri week-ismi dalla spec: L321 resta com'e'
  (`strftime("%Y-%m-%d")` va bene anche per i primi del mese, che sono date
  uniche); L324-326 diventa `spec.point_label(...)`; L333-337 prende
  `spec.axis_format`, `spec.axis_interval` e `spec.unit`; L433-438 costruisce la
  lista dei tooltip saltando la riga "Starting" quando
  `tooltip_start_format` e' `None`. `_chart` e `_pair` prendono un parametro
  `spec`; `_row_spec` no.

Le chiavi di sessione:

- **Quattordici chiavi passano per `spec.key(...)`**: `dates` (L621), `table`
  (L642), `prev_chart`/`prev_rows`/`prev_table`/`source` (L648-651), `sports`
  (L689), `total` (L728), `charts` (L836), piu' quelle oggi globali
  `_week_sports_off` (L688, L716), `_week_total_off` (L732, L751),
  `_week_rows_closed` (L797, L804) e `week_row_{value}` (L800).
- **La ragione non e' l'eleganza.** `range_key` e' costruita solo dalle due
  date, quindi con "All" su tutte e due le pagine le chiavi sarebbero
  **identiche**. E quella della tabella non si limita a sporcare lo stato, fa
  cadere la pagina: L863-864 legge l'indice di riga **prima** che la tabella
  esista, e la riga 40 di una tabella settimanale da 55 righe, letta su un
  indice mensile da 21, solleva `IndexError`. E' la prova che chiude la
  verifica, punto 9.
- **Conseguenza da sapere, non da nascondere**: con le chiavi separate le due
  pagine ricordano i filtri in modo indipendente — spegnere Cycling sulla Week
  non lo spegne sulla Month. E' il comportamento sicuro ed e' quello da
  consegnare. Se un giorno si volesse una legenda sola, si cambiano **solo** le
  tre chiavi di memoria; quelle dei widget devono restare separate comunque.
- Non serve una chiave per `activity_table()` nell'elenco (L1009-1016, il
  commento a L1006-1008 spiega perche') ne' per niente dentro
  `activity_detail.py`: due pagine non vengono mai disegnate nello stesso giro,
  e Streamlit butta lo stato dei widget che un giro non ha disegnato.

I preset del filtro a calendario:

- **`filters._PRESETS` (L9-18) diventa `_PRESET_SETS`**, un gruppo per unita' di
  tempo (`"weeks"` con 4/8/12 e default "12 weeks", `"months"` con 6/12/24 e
  default "12 months"), e `date_range()` prende un argomento `period="weeks"`.
  `_DEFAULT_PRESET` sparisce dentro i gruppi.
- **Day non passa `presets` e resta intoccata** (`activities.py` L30-34, il
  ramo L69-76). **Week eredita il default e non cambia di una riga al punto di
  chiamata**: e' proprio cio' che serve mentre si dimostra che l'estrazione non
  ha cambiato niente.
- **Indietro di N mesi si conta con `pd.DateOffset(months=N)`**, non con una
  `timedelta`: i mesi non sono lunghi uguali. Verificato:
  `Timestamp(2026-09-23) - DateOffset(months=6)` da' `2026-03-23`. `pandas` e'
  gia' importato in `filters.py` (L5).

L'ordine dei passi (ognuno lascia l'app funzionante):

1. **Sole rinomine dentro `week.py`**: `week_start` -> `period_start`,
   `week_key` -> `period_key`, `period_key` -> `range_key`, `_weekly_sum` ->
   `_by_period`, `_weekly_total` -> `_period_total`, `_clicked_week` ->
   `_clicked_period`, `_week_label` -> `_label`. Nessun cambio di struttura,
   nessun cambio di chiavi. Serve a rendere piccolo il diff del passo
   pericoloso.
2. **Gli helper generici nel modulo nuovo**: `_hm`, `_totals`, le costanti di
   geometria col loro commento lungo, la tavolozza, `_sport_colors`,
   `_series_label`, `_series_symbol`, `_color_scale`, `_row_spec`,
   `CHART_ROWS`. `week.py` li importa e continua a girare.
3. **Il corpo della pagina dentro `render()`, senza parametrizzare**: un
   taglia-e-incolla puro piu' un livello di indentazione, con `render()` ancora
   senza argomenti e i valori della settimana scritti dentro. `week.py` diventa
   due righe.
4. **`PeriodSpec`**: si introduce la spec, la si passa a `render`, `_chart`,
   `_pair`, `_boundary_layers`, `_column_config`, si applicano le chiavi e le
   stringhe. Qui l'app **deve** comportarsi ancora esattamente come prima.
5. **I preset** in `filters.py`.
6. **`month.py` e la riga in `app.py`**; poi aggiornare il todo 08.

- **Il passo 3 e' il piu' rischioso.** Il corpo della pagina e' uno script in
  cui l'**ordine delle chiamate Streamlit e' portante** in quattro punti: i tre
  contenitori prenotati (L659-666) e le tre scritture di stato prima che il
  widget esista (L690-691 gli sport, L729-733 il totale, L800-802 le sezioni
  richiudibili, L895-897 la riga della tabella). Un riordino accidentale **non
  solleva niente**: costa un click in piu' o una selezione che punta alla riga
  sbagliata, e ci si accorge dopo. Due contromisure, tutte e due obbligatorie:
  in quel commit **non si modifica una virgola** oltre all'indentazione, e lo si
  dimostra con un `diff` fra il vecchio corpo e il nuovo de-indentato; e
  `render()` **non va spezzata in sotto-funzioni**, perche' una funzione che si
  legge come lo script di oggi e' quella il cui ordine si controlla a occhio.

Vincoli:

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Niente `use_container_width`, deprecato in 1.63.
- Nessuna dipendenza nuova.
- **I commenti di `week.py` devono sopravvivere al trasloco.** Sono la parte
  piu' difficile da riscrivere e la ragione per cui non si copia il file: chi
  sposta il codice sposta anche il commento che lo spiega, adattando solo le
  parole che dicono "settimana" dove ora vale per tutti e due i periodi.
- Non toccare `CHARTS_TOTAL_WIDTH` ne' la geometria dei pannelli: la Month usa
  gli stessi 914px, gia' tarati.
- `training-activity-reports` gira fuori da Streamlit e usa `list_activities()`:
  deve continuare a girare.

Rischi:

- **Si rimaneggia una pagina che oggi funziona.** La Week e' il risultato di
  sei todo (01-06) e ogni suo comportamento e' stato guadagnato: il crosshair
  condiviso dentro la riga, il click che costa un giro solo, i filtri che
  sopravvivono al cambio di periodo, le sezioni che restano chiuse. Vanno
  ricontrollati tutti, non solo che la pagina si apra.
- **Un `boundary_freq` sbagliato produce un grafico plausibile e falso**: linee
  che sembrano al posto giusto ma cadono su un confine che non e' quello. Per
  questo la verifica conta le linee e le etichette invece di guardarle.
- **Nessuno dei 21 mesi e' vuoto** (verificato: 21 mesi nell'intervallo, 21 con
  attivita'). Il percorso "periodo senza attivita' riempito di zeri", che sulle
  settimane si vede tutti i giorni, a granularita' mensile **non viene
  esercitato dai dati reali**: va provato stringendo l'intervallo a mano.
- La Month con "All" mostra 21 punti contro i 91 della Week: le soglie e le
  spaziature tarate su un asse fitto vanno riguardate su uno rado, non
  solo il contrario.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

I numeri vengono dal DB: 127 attivita', dal 3 gennaio 2025 al 23 settembre 2026.
La tabella dei totali copre sempre tutti gli sport (didascalia L673).

1. **Week invariata**, da ricontrollare dopo **ogni** passo, non solo alla fine.
   Con "12 weeks" (dal 2026-07-01): 9 righe, la prima
   `21 Sep 2026 · 2 · 49.4 · 03:13 · 247`, la seconda
   `14 Sep 2026 · 5 · 77.5 · 08:28 · 2047`. Con "All": 55 righe, 91 punti sul
   grafico, **21** linee di mese.
2. **Week, i comportamenti guadagnati dai todo 01-06**: il crosshair si muove su
   tutti e due i pannelli della riga (e non fra righe diverse); un click su un
   punto spunta la riga della tabella in **un solo** giro; un doppio click
   riporta il comando alla riga della tabella; spegnere uno sport, cambiare
   periodo e riaccenderlo lo lascia spento; chiudere "Distance", andare su
   Profile e tornare la lascia chiusa; a 1440 con la barra laterale aperta non
   compare la barra di scorrimento orizzontale.
3. **Month, la tabella.** Con "12 months" (dal 2025-09-23): **13** righe.
   `September 2026 · 16 · 246.1 · 23:38 · 3288`;
   `August 2026 · 17 · 151.5 · 67:37 · 8459`;
   ultima riga `September 2025 · 10 · 152.1 · 60:58 · 1711`.
   Con "All": **21** righe, da gennaio 2025 a settembre 2026.
4. **Month, l'asse**: una tacca per mese, etichette "Jan".."Sep", e **nessun**
   `w%V` da nessuna parte.
5. **Month, le annotazioni**: con "All", **esattamente una** linea d'anno, al
   2026-01-01 (il 2025-01-01 coincide col primo bucket e il filtro lo esclude),
   e **due** etichette, "2025" e "2026".
6. **Month, il tooltip**: `Month: Sep 2026`, poi la serie e il valore, e
   **nessuna** riga "Starting".
7. **Month, le schede** di settembre 2026, in quest'ordine (per tempo
   decrescente): running 10 att. / 73.5 km / 11:51 / VO2Max **40.5**; cycling
   4 / 167.9 km / 10:49; walking 2 / 4.7 km / 00:58.
8. **Month, l'elenco**: 16 righe per settembre 2026, e cliccandone una si apre
   la stessa scheda di dettaglio della Day.
9. **La prova della collisione, che e' il motivo per cui il refactor esiste.**
   Sulla Week: "All", Cycling spento, "Distance" chiusa, selezionata la riga
   `2025-06-30`. Si passa alla Month e si sceglie "All" (stesse due date, quindi
   `range_key` identica). La Month deve aprirsi con **tutti gli sport accesi**,
   **tutte le righe aperte**, **un mese selezionato**, e **senza sollevare
   eccezioni**. Tornando alla Week, Cycling e' ancora spento, "Distance" ancora
   chiusa e `2025-06-30` ancora selezionata.
10. **I preset**: la Month mostra 6 months / 12 months / 24 months / This year /
    All; la Week mostra ancora 4 / 8 / 12 weeks / This year / All; la Day non ha
    scorciatoie, come prima.
11. **Il mese vuoto**: stringendo l'intervallo a mano su un mese senza
    attivita', la tabella non lo elenca e il grafico lo mostra a zero senza
    saltarlo con una diagonale.
12. **Senza browser**: `AppTest` sulle **quattro** pagine, nessuna eccezione.
    Piu' un'asserzione mirata sulle annotazioni, che `AppTest` non mostra:
    costruito il frame mensile su "All" e chiamata `_chart(...)`, il primo layer
    ha **una** riga (`2026-01-01`) e quello delle etichette ne ha **due**; la
    stessa cosa sulla Week su "All" deve dare **21** linee.
13. **La console del browser**: sulla Month non devono comparire messaggi di un
    tipo nuovo rispetto alla Week, ne' errori. Gli avvisi `Infinite extent for
    field` sono noti e gia' contati dal todo 06: il controllo e' "niente di
    nuovo", non "zero".
14. `make activity_reports` gira senza errori.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
