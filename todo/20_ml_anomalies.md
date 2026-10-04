---
status: todo
---

# ML: giorni anomali nei segnali di recupero

Segnalare i giorni in cui HRV, FC a riposo, stress o sonno escono dalla tua
normalita': spesso sono il primo segno di una malattia in arrivo o di troppa
fatica, prima che la readiness lo dica.

**Da fare dopo il todo 19**: usa `analysis/dataset.daily_frame()`.

## Work

- `analysis/anomalies.py`:
  - **baseline personale mobile**: per ogni metrica (`hrv_last_night`,
    `resting_hr`, `stress_avg`, `sleep_hours`, `body_battery_high`), mediana
    e deviazione robusta (MAD) dei 28 giorni **precedenti**, senza il giorno
    stesso;
  - **z-score robusto** per giorno e metrica; un giorno e' anomalo se una
    metrica passa la soglia (|z| >= 2.5) o se due insieme passano 2 (per
    esempio HRV giu' e FC a riposo su, la coppia tipica della malattia);
  - in piu', un `IsolationForest` di scikit-learn sulle stesse metriche,
    come secondo parere: si riportano i giorni in cui i due metodi sono
    d'accordo;
  - per ogni giorno anomalo: quali metriche, in che direzione, e se nei 2
    giorni prima c'era carico alto (cosi' si distingue "fatica da
    allenamento" da "qualcos'altro").
- CLI `training-anomalies [--days N]` e `make anomalies`: gli ultimi N giorni
  (default 60) con i giorni anomali; report in
  `summary/06.analysis/anomalies.md`, in inglese, per l'atleta.

## Vincoli

- Nessuna dipendenza nuova oltre a scikit-learn (todo 19).
- Solo dati locali; niente pagine nell'app.
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Senza etichette** non si sa quali anomalie fossero vere: la soglia e' una
  scelta, e va scritta nel report.
- **Giorni senza orologio** (settembre 2026, 1-6) non sono anomali: sono
  vuoti. Non entrano ne' nella baseline ne' tra le anomalie.
- **Inizio della serie**: i primi 28 giorni non hanno baseline e si saltano.

## Verifica

1. Una serie finta con un picco messo a mano: il picco viene trovato, i
   giorni normali no.
2. Sui dati veri: il numero di giorni anomali e' una piccola parte del
   totale (sotto il 5%); se e' di piu', la soglia e' sbagliata.
3. I giorni dall'1 al 6 settembre 2026 non compaiono.
4. La baseline di un giorno non usa quel giorno ne' i successivi.
