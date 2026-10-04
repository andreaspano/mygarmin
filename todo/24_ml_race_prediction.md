---
status: todo
---

# ML: tempi previsti su 5 km, 10 km e mezza maratona

Dalle tue migliori prestazioni e dal VO2max, prevedere i tempi su 5 km,
10 km e mezza maratona, e seguire come cambiano mese per mese.

**Da fare dopo il todo 13** (record personali: tabella `best_efforts`) e
**dopo il todo 21** (indice di efficienza aerobica).

## Work

- `analysis/race_prediction.py`, tre stime messe a confronto:
  - **Riegel**: dal miglior tratto recente (ultimi 90 giorni, tabella
    `best_efforts` del todo 13) su una distanza, il tempo sulle altre con
    `T2 = T1 * (D2 / D1) ** 1.06`; l'esponente si adatta anche ai tuoi dati
    se ci sono abbastanza distanze diverse;
  - **VDOT / VO2max**: dal VO2max dell'orologio (`health_daily.vo2max`, o
    `activities.vo2max`) con le tabelle di Daniels (formula, non tabella
    copiata);
  - **regressione** sui tuoi dati: tempo sul tratto migliore del mese ~
    indice di efficienza aerobica (todo 21) + volume delle 8 settimane prima
    (`LinearRegression` di scikit-learn).
- Per ogni mese degli ultimi 2 anni, i tre tempi previsti per distanza.
- CLI `training-race-prediction` e `make race_prediction`: i tempi previsti
  di oggi con un intervallo (il minimo e il massimo dei tre metodi) e la
  tendenza; report in `summary/06.analysis/race_prediction.md`, in inglese.

## Vincoli

- Solo corse; solo dati locali; niente pagine nell'app.
- Nessuna dipendenza nuova oltre a scikit-learn (todo 19).
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Le tue corse sono quasi tutte facili**: i migliori tratti non sono gare,
  quindi le previsioni da Riegel saranno **pessimiste**. Va scritto nel
  report, non corretto in silenzio.
- **Distanze mai corse** (forse la mezza): la previsione e' un'estrapolazione
  e va segnata come tale.
- **VO2max dell'orologio** e' una stima che si muove poco: utile come
  confronto, non come verita'.

## Verifica

1. Riegel con valori noti (per esempio 5 km in 25:00 -> 10 km circa 52:07):
   il calcolo coincide.
2. VDOT con un valore noto dalle tabelle di Daniels: coincide entro pochi
   secondi.
3. Le tre stime per oggi sono nello stesso ordine di grandezza; se una e'
   lontanissima dalle altre, il report lo segnala.
4. Due giri: stessi numeri.
