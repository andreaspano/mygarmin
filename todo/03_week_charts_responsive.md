---
status: todo
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
