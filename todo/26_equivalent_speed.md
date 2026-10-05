---
status: todo
---

# Velocita' equivalente in piano (pendenza normalizzata), in tabella

La velocita' media non confronta uscite con dislivelli diversi: 9 km/h su un
percorso collinare possono valere piu' di 10 km/h in piano. La **velocita'
equivalente** e' la velocita' che in piano costerebbe la stessa energia spesa
sulla pendenza reale. Oggi il repo calcola la pendenza solo per colorare lo
scatter "Speed vs HR" della scheda di dettaglio (`activity_detail.py`, righe
167-171), e una velocita' equivalente non c'e'.

Qui la si calcola una volta per attivita', la si salva in `activities.db` e la
si mostra come colonna della tabella delle attivita'.

## Il modello

Costo energetico della corsa di Minetti et al. 2002 (J/kg/m), con la pendenza
`i` come frazione (5% -> 0.05), valido fra -45% e +45%:

```
C(i) = 155.4 i^5 - 30.4 i^4 - 43.3 i^3 + 46.3 i^2 + 19.5 i + 3.6
C(0) = 3.6
```

La distanza equivalente e' la somma dei tratti pesati per il costo, e la
velocita' equivalente e' quella distanza divisa per il tempo in movimento:

```
v_eq = sum(dd * C(i) / C(0)) / tempo in movimento
```

Si divide per il tempo in movimento, come fa `avg_speed_kmh`
(`fit._avg_speed_kmh`), cosi' su un percorso piatto le due velocita'
coincidono. Si sommano le distanze invece di fare la media delle velocita'
istantanee: ogni tratto pesa per il tempo che ci si passa, e le pause non
contano.

Ordini di grandezza: +5% -> x1.30, -5% -> x0.76, -20% -> x0.50 (il minimo; piu'
ripido il costo risale, perche' frenare costa).

## Work

- **Nuovo modulo `src/training/interface/grade.py`**:
  - `slope_pct(records)`: la pendenza in percentuale dai record, come la
    calcola oggi `activity_detail.py`: dislivello diviso distanza, distanza 0
    -> NaN, media mobile di 30s centrata. La clip la fa ogni chiamante: ±45%
    per il modello (il suo intervallo di validita'), ±30% per i colori del
    grafico.
  - `minetti_cost(i)`: il polinomio qui sopra.
  - `equivalent_speed_kmh(records) -> float | None`. Il tempo in movimento
    conta solo i campioni con velocita' > 0 e Δt <= 30s (la soglia di
    `_with_gap_breaks`). Restituisce `None` se mancano altitudine o distanza,
    o se il tempo in movimento e' zero.
  - Il commento cita la fonte della formula e dice che in salita Minetti e'
    piu' severo del GAP di Strava, quindi i numeri non coincidono con Strava.
- **`activity_detail.py`**: usa `grade.slope_pct` al posto del calcolo
  inline, con la clip a ±30. Lo scatter non deve cambiare.
- **`db.py`**:
  - colonna `equiv_speed_kmh REAL` in `_SCHEMA` e in `_insert_activity`;
  - in `_parse_and_store` il valore si calcola dai `records` gia' letti, cosi'
    il FIT non si legge una seconda volta. Gli sport fuori elenco restano a
    `None`;
  - `LOGIC_VERSION` passa da "4" a "5", con la sua nota nello storico delle
    versioni. Il rebuild lo fa `sync()` da solo al primo avvio: niente
    migrazioni a parte e niente modifiche a mano a `activities.db`.
- **Sport**: `running`, `hiking`, `walking`. La curva e' misurata sulla corsa:
  per camminata ed escursione e' un'approssimazione, e il commento lo dice.
  Bici e sci restano fuori, con la cella vuota.
- **`activity_table.py`**: colonna `equiv_speed_kmh` in `ACTIVITY_COLUMNS`
  dopo `total_ascent_m`, e in `ACTIVITY_COLUMN_CONFIG` con intestazione
  "Eq km/h", un decimale, allineata a destra, e questo `help`: "Grade-adjusted
  speed: the flat-ground speed with the same energy cost (Minetti 2002), over
  moving time. Running, hiking and walking only." Il commento sopra
  `ACTIVITY_COLUMNS` dice "solo tre grandezze": va aggiornato, diventano
  quattro per scelta di Andrea.

## Vincoli

- Nessuna dipendenza nuova: numpy e pandas ci sono gia'.
- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- La chiave del `column_config` e' il nome della colonna, `equiv_speed_kmh`:
  una chiave sbagliata viene ignorata senza errori.
- `training-activity-reports` usa `list_activities()` fuori da Streamlit e
  deve continuare a girare, colonna nuova compresa.

## Rischi

- **Il primo avvio rifa' tutta la cache**: qualche minuto in cui la pagina
  sembra ferma. Succede una volta sola e va scritto nel report.
- **Il rumore dell'altimetro** gonfia salite e discese. La media a 30s e' la
  stessa del grafico. Se i numeri escono strani si allarga la finestra, senza
  cambiare il modello.
- **La tabella si allarga** di una colonna: controllare a 1280px che non
  spinga fuori pagina niente.

## Verifica

Non esiste una suite di test; l'app gira su http://localhost:8501.

1. Una corsa quasi piatta (D+ basso, da scegliere guardando `total_ascent_m`):
   `equiv_speed_kmh` entro ±2% di `avg_speed_kmh`.
2. Una corsa con D+ alto, o un'escursione: velocita' equivalente
   chiaramente sopra quella media.
3. Le uscite in bici hanno la cella vuota.
4. Il conteggio per sport delle celle piene e vuote, stampato.
5. Due rebuild di fila danno gli stessi numeri.
6. Lo scatter della scheda di dettaglio e' colorato come prima.
