---
status: todo
---

# ML: quanto sonno e stress cambiano la prestazione del giorno dopo

Una notte corta o una giornata stressante ti fanno andare piu' piano, a
parita' di battiti, il giorno dopo? E di quanto? Qui si stima l'effetto,
tenendo conto delle altre cose che cambiano insieme (il carico dei giorni
prima, la stagione, il tipo di seduta).

**Da fare dopo i todo 19 e 21**: usa `daily_frame()` e l'indice di
efficienza aerobica per corsa. Se il todo 23 e' fatto, il tipo di seduta
entra come variabile.

## Work

- `analysis/sleep_stress_effect.py`:
  - una riga per corsa con indice di efficienza (todo 21): le ore e il
    punteggio della notte prima, lo stress del giorno prima, il TRIMP dei 3
    giorni prima, la temperatura se disponibile (oggi no: si lascia fuori e
    si dice), il mese, il tipo di seduta (todo 23, se c'e');
  - **modello a effetti misti** (`statsmodels`, `mixedlm`): l'indice come
    risposta, sonno e stress come effetti da stimare, l'anno come gruppo
    (la forma di fondo cambia da un anno all'altro e non deve confondere
    l'effetto);
  - per confronto, una regressione semplice senza gruppi;
  - il risultato in parole: "una notte sotto le 6.5 ore e' associata a un
    indice piu' basso del X%, con un intervallo da A a B".
- CLI `training-sleep-stress-effect` e `make sleep_stress_effect`; report in
  `summary/06.analysis/sleep_stress_effect.md`, in inglese, per l'atleta.
- **Dipendenza nuova**: `statsmodels` (via `uv add`).

## Vincoli

- Solo dati locali; niente pagine nell'app.
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Associazione, non causa**: dormi meno anche quando sei stressato, malato
  o in viaggio. Il report dice "associato a", mai "causa".
- **Pochi dati di salute prima del 2023**: il modello usa solo le corse dal
  2023 con indice e sonno; il numero va stampato.
- **Effetti piccoli**: se l'intervallo comprende lo zero, il report dice che
  non si vede un effetto, invece di riportare la stima come se fosse certa.

## Verifica

1. Dati sintetici con un effetto noto del sonno: il modello lo ritrova
   (entro l'intervallo).
2. Sui dati veri: numero di corse usate, stima e intervallo stampati.
3. Il report non usa mai "causes" / "because of".
4. Due giri: stessi numeri.
