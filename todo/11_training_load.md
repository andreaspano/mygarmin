---
status: todo
---

# Recovery: carico acuto e carico cronico

Il report di forma del 26 settembre 2026 dice "carico acuto 408 su una base di
348, bilancio ottimale". E' il numero piu' utile per capire se si sta
costruendo in modo graduale o se il carico sta salendo di colpo, ma nell'app
non c'e'.

Qui si aggiunge alla pagina Recovery un grafico del carico: acuto (7 giorni) e
cronico (4 settimane) giorno per giorno, con la fascia in cui Garmin considera
l'acuto ottimale.

**Dipende dal todo 10**: il loader `load_health()` e la pagina Recovery devono
esistere ed essere uniti a `main`.

## Dati, verificato

`DATA_DIR/health/training_status/<giorno>.json`, dentro
`mostRecentTrainingStatus.latestTrainingStatusData`. Quel dizionario ha **come
chiave l'id del dispositivo** (`3600579909`), non un nome fisso: si prende il
primo valore, oppure quello con `primaryTrainingDevice == true` se ce n'e' piu'
di uno. Da li':

| grandezza | campo | 21 set 2026 |
|---|---|---|
| giorno | `calendarDate` | "2026-09-21" |
| carico acuto | `acuteTrainingLoadDTO.dailyTrainingLoadAcute` | 494 |
| carico cronico | `acuteTrainingLoadDTO.dailyTrainingLoadChronic` | 345 |
| limite basso fascia ottimale | `acuteTrainingLoadDTO.minTrainingLoadChronic` | 276.0 |
| limite alto fascia ottimale | `acuteTrainingLoadDTO.maxTrainingLoadChronic` | 517.5 |
| rapporto acuto/cronico | `acuteTrainingLoadDTO.dailyAcuteChronicWorkloadRatio` | 1.4 |
| stato ACWR | `acuteTrainingLoadDTO.acwrStatus` | "OPTIMAL" |
| stato allenamento | `trainingStatusFeedbackPhrase` | "PRODUCTIVE_3" |

Nonostante il nome, `min/maxTrainingLoadChronic` sono i limiti della fascia in
cui deve stare l'**acuto**: sono 0.8 e 1.5 volte il cronico (345 x 0.8 = 276,
345 x 1.5 = 517.5).

## Work

- Aggiungere le colonne della tabella a `load_health()` (todo 10), con la
  stessa lettura difensiva.
- Nella pagina Recovery, un grafico **Training load** in cima, sopra la
  readiness: il carico e' la causa, gli altri grafici sono l'effetto.
  - fascia ottimale come area grigia chiara fra minimo e massimo;
  - linea del cronico, tratteggiata;
  - linea dell'acuto, piena e in evidenza;
  - tooltip con giorno, acuto, cronico, rapporto e stato.
- Stesso asse x e stesso periodo degli altri grafici della pagina.
- Lo stato di allenamento ("Productive", "Maintaining", ...) come metrica nella
  fila in cima, senza il suffisso numerico (`PRODUCTIVE_3` diventa
  "Productive").

## Vincoli

- Niente CSS e niente HTML. Commenti in italiano senza accenti, UI in inglese.
- Non ricalcolare il carico dalle attivita': Garmin lo calcola con l'EPOC dei
  file e un nostro numero non tornerebbe con quello dell'orologio. Si mostra
  quello di Garmin.

## Rischi

- I giorni vecchi scaricati col backfill del todo 10 potrebbero non avere
  `acuteTrainingLoadDTO`, o avere lo stato "di oggi" invece di quello di quel
  giorno. Va controllato su qualche file dopo il backfill: se il valore non
  dipende dalla data chiesta, il grafico si limita ai giorni scaricati il
  giorno stesso.
- Se l'orologio cambia, cambia la chiave del dizionario: non va scritta nel
  codice.

## Verifica

1. Il 21 settembre 2026: acuto 494, cronico 345, fascia 276-517.5, rapporto
   1.4.
2. Il 26 settembre 2026: acuto 408, cronico 348, stato "Productive".
3. L'acuto sta dentro la fascia su tutto il periodo di settembre.
4. Un giorno senza file lascia un buco, non uno zero.
5. Nessuna eccezione: `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity`, `make backfill_activity_names` o
`make backfill_health`: chiamano l'API Garmin e scrivono nell'albero dati.
