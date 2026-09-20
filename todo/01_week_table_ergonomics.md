---
status: done
---

# Week: tabella dei totali settimanali piu' ergonomica

La tabella dei totali del tab Week (`src/training/interface/app_pages/week.py`,
`st.dataframe` a L330-338 + `VALUE_COLUMNS` a L18-26) e' il comando della
pagina: la riga selezionata decide cosa mostrano le schede per sport e la lista
attivita' sotto. Va resa piu' leggibile, piu' compatta e davvero ordinabile,
**senza cambiare quali colonne mostra** (`week, n, distance, time, d+, hr`) e
senza toccare l'arbitraggio tabella<->grafici (L438-474).

Riferimento di stile: `activity_table.py` (`ACTIVITY_COLUMN_CONFIG`, L36-56).
Le due tabelle stanno nella stessa pagina e oggi non si somigliano.

Work:

- **Tempo in h:mm.** Oggi `time` e' in ore decimali (`1.8`). Mostrarlo come
  `01:48`, con una `TextColumn` alimentata da un helper:

  ```python
  def _hm(hours: float) -> str:
      """Ore decimali in "hh:mm" (1.8 -> "01:48")."""
      if pd.isna(hours):
          return ""
      minutes = round(hours * 60)
      return f"{minutes // 60:02d}:{minutes % 60:02d}"
  ```

  Lo zero iniziale e' obbligatorio: rende l'ordinamento alfabetico identico a
  quello cronologico (`"09:45" < "10:05"`) e incolonna la cifra. Arrotondare i
  **minuti**, non le ore. Serve `alignment="right"` sulla TextColumn, altrimenti
  resta a sinistra.
  Alternative gia' valutate e scartate (non riaprirle): `timedelta64` viene
  reso dal frontend con `moment.duration().humanize()` -> "2 hours", impreciso e
  non configurabile; `TimeColumn` vuole un `datetime.time` e si rompe oltre le
  24h; non esiste una `DurationColumn` in Streamlit 1.63.
- **Formattare solo a display.** `_totals()` (L39-62) deve continuare a
  restituire ore float: e' usata anche a L488 per le schede per sport, che ci
  fanno aritmetica e `sort_values("time")`. La conversione va fatta su
  `summary` (L311-312).
- **Ordinamento cronologico della settimana.** La colonna `week` e' la stringa
  di `_week_label()` (L35-36), quindi cliccando l'intestazione ordina in
  alfabetico: con un intervallo su piu' anni "01 Jan 2024" finisce accanto a
  "01 Jan 2025". Mostrare invece `week_start` (gia' in `summary`, `datetime64`)
  con una `DatetimeColumn("Week", format="D MMM YYYY", width=130)`.
  `_week_label()` resta: serve ancora a L477, L483, L512.
  Attenzione: rinominare anche la **chiave** nel `column_config` da `"week"` a
  `"week_start"`, altrimenti viene ignorata in silenzio e la colonna esce grezza.
- **Allineamento, intestazioni, tooltip.** `alignment="right"` su tutte le
  colonne numeriche come fa `ACTIVITY_COLUMN_CONFIG` (sui NumberColumn e' gia'
  il default: scriverlo lo stesso, per far leggere le due tabelle come un
  sistema solo). Rinominare l'intestazione `n` -> `"Activities"`. Aggiungere
  `help=` dove il valore non e' ovvio: FC media pesata sulla durata e vuota
  quando nessuna attivita' l'ha registrata, D+ come somma del dislivello
  positivo, settimana = lunedi' che la apre.
- **Densita' e ingombro.** Due parametri risolvono entrambi i lati:
  - `width="content"` — oggi ~710px di colonne vengono stirati su ~1760px di
    layout wide; e' l'origine dello spazio sprecato in orizzontale.
  - `height="auto"` al posto di `height=600` — "auto" significa al massimo
    dieci righe (poi scorre) e meno se le righe sono poche: con un periodo di
    3 settimane oggi si vedono ~550px di griglia vuota.

  Lasciare `row_height` al default (34px): e' gia' stretto, portarlo a 30
  guadagna 40px su dieci righe e rischia testo tagliato. E' il bottone da
  girare dopo, se le righe risultano ancora ariose.
  Non mettere `pinned=True` sulla settimana: con `width="content"` non c'e'
  scroll orizzontale, quindi aggiungerebbe solo una riga di separazione.
- **Celle FC vuote.** Aggiungere `placeholder="-"` alla tabella, per allinearsi
  al `"-"` gia' usato dalle schede per sport (L504-506). Solo `hr` puo' essere
  NaN: `distance`, `time`, `d+` sono somme e tornano `0.0`.
- **Intestazione e affordance sopra la tabella** (questo e' il "contorno"): oggi
  la tabella compare senza titolo, subito dopo i due campi data, mentre ogni
  altro blocco della pagina ha il suo `st.subheader`. Aggiungere un subheader e
  una caption sulla falsariga di `activities.py:57`, che dica sia del click sia
  dell'ordinamento.
- **Coerenza con le schede per sport.** A L502 la metrica del tempo usa
  `f"{totals['time']:.1f} h"`: passarla a `_hm()`, altrimenti la stessa
  settimana si legge `07:24` nella tabella e `7.4 h` duecento pixel piu' sotto.
- **Filtri data (L295-309): non toccarli.** `date_range()` e' condivisa con la
  pagina Activities (`filters.py`); i due input da 160px in container
  orizzontale sono gia' compatti e modificarli toccherebbe una seconda pagina
  senza alcun guadagno per la tabella.
- **Pulizia.** Il commento a L16-17 dice che `VALUE_COLUMNS` e' "condivisa dalle
  due tabelle": non e' piu' vero, l'unico uso e' L332 (verificato) — correggerlo
  e rinominare la costante in `WEEK_COLUMN_CONFIG` (+ `WEEK_TABLE_COLUMNS` per
  l'elenco delle colonne). `from pathlib import Path` (L5) e' inutilizzato.

Decisioni gia' prese (non rimetterle in discussione):

- **Niente icone degli sport nella tabella settimanale.** `ImageColumn` rende
  una sola immagine per cella e una riga settimanale aggrega piu' sport:
  l'icona dello sport dominante sarebbe fuorviante (6h di bici + 40' di corsa
  letta come settimana di sola bici) e una colonna "sports" sarebbe una colonna
  nuova, esclusa dallo scope. Le icone restano dove uno sport esiste davvero:
  schede per sport (L494-496) e tabella delle attivita'.
- **La configurazione resta inline in `week.py`.** `activity_table.py` esiste
  perche' due pagine rendono la stessa lista e stavano divergendo; questa
  tabella ha un solo chiamante. Si estrae quando servira' a una seconda pagina.
- **Non sostituire il preseeding manuale di `st.session_state[table_key]`
  (L324-328) con `selection_default=`.** Verificato: `selection_default` vale
  solo al primo render e non sovrascrive le selezioni successive, quindi non
  puo' esprimere "un click su un grafico ha appena forzato la riga N". Il giro
  `_force_week_row` + `st.rerun()` (L465-467) esiste per quello e va lasciato
  com'e', insieme a tutto il blocco L438-474.

Vincoli:

- Niente CSS e niente HTML: solo elementi nativi e `column_config`.
  Niente `use_container_width`, deprecato in 1.63.
- I commenti del file sono in italiano senza accenti: mantenere lingua e tono.
  Le stringhe della UI restano in inglese.
- Non trasformare in zero la cella FC vuota: la `.where()` a L60 e' voluta.

Rischi:

- L'ordinamento **non** puo' rompere la selezione: verificato in
  `streamlit/elements/arrow.py` (L138-148), `event.selection.rows` sono
  posizioni nel dataframe originale e restano valide anche dopo un ordinamento
  dall'interfaccia. Quindi `weekly.index[...]` e `_force_week_row` reggono. Va
  comunque provato a mano (punti 6 e 7 della verifica).
- Si perde dalla tabella l'intervallo "01 Jan 2025 - 07 Jan 2025": e'
  voluto (colonna piu' stretta e ordinabile), e l'intervallo completo resta
  scritto nei subheader "By sport - ..." e "Activities - ..." sotto.

Da chiedere ad Andrea, non fare di iniziativa:

- La tabella delle attivita' sotto mostra `Duration (min)` = `108`, che dopo
  questa modifica stona con `01:48` sopra. Uniformarla vuol dire toccare
  `ACTIVITY_COLUMN_CONFIG` in `activity_table.py`, che cambia anche la pagina
  Activities: fuori dallo scope "tab week".

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501 e
ricarica al salvataggio):

1. Aprire **Week**: la tabella e' larga quanto le sue colonne, non quanto la
   finestra; al massimo dieci righe, poi scorre.
2. Stringere From/To a ~3 settimane: la tabella si riduce a 3 righe, senza
   griglia vuota sotto.
3. Cliccare due volte l'intestazione **Week**: l'ordine si inverte in modo
   cronologico. Con un intervallo a cavallo di due anni, verificare che
   "01 Jan 2024" non finisca piu' accanto a "01 Jan 2025".
4. Cliccare l'intestazione **Time (h:mm)** su un periodo con settimane sopra le
   10h: `09:45` deve precedere `10:05` (prova del padding).
5. Prendere una settimana con una sola attivita': il suo `Time (h:mm)` deve
   coincidere con il `Duration (min)` di quell'attivita' nella tabella sotto
   (108 -> `01:48`) e con la metrica `Time` della scheda per sport.
6. Ordinare per Distance decrescente e poi cliccare una riga: il titolo
   "By sport - <settimana>" e la lista attivita' devono seguire la riga
   **cliccata**, non quella nella stessa posizione dei dati non ordinati.
7. Sempre con l'ordinamento per Distance attivo, cliccare un punto in un
   grafico: si deve evidenziare la riga giusta e il dettaglio deve seguirla
   (e' il giro `_force_week_row` + `st.rerun()`).
8. Una settimana senza dato FC: la cella mostra `-`, non `0`, `None` o vuoto.
9. Passare il mouse sulle intestazioni: i tooltip compaiono; quello della FC
   spiega sia la pesatura sulla durata sia le celle vuote.
10. Nessun warning di Streamlit nel terminale su chiavi di `column_config`
    sconosciute o tipi di colonna incompatibili.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
