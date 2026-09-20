---
status: todo
---

# Week: ordine e ingombro della pagina

La pagina `src/training/interface/app_pages/week.py` e' alta ~4.700px, cinque
schermate a 1080p, e i blocchi non stanno nell'ordine in cui servono. I
segnaposto `st.container()` (L399-403) invertono l'ordine di scrittura: i
grafici sono scritti prima nel sorgente ma finiscono **ultimi** sullo schermo,
sotto la scheda di dettaglio attivita' che da sola e' alta ~1.900px. Cliccare
un punto in un grafico sposta contenuto che sta ~2.700px piu' in alto, cioe'
fuori campo: non si vede succedere niente.

Ordine attuale sullo schermo -> ordine obiettivo:

| Oggi | Obiettivo |
|---|---|
| titolo, filtri, tabella settimanale | titolo, filtri **con preset**, tabella |
| schede per sport (~830px) | **grafici** |
| tabella attivita' + dettaglio (~1.900px) | schede per sport, compattate |
| heading + checkbox sport, grafici (~1.200px) | tabella attivita' + dettaglio |

Work:

- **Riordinare i blocchi** con gli stessi segnaposto `st.container()` gia' in
  uso (L399-403), cambiando quale blocco si prenota dove. Il dettaglio
  attivita', il blocco piu' alto della pagina, va in fondo. I grafici salgono
  subito sotto la tabella che comandano.
- **Semplificare l'arbitraggio.** Disegnando i grafici *prima* di creare la
  tabella (che resta visivamente sopra, dentro un container prenotato), al
  momento di creare `st.dataframe` la settimana scelta nel grafico e' gia'
  nota: si puo' passare la riga direttamente invece di lasciarla in
  `_force_week_row` e rilanciare lo script. Questo **elimina lo `st.rerun()`
  (L526)** e dimezza il lavoro per ogni click su un grafico, che oggi costa due
  esecuzioni complete dello script.
  E' la modifica piu' delicata del todo. Se non regge, tornare al giro con
  `st.rerun()` e **scrivere nel report perche'**, invece di forzarla.
- **Preset di periodo** in `filters.py`: scorciatoie ultime 4 / 8 / 12
  settimane / anno corrente / tutto, con `st.segmented_control`. Oggi la pagina
  parte sull'intero storico, 89 settimane: 89 righe in tabella e 89 punti su
  ogni grafico. Il default va stretto.
  `date_range()` e' condivisa con la pagina Activities (`activities.py:38-42`
  e' l'altro chiamante): aggiungere un **parametro opzionale, spento di
  default**, cosi' Activities resta identica finche' non si decide altrimenti.
- **Schede per sport** (L538-565): oggi impilate a tutta larghezza, ~150px
  l'una, ~830px con cinque sport. Affiancarle con `st.columns`. Quando lo sport
  della settimana e' uno solo, la scheda e' pura duplicazione — i suoi cinque
  numeri sono gli stessi cinque della riga selezionata in tabella 400px piu' su
  (stesso `_totals`): in quel caso si puo' evitare del tutto.
  Il rapporto `st.columns([1, 9])` (L551) e' una proporzione, non una
  larghezza: a 1760px da' ~176px di colonna per un'icona da 56px, cioe' ~120px
  morti per scheda. Stringerlo.
- **Tabella attivita'** (L576-583): `height=300` fisso vuol dire ~230px di
  griglia vuota con una sola attivita', e sette righe alla volta con dodici.
  Portarla all'altezza che segue le righe con un tetto, come la tabella
  settimanale.
- **Salti di layout**: la caption condizionale (L540), l'`st.info` che
  sostituisce 1.200px di grafici quando si spengono tutti gli sport (L423) e il
  dettaglio che raddoppia la pagina a ogni click cambiano l'altezza senza
  preavviso. Attenuarli dove si puo' (spazio prenotato, messaggi che occupano
  un posto stabile).
- **Bug dell'arbitraggio da correggere**: il doppio click su un grafico
  (`clear="dblclick"`, L435) azzera `chart_week`, ma la condizione a L504
  pretende `chart_week is not None`, quindi `source` resta `"chart"`,
  `picked_week` diventa `None` e la pagina salta all'ultima settimana **mentre
  la riga della tabella resta evidenziata su un'altra**. Stato incoerente fra
  cio' che e' selezionato e cio' che si vede.

Vincoli:

- Niente CSS e niente HTML: elementi nativi. Niente `use_container_width`.
- Commenti in italiano senza accenti, stringhe UI in inglese.
- Non e' questo il todo dei grafici adattivi (e' il 03): qui i grafici si
  spostano, non si ristrutturano.
- Non e' questo il todo della coerenza dei nomi (e' il 04).

Rischi:

- L'arbitraggio (L497-533) e' la parte fragile della pagina. L'ordine
  obbligatorio oggi e' "stato tabella seminato -> tabella creata -> grafici
  disegnati -> arbitraggio": va sostituito consapevolmente, non aggirato.
- `picked` e' usato sia come parametro Altair (L434) sia come DataFrame di
  attivita' (L535). Oggi non fa danno solo perche' i grafici sono gia'
  costruiti quando viene riassegnato: un riordino lo rompe. Rinominarne uno.
- `int(weekly.index.get_loc(picked_week))` (L525) e' una posizione nel
  `weekly` corrente, ordinato dal piu' recente: resta valido solo finche' il
  DataFrame passato a `st.dataframe` conserva quell'ordine.

Verifica (non esiste una suite di test; l'app gira su http://localhost:8501):

1. Misurare l'altezza della pagina prima e dopo: l'obiettivo e' che i grafici
   siano raggiungibili senza attraversare il dettaglio attivita'.
2. Click su una riga della tabella: schede per sport e lista attivita'
   seguono, e si vede succedere qualcosa senza scorrere.
3. Click su un punto di un grafico: la riga giusta si evidenzia in tabella e il
   resto segue. Se lo `st.rerun()` e' stato rimosso, verificare che basti un
   solo giro (niente sfarfallio, niente doppio caricamento).
4. Doppio click su un grafico: selezione azzerata in modo coerente, la tabella
   non resta evidenziata su una settimana diversa da quella mostrata.
5. Preset di periodo: ognuno seleziona l'intervallo giusto; le date restano
   modificabili a mano; la pagina Activities e' rimasta identica.
6. Settimana con un solo sport e settimana con cinque: le schede si comportano
   come previsto in entrambi i casi.
7. Settimana con una sola attivita' e settimana con dodici: la tabella in fondo
   non lascia vuoto ne' comprime.
8. Spegnere tutti gli sport e riaccenderli: la pagina non deve sobbalzare di
   una schermata.
9. Nessuna eccezione: `st.testing.v1.AppTest` sulla pagina (in-process, vedi
   come e' stato fatto per il todo 1) piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati.
