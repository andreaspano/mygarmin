---
status: to commit
---

# Week: la verticale su tutti i grafici, non solo su quello sotto il mouse

Passando il mouse su un grafico della pagina Week la riga verticale tratteggiata
compare **solo li'**. Serve invece su tutti e sei insieme, alla stessa settimana:
e' quello che permette di leggere km, ore e dislivello della stessa settimana in
un colpo d'occhio, senza spostare gli occhi avanti e indietro fra i pannelli.

Era cosi' fino al todo 02. Il todo 03 l'ha sacrificata di proposito (opzione A,
scelta da Andrea) per avere i grafici adattivi alla finestra: sei viste Vega
separate dentro `st.columns`, e fra viste distinte i segnali non passano.

**Quella conclusione era giusta sulla forma sbagliata.** Il todo 03 aveva
provato `width="container"` su un `vconcat` di `hconcat`, dove non puo'
funzionare. Non aveva provato a **forzare l'autosize** su un `vconcat` di
grafici a layer. Provato adesso, funziona: si riprende la verticale condivisa
**senza** rinunciare all'adattivita'.

## Il meccanismo, verificato

In `streamlit/elements/vega_charts.py`, `_prepare_vega_lite_spec()` aggiunge un
autosize **solo se lo spec non ne ha gia' uno** (L328: `if "autosize" not in
spec`). Per un `vconcat` a larghezza contenitore sceglie:

- `fit-x` se il `vconcat` non ha composizioni annidate: la larghezza totale
  (assi compresi) si adatta al contenitore;
- `pad` se ne ha: nessun adattamento, e il totale sfora il contenitore.

`_has_nested_composition()` (L277-302) conta anche `layer` fra le composizioni
annidate, e i nostri grafici sono `alt.layer(...)` di cinque strati. Quindi
Streamlit da' `pad` e si torna allo sbordamento del todo 03. Ma l'autosize lo
possiamo scrivere noi, e Streamlit non lo sovrascrive:

```
has_nested_composition(vconcat di layer) : True
autosize che Streamlit inietterebbe      : {'type': 'pad',   'contains': 'padding'}
autosize se lo scriviamo noi             : {'type': 'fit-x', 'contains': 'padding'}
```

Misurato nel browser su un banco di prova (tre pannelli a layer in un
`vconcat`, `autosize` `fit-x` forzato, `st.vega_lite_chart(..., width="stretch")`):

| finestra | larghezza SVG | barra orizzontale | verticale passando sul 1o pannello |
|---|---|---|---|
| 1680px | 1520px | no | visibile su **tutti e tre** i pannelli |
| 1280px | 1120px | no | visibile su **tutti e tre** i pannelli |

Nessun errore "Infinite extent" (quello che il commento di Streamlit associa al
`fit-x` su `hconcat` annidati non si presenta con i `layer`).

**Il prezzo e' la disposizione**: un `vconcat` di `hconcat` resta la forma che
non funziona, quindi i sei grafici vanno **incolonnati uno sotto l'altro**, non
piu' a griglia 3x2.

Work:

- **Prima di tutto, la verifica che decide.** Rifare la prova qui sopra **sui
  grafici veri** della pagina, non sul banco di prova: sei pannelli, i dati
  reali, il periodo di default. Se la verticale non si muove su tutti e sei, o
  se compare una barra di scorrimento orizzontale, o se Vega tira fuori un
  "Infinite extent": **fermarsi e riferire**, senza ripiegare da soli su una
  larghezza fissa (e' il pasticcio che il todo 03 ha appena tolto di mezzo).
- **Ricomporre i sei grafici in una vista sola**: `alt.vconcat(...)` dei sei
  grafici foglia, `.resolve_scale(color="shared")`, poi `.to_dict()` e
  `spec["autosize"] = {"type": "fit-x", "contains": "padding"}` prima di
  passarlo a `st.vega_lite_chart(spec, width="stretch", on_select="rerun",
  key=f"charts_{period_key}")`. Serve `st.vega_lite_chart` e non
  `st.altair_chart` perche' l'autosize va scritto nel dizionario.
- **Ordine dei pannelli**: settimanale e cumulato della stessa grandezza uno
  sotto l'altro (Distance, Distance cumulative, Duration, Duration cumulative,
  Elevation gain, Elevation gain cumulative), cosi' la coppia resta vicina come
  quando era affiancata.
- **Altezza**: a tutta larghezza i pannelli possono essere piu' bassi.
  Abbassare `CHART_HEIGHT` (L145) da 320 a ~180-200 e misurare l'altezza totale
  del blocco: sei pannelli a 320 farebbero ~2.000px, che e' troppo.
- **Semplificazione che viene in regalo**: tornando a un evento solo,
  `_clicked_weeks()` (L395) torna a leggere una selezione sola, e spariscono
  `_prev_chart_weeks` e la trafila del "quale dei sei e' cambiato" (L656-670).
  Toglierli, non lasciarli a girare a vuoto.
- **Via `_pair()` che restituisce una coppia** (L352): ora serve una lista
  piatta di pannelli. Va bene anche tenerlo e spacchettarlo, basta che non resti
  la struttura a righe (`rows`, L574) e le `st.columns` (L637).
- **Legenda**: con una vista sola `resolve_scale(color="shared")` torna a dare
  una legenda unica dentro lo spec, gratis. Vedi la nota sul todo 05 qui sotto.

Vincoli:

- Niente CSS e niente HTML.
- Commenti in italiano senza accenti, stringhe UI in inglese.
- Non tornare a una larghezza in pixel: se la strada dell'autosize non regge, ci
  si ferma, non si ripiega.
- I colori e la semantica delle serie non cambiano: il Total settimanale resta
  la somma degli sport accesi, il cumulato resta su tutti.
- Non toccare le chiavi legate al periodo ne' la memoria `_week_sports_off`
  (todo 04).

## Rapporto con il todo 05

Il todo 05 (una riga sola per legenda e scelta sport) tocca lo stesso blocco, e
i due si incrociano:

- **Fare prima il 06.** Il 05 parte dal fatto che la legenda e' una striscia
  Altair separata (`_legend()`), che il 06 rende inutile: con una vista sola la
  legenda torna dentro lo spec.
- Fatto il 06, il 05 si puo' anche fare meglio: dentro una vista sola una
  selezione `bind="legend"` funziona davvero, e le selezioni di legenda tornano
  da `on_select` (verificato). Quindi il click sulla voce di legenda potrebbe
  restare dentro Vega invece di passare dalle pills.
- Non decidere qui: rileggere il 05 dopo aver fatto il 06.

Rischi:

- L'autosize forzato e' un dettaglio interno di Streamlit (`if "autosize" not in
  spec`): un aggiornamento potrebbe cambiarlo. Scriverlo nel commento, cosi' chi
  lo trova sa perche' c'e' e cosa guardare se un giorno smette.
- Incolonnare sei pannelli allunga la pagina: e' il motivo per cui l'altezza va
  rivista, ed e' il compromesso che il todo 02 aveva gia' affrontato una volta.
- `st.vega_lite_chart` invece di `st.altair_chart` vuol dire che il grafico
  arriva come dizionario: attenzione a non perdere per strada i parametri di
  selezione (`picked`, `hover`) nella conversione con `.to_dict()`.
- La verticale condivisa e il click sulla settimana sono le due cose che rendono
  utili questi grafici: se la ricomposizione ne rompe una, si e' solo spostato
  il problema.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. **Il controllo che precede tutto**: passando il mouse su un pannello
   qualunque, la verticale tratteggiata e il punto evidenziato compaiono su
   **tutti e sei**, alla stessa settimana. Documentare l'esito nel report.
2. Restringere la finestra a 1440px e poi a 1280px, con la sidebar aperta **e**
   chiusa: i pannelli si adattano, nessuna barra di scorrimento orizzontale.
3. Click su un punto in ognuno dei sei pannelli: la settimana selezionata arriva
   alla tabella in tutti i casi, e il doppio click la azzera come prima.
4. Lo stesso sport ha lo stesso colore in tutti e sei, e la legenda compare una
   volta sola.
5. Spegnere e riaccendere sport: le serie compaiono e spariscono in tutti i
   pannelli in modo coerente.
6. Misurare l'altezza totale del blocco dei grafici e riportarla nel report:
   deve restare nell'ordine di quella di oggi (~1.200px), non il doppio.
7. Nessuna eccezione, e nessun messaggio di Vega nella console del browser:
   `AppTest` sulla pagina piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.

## Esito: implementato

La verticale si muove su tutti e sei i pannelli. La disposizione e' rimasta la
griglia 3x2, per scelta di Andrea a lavoro gia' fatto: i sei incolonnati
funzionavano ed erano adattivi, ma la griglia si legge meglio.

**La griglia costa la larghezza fissa, e non e' negoziabile.** Provate tutte le
strade native, misurando:

| forma | crosshair condiviso | adattiva |
|---|---|---|
| sei pannelli incolonnati (`vconcat` di `layer`) + `fit-x` forzato | si' | si' |
| griglia (`vconcat` di `hconcat`) + `fit-x` forzato | si' | no, collassa a larghezza 0 |
| griglia + `fit` o `pad` | si' | no, larghezza fissa |
| facet `columns=2` | si' | no, larghezza fissa |
| sei `st.altair_chart` in `st.columns` | **no** | si' |

Il frontend di Streamlit passa la larghezza misurata ai figli di un `vconcat`,
ma non scende dentro gli `hconcat`; e `st.context` non espone la larghezza
della finestra, quindi non la si puo' nemmeno calcolare. Percio' con la
griglia l'autosize non si forza: Streamlit mette `pad` da solo, che e'
"nessun adattamento", cioe' quello che serve avendo gia' deciso noi i pixel.

**La legenda e' passata da destra a sopra.** A destra la sua larghezza entrava
nel bilancio orizzontale, e quella larghezza **dipende dai dati**: "Cross
country skiing" e' ~90px piu' lungo di "Cycling", quindi bastava uno sport
nuovo per far sbordare il blocco. Sopra, il bilancio in larghezza non dipende
piu' da cosa c'e' nei dati, e i ~100px liberati sono tornati ai pannelli.

Misurato nel browser (SVG 938x1031, `CHARTS_TOTAL_WIDTH = 940`: la costante
ora vale davvero la larghezza occupata):

| finestra | sidebar | contenitore | margine | barra |
|---|---|---|---|---|
| 1920 | aperta | 1460 | 522 | no |
| 1920 | chiusa | 1760 | 822 | no |
| 1440 | aperta | 980 | 42 | no |
| 1280 | aperta | 820 | **-118** | **si'** |
| 1280 | chiusa | 1120 | 182 | no |

**Limite noto**: a 1280 con la sidebar aperta il blocco sborda ancora. Chiudere
la sidebar basta; in alternativa si abbassa `CHARTS_TOTAL_WIDTH`, al prezzo di
pannelli piu' stretti.

Attenzione a come si misura: il contenitore del grafico non e' l'area
principale della pagina. A 1440 l'area principale e' 1.140 ma il contenitore e'
980, e controllando l'overflow sul documento invece che sul contenitore lo
sbordamento non si vede (la barra compare sull'elemento del grafico).

Altre scelte:

- **L'asse dei tempi lo disegna solo l'ultima riga.** Le tre righe ce l'hanno
  uguale: ripeterlo allungava il blocco senza dire niente di nuovo.
- **Altezza del blocco: 1.031px contro i 1.048px di prima.** Ci sta, anche con
  la legenda sopra, perche' due righe di asse x in meno pagano il suo ingombro.
- `_clicked_weeks()` torna a leggere **una** selezione, e sono spariti
  `_prev_chart_weeks` e la trafila del "quale dei sei e' cambiato" del todo 03.
- Via `_legend()`: la legenda torna dentro lo spec, gratis, con
  `resolve_scale(color="shared")`.

**Un avviso di Vega che c'era gia'**: la console mostra 48
`WARN Infinite extent for field ...`. Non sono nuovi: contati anche su `main`
prima della modifica, sono **48 identici**. Nessun errore, e i grafici si
disegnano giusti. Varrebbe un todo suo: l'origine e' qualche layer che riceve
dati vuoti.
