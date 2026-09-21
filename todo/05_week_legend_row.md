---
status: done
---

# Week: una riga sola per legenda e scelta degli sport

Sotto **Weekly volume by sport** la pagina spende tre blocchi in fila per
quella che e' una cosa sola:

1. la fila di `st.pills` degli sport, cioe' il filtro (L490-523);
2. il toggle `Show total` (L526-543);
3. una striscia Altair alta 40px che disegna la legenda (`_legend()`, L200-227,
   disegnata a L629).

La legenda e il filtro elencano le stesse voci due volte, una sopra l'altra: la
legenda e' quella che porta i colori, il filtro e' quello che si puo' cliccare.
Chi guarda deve tenere insieme due righe per capire una cosa sola.

Obiettivo: **una riga sola**. Ogni voce e' un anello colorato con un pallino
scuro in mezzo (lo stesso simbolo che la legenda Vega disegna gia' oggi) seguito
dal nome. Cliccandola, la voce diventa grigia e la sua linea sparisce dai sei
grafici.

Decisioni gia' prese, da non rimettere in discussione:

- spegnere uno sport **ricalcola** il Total settimanale senza di lui, cioe' il
  comportamento di oggi: cambia il controllo, non il significato. (Il Total
  cumulato resta su tutti gli sport, come documenta `_pair()`.)
- con un solo sport selezionato la voce **Total resta, grigia e non
  cliccabile**: sotto i due sport la serie Total non viene proprio costruita.

## La strada: pills native, non una legenda disegnata a mano

Verificato contro le versioni installate (Streamlit 1.63.0, Altair 6.2.2), sono
fatti, non ipotesi:

- `st.pills` **non** ha un parametro `icons`, ma quello che restituisce
  `format_func` **viene reso come Markdown**;
- il Markdown di Streamlit accetta un **colore esadecimale qualunque** con
  `:color[testo]{foreground="#4c78a8"}` (i badge no, quelli accettano solo la
  tavolozza di nomi: percio' niente badge);
- un'icona Material annidata li' dentro eredita quel colore, perche' lo span
  dell'icona non imposta un `color` suo;
- `:material/radio_button_checked:` e' un'icona valida ed e' esattamente "un
  cerchio colorato con un bottone scuro in mezzo"; `radio_button_unchecked` e'
  l'anello vuoto;
- l'etichetta non finisce nel percorso "solo icona" di `extract_leading_icon()`,
  che la toglierebbe dal Markdown: provato in memoria, il primo pezzo
  `:color[:material/radio_button_checked:]{foreground="#4c78a8"}` non viene
  riconosciuto come icona pura, quindi la stringa resta intera e passa dal
  Markdown.

Quindi il simbolo della legenda puo' stare **dentro l'etichetta della pill**, e
la fila di pills diventa la legenda. Meglio delle alternative:

- una striscia Altair con selezione al click funzionerebbe (le selezioni
  `bind="legend"` tornano davvero da `on_select`, verificato), ma rifarebbe a
  mano l'impaginazione di una legenda, e la semantica del binding di legenda e'
  "seleziona solo questa", non "spegni questa";
- resta tutto nativo, accessibile da tastiera, e fuori dalla lotta con
  l'altezza che `_legend()` ha dovuto combattere (`padding=0`, `height=40`).

Work:

- **Prima di tutto, la verifica che decide.** Accertare **nel browser** che
  `:color[:material/radio_button_checked:]{foreground="#4c78a8"} Cycling` si
  veda come un anello del colore dello sport dentro una pill. L'annidamento e'
  confermato leggendo il codice, non guardandolo: se l'anello esce senza
  colore, **fermarsi e riferire**, senza ripiegare da soli sui colori con nome
  della tavolozza Streamlit — vorrebbe dire cambiare `_SPORT_COLORS`, che il
  todo 03 ha congelato.
- **Una riga sola**: un `st.container(horizontal=True)` con dentro due widget.
  - la fila di pills degli sport che c'e' gia' (`sport_key` legata al periodo,
    con la memoria `_week_sports_off` del todo 04: **tenerle tutte e due**,
    hanno risolto un problema vero), con `wrap=False` per non andare a capo;
  - una seconda `st.pills` con la sola voce **Total**, cosi' puo' avere
    `disabled=not total_available`. E' un flag che vale per tutto il widget:
    e' questo il motivo per cui Total prende un widget suo invece di essere la
    quinta voce del primo, ed e' quello che rende onesto "grigia e non
    cliccabile". Tenere il testo di `help` del todo 04, che spiega perche'
    servono due sport.
- **Il simbolo**: una funzione `_series_symbol(name, colors, on)` che costruisce
  l'etichetta — il colore dello sport (o `TOTAL_COLOR`) quando la voce e'
  accesa, un grigio neutro quando e' spenta — riusando `_series_label()` per il
  testo e `_sport_colors()` per il colore. `format_func` legge quali voci sono
  spente da `st.session_state[sport_key]`: Streamlit scrive lo stato dei widget
  prima di far partire lo script, quindi li' c'e' gia' il valore corrente.
- **Togliere `_legend()`** (L200-227) e la sua chiamata `st.altair_chart`
  (L629). `_color_scale()` **resta**: alimenta i sei grafici ed e' quello che
  tiene lo stesso sport dello stesso colore dappertutto.
- **Restano** la didascalia `Charts only — the tables on this page always cover
  every sport.` (L488) e il ramo
  `st.info("Select at least one sport to plot.")`.

Vincoli:

- Niente CSS e niente HTML: il colore passa dalla direttiva `:color[...]{...}`
  del Markdown di Streamlit, non da uno `style`.
- Commenti in italiano senza accenti, stringhe UI in inglese.
- I colori (`TOTAL_COLOR`, `_SPORT_COLORS`, `_sport_colors()`) non cambiano.
- Non toccare il significato delle serie: il Total settimanale resta la somma
  degli sport accesi, il Total cumulato resta su tutti.
- Non rimettere in discussione le chiavi legate al periodo ne' la memoria
  `_week_sports_off`: sono il todo 04, e il motivo sta scritto li'.

Rischi:

- L'anello colorato dentro una pill e' confermato leggendo il codice, non
  guardandolo: per questo la verifica viene prima del lavoro.
- `format_func` che legge `st.session_state[sport_key]` gira un po' su se
  stesso: se leggesse un valore vecchio, il colore del simbolo resterebbe
  indietro di un giro rispetto alla selezione. Da controllare nel browser, non
  solo a ragionamento.
- Le pills vanno a capo quando la finestra si stringe; `wrap=False` le tiene su
  una riga e semmai le fa scorrere. Controllare a 1280px che non si tagli
  niente, come nel todo 03.
- Via `_legend()` sparisce l'unico elemento fra la didascalia e i grafici:
  verificare che il blocco non perda il suo respiro verticale.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. **Il controllo che precede tutto**: l'anello si vede del colore dello sport
   dentro la pill, provato nel browser. Documentare l'esito nel report.
2. Spegnere uno sport: il suo simbolo diventa grigio **e** la sua linea sparisce
   da tutti e sei i grafici; il Total settimanale cala di quel volume, il Total
   cumulato no.
3. Con un solo sport selezionato: la voce Total e' grigia e non risponde al
   click, e la serie Total non compare nei grafici.
4. Uno sport spento resta spento cambiando periodo e tornando indietro: la
   memoria del todo 04 deve continuare a funzionare.
5. A 1920, 1440 e 1280px: la riga resta una riga, niente barra di scorrimento
   orizzontale sulla pagina, niente tagliato.
6. Nessuna eccezione: `AppTest` sulla pagina piu' un giro nel browser, e un
   controllo che le tre pagine si aprano ancora.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

## Esito: implementato

**La verifica che decideva e' passata**: nel browser l'anello dentro la pill
prende il colore esatto della serie (`rgb(228, 87, 86)` per Cycling, cioe'
`#e45756`, e cosi' via), spento diventa l'anello vuoto grigio. Niente ripiego
sulla tavolozza con nome: `_SPORT_COLORS` non e' stato toccato.

Una riga sola, `st.container(horizontal=True)`, con due `st.pills`: gli sport, e
Total in un widget suo per poterlo disabilitare. Provato nel browser, in
sequenza: spegnere Hiking (simbolo grigio, linea via da tutti i pannelli),
cambiare periodo e tornare (resta spento), spegnere e riaccendere Total, ridursi
a un solo sport (Total grigio e `disabled`, serie Total assente). Il colore
segue il click nello stesso giro, senza restare indietro.

Il todo era stato scritto prima del 06, e due cose sono cambiate di
conseguenza:

- `_legend()` non c'era piu' da togliere: l'aveva gia' tolta il 06, che aveva
  rimesso la legenda dentro lo spec. **Quella legenda ora e' spenta**
  (`legend=None`): la riga di pills e' la legenda, e tenerle tutte e due era
  esattamente il doppione da eliminare. Il blocco dei grafici scende da 1.031 a
  977px.
- La strada `bind="legend"` che il 06 suggeriva di riconsiderare e' stata
  scartata per il motivo che il todo dava gia': la sua semantica e' "seleziona
  solo questa", non "spegni questa", e Total grigio-e-non-cliccabile li' non si
  puo' fare.

Da sapere:

- **La chiave del totale e' cambiata** (`plot_total_pill_{periodo}`): prima lo
  stato era un booleano (toggle), ora e' una lista (pills), e una sessione
  rimasta aperta li avrebbe confusi.
- **Le etichette che cambiano con la selezione non rimontano il widget**: con
  una `key`, l'identita' di `st.pills` e' la chiave piu' `click_mode`
  (`key_as_main_identity` in `button_group.py`), le opzioni formattate non ne
  fanno parte.
- **`AppTest` non sa pilotare queste pills**: confronta i valori grezzi con le
  etichette disegnate, che ora sono Markdown, e svuota la selezione. E' un
  limite del banco di prova, non dell'app: le verifiche di comportamento sono
  state fatte nel browser. `AppTest` resta valido per "la pagina gira senza
  eccezioni".
- A 1920, 1440 e 1280 la riga sta su una riga sola (finisce a 826px). Il limite
  dei grafici a 1280 con la sidebar aperta e' quello gia' noto del todo 06, e
  non dipende da questa riga.
