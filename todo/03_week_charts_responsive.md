---
status: done
---

# Week: grafici adattivi alla finestra

I sei grafici della pagina Week hanno una larghezza fissa in pixel:

```python
CHARTS_TOTAL_WIDTH = 1760   # week.py:142
CHART_WIDTH = (CHARTS_TOTAL_WIDTH - _LEGEND_WIDTH) // 2 - _AXIS_WIDTH   # = 750
```

tarata su una finestra da 1920 in layout wide. Ma `app.py` non imposta
`initial_sidebar_state`, quindi la sidebar di navigazione e' aperta e si prende
~244px: lo spazio reale su uno schermo da 1920 e' ~1.548px. **Il blocco sfora
gia' oggi**, sulla macchina per cui e' stato tarato, e produce una barra di
scorrimento orizzontale che serve solo a lui mentre il resto della pagina sta
comodo.

Il fatto centrale, verificato su tre fonti indipendenti: **`width="container"`
non puo' funzionare su questa forma.** I grafici sono un `vconcat` di tre
`hconcat` (L452-491), e:

- lo schema Vega-Lite spedito con altair 6.2.2 dice che `"container"` non e'
  utilizzabile per viste concatenate;
- `streamlit/elements/vega_charts.py` (L339-360) documenta esplicitamente il
  vicolo cieco e sceglie di accettare l'overflow pur di non rompere il
  rendering;
- il frontend propaga la larghezza misurata ai figli del `vconcat` **solo se il
  figlio non e' a sua volta una composizione**, e qui ogni figlio e' un
  `hconcat`, quindi viene saltato.

Passare `width="stretch"` alla chiamata non cambierebbe nulla: cambierebbe solo
la modalita' di autosize.

Work:

- **Prima di tutto, la verifica che decide.** `activity_detail.py` (L137-177)
  passa lo stesso parametro `hover` a grafici disegnati come chiamate
  `st.altair_chart` separate dentro `st.columns`. Accertare **nel browser** se
  il crosshair resta davvero sincronizzato fra viste Vega distinte.
  Se **non** resta sincronizzato: **fermarsi e chiedere ad Andrea**, e' gia'
  stato deciso cosi'. Non sacrificare il crosshair di iniziativa, e non
  ripiegare da soli su una larghezza diversa.
- **Se regge, sostituire la composizione Vega con colonne Streamlit**: sei
  `st.altair_chart` distinti dentro `st.columns(2)` x 3 righe, ogni grafico
  foglia con `.properties(width="container")` e `width="stretch"` sulla
  chiamata. E' esattamente il pattern gia' in uso in `activity_detail.py`
  (L168-177), che porta anche il commento che spiega perche' un `hconcat` con
  figli responsive non funziona.
- **Selezione**: oggi il click arriva da un unico evento
  (`st.altair_chart(charts, on_select="rerun", key=f"charts_{period_key}")`,
  L493-495) letto da `_clicked_weeks` (L311-319). Con sei grafici ci sono sei
  eventi da unire, ognuno con la sua `key`. `_clicked_weeks` va adattata per
  accettarne piu' di uno.
- **Legenda**: oggi ce n'e' una sola per tutti
  (`.resolve_scale(color="shared")`, L491, con il commento "Una sola legenda
  per tutti invece di sei uguali"). Separando i grafici ognuno si porterebbe la
  sua: sopprimerla su cinque, oppure metterne una sola sopra la griglia.
- **Pulizia**: spariscono `CHARTS_TOTAL_WIDTH`, `_LEGEND_WIDTH`, `_AXIS_WIDTH`,
  `CHART_WIDTH` e il commento a L136-147 che li giustifica. `CHART_HEIGHT`
  resta: e' l'altezza dell'area di disegno, non dipende dalla finestra.
- Valutare, se l'altezza resta un problema, di stringere `CHART_HEIGHT` (oggi
  320px per grafico, ~1.200px per il blocco): ma e' una regolazione, non il
  cuore del todo.

Vincoli:

- Niente CSS e niente HTML. Niente `use_container_width` (deprecato in 1.63).
- Commenti in italiano senza accenti, stringhe UI in inglese.
- Il riordino della pagina e' il todo 02, gia' fatto quando si arriva qui: non
  rimetterlo in discussione.
- I colori (`TOTAL_COLOR`, `_SPORT_COLORS`, `_sport_colors()`) e la semantica
  delle serie non cambiano: qui si tocca solo la geometria e il modo di
  disegnare.

Rischi:

- Il crosshair condiviso e il click sulla settimana sono le due cose che
  rendono utili questi grafici. Se la separazione ne rompe una, l'adattivita'
  non vale il prezzo: ecco perche' la verifica viene prima del lavoro.
- Sei chiamate separate vogliono dire sei `key` e sei eventi in sessione al
  posto di uno: attenzione a legarle al periodo come gia' fa
  `f"charts_{period_key}"`.
- La scala dei colori oggi e' condivisa esplicitamente fra i grafici: separandoli
  va garantito che lo stesso sport resti dello stesso colore in tutti e sei,
  altrimenti si perde la leggibilita' a colpo d'occhio.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. **Il controllo che precede tutto**: crosshair sincronizzato fra grafici
   separati, provato nel browser. Documentare l'esito nel report.
2. Restringere la finestra del browser a 1440px e poi a 1280px: i grafici si
   adattano, nessuna barra di scorrimento orizzontale sulla pagina.
3. Con la sidebar di navigazione aperta **e** chiusa: in entrambi i casi i
   grafici occupano la larghezza disponibile, senza sforare.
4. Click su un punto in ognuno dei sei grafici: la settimana selezionata arriva
   alla tabella in tutti i casi.
5. Lo stesso sport ha lo stesso colore in tutti e sei i grafici, e la legenda
   compare una volta sola.
6. Spegnere e riaccendere sport: le serie compaiono e spariscono in tutti i
   grafici in modo coerente.
7. Nessuna eccezione: `AppTest` sulla pagina piu' il giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

---

## Needs decision: il crosshair NON e' condiviso fra viste Vega separate

La verifica che il todo mette prima di tutto e' stata fatta, ed e' negativa.

**Esito.** Passare lo stesso oggetto `alt.selection_point` a due
`st.altair_chart` distinti non condivide il segnale. Ogni `st.altair_chart` e'
una vista Vega a se' stante, con il suo registro di segnali: Altair serializza
lo stesso parametro dentro le due specifiche, ma a runtime diventano due
segnali omonimi e indipendenti. Non esiste un ponte fra le viste, e Streamlit
non ne crea uno.

**Come e' stato verificato** (browser headless, Chromium via Playwright, non
installato nel progetto):

1. Banco di prova costruito apposta con il pattern proposto dal todo: due
   grafici foglia `width="container"` in `st.columns(2)`, stessi `picked` e
   `hover`, `width="stretch"` sulla chiamata. Passando il mouse sul grafico di
   sinistra la riga verticale compare **solo** a sinistra; a destra non succede
   nulla. Gli eventi lo confermano: `LEFT event -> {"hovered": [{"x": 5}]}`,
   `RIGHT event -> {"hovered": {}}`.
2. Stessa prova su `activity_detail.py`, che il todo cita come precedente
   (L137-177): aperta un'attivita' reale nell'app, il crosshair sul grafico
   "Heart rate" resta confinato li'; il grafico "Speed" accanto non mostra ne'
   la verticale ne' il punto evidenziato. **Il parametro `hover` condiviso in
   `activity_detail.py` non sincronizza niente**: ogni grafico ha la sua copia
   del segnale. Il precedente su cui poggiava il piano non regge.

Quindi separare i sei grafici costa il crosshair che si muove su tutti insieme.
Il todo dice di fermarsi qui e non sacrificarlo di iniziativa: fermato.

**Quello che invece funziona** (utile per decidere): `width="container"` dentro
una colonna Streamlit si adatta davvero. Nel banco di prova i due grafici
misuravano 712px per parte su finestra 1600, e 722px su 1920, riempiendo la
riga senza barra di scorrimento. La strada e' percorribile: l'unico prezzo e'
il crosshair. Confermato anche il resto delle previsioni del todo: ogni grafico
separato si porta la sua legenda (da sopprimere), e ogni grafico emette il suo
evento di selezione (sei `key`, `_clicked_weeks` da adattare).

**Opzioni.**

- **A - Adattivi, senza crosshair condiviso.** Sei `st.altair_chart` in
  `st.columns(2)`. I grafici si adattano a qualunque finestra, la barra di
  scorrimento sparisce. Il crosshair resta, ma solo sul grafico sotto il mouse:
  si perde il confronto a colpo d'occhio della stessa settimana su km, ore e
  dislivello. Click e tooltip restano intatti.
- **B - Larghezza fissa, ma tarata giusta.** Si resta sul `vconcat` e si
  abbassa `CHARTS_TOTAL_WIDTH` da 1760 a ~1500, cioe' 1920 meno la sidebar
  (~244px) meno i margini. Il crosshair condiviso resta, la barra di
  scorrimento di oggi sparisce sulla macchina di Andrea, ma il blocco continua
  a non adattarsi e sforerebbe sotto i 1500px di finestra.
- **C - Fisso con la sidebar chiusa.** Come B, piu' `initial_sidebar_state="collapsed"`
  in `app.py`: si recuperano i 244px e i 1760 attuali tornano corretti. Tocca
  pero' tutte le pagine, non solo Week.
- **D - Adattivi con crosshair ricostruito.** Sei grafici separati, e la
  settimana sotto il mouse propagata via `on_select` per farla ridisegnare
  sugli altri cinque. Vuol dire un rerun di Streamlit a ogni movimento del
  mouse: da scartare, e' fuori scala rispetto al beneficio.

**Raccomandazione: A.** La barra di scorrimento orizzontale si paga a ogni
sguardo alla pagina e su qualunque finestra; il crosshair sincronizzato e' un
confronto comodo ma il tooltip, che resta, porta gia' settimana, serie e
valore. B e C rimandano solo il problema, e nessuna delle due rende la pagina
adattiva, che e' quello che il todo chiede.

**Decisione di Andrea: opzione A.** Si procede con i sei grafici separati e
adattivi; il crosshair resta, ma solo sul grafico sotto il mouse.

## Esito: implementato (opzione A)

Sei `st.altair_chart` in `st.columns(2)` x 3 righe, ogni grafico foglia con
`width="container"` e `width="stretch"` sulla chiamata. Spariti
`CHARTS_TOTAL_WIDTH`, `_LEGEND_WIDTH`, `_AXIS_WIDTH`, `CHART_WIDTH` e il
commento che li giustificava; `CHART_HEIGHT` resta a 320, l'altezza non era il
problema. Il crosshair si muove sul solo grafico sotto il mouse, come deciso.

Due cose sono venute fuori strada facendo:

- **La legenda unica sta sopra la griglia, non dentro un grafico.** Messa
  dentro il primo (`orient="top"`) era completa a 1920 ma a 1280px l'ultima
  voce finiva tagliata, perche' un grafico e' largo meta' pagina. Spostata in
  un grafico suo a tutta larghezza: serve `padding=0` e `height=40`, perche'
  Streamlit fissa l'altezza dell'area disegnata e quello che non ci sta viene
  ritagliato.
- **Il blocco `warnings.catch_warnings()` era diventato inutile** e l'ho tolto,
  con l'`import warnings`. Deduplicava un parametro ripetuto dentro *una*
  specifica: con sei specifiche distinte non succede piu' (verificato, nessun
  avviso ne' in `AppTest` ne' nel log dell'app).
