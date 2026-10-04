---
status: todo
---

# ML: efficienza aerobica nel tempo (velocita' a parita' di battiti)

Il VO2max dell'orologio si muove di decimi ed e' una stima di Garmin. Un
indice piu' diretto: **quanto vai veloce a una certa frequenza cardiaca**. Se
a 135 bpm corri piu' veloce di un anno fa, la base aerobica e' migliorata.
Con le corse dal 2016 si vede la tendenza su dieci anni.

**Da fare dopo il todo 19** (pacchetto `analysis/`).

## Work

- `analysis/aerobic_efficiency.py`:
  - per ogni corsa, dai `records`: si tengono i tratti **stabili** (almeno 5
    minuti senza pause, pendenza fra -2% e +2%, dopo i primi 10 minuti di
    riscaldamento), e su quelli si stima la retta velocita' ~ FC;
  - l'indice della corsa e' la velocita' prevista a una FC di riferimento
    fissa (`REFERENCE_HR = 135`, nel codice con il motivo);
  - **deriva cardiaca** della corsa: di quanto sale la FC a velocita'
    costante fra prima e seconda meta' (un altro segno di efficienza);
  - tendenza nel tempo: media mobile di 8 settimane dell'indice, e i punti di
    cambio (una regressione a tratti semplice, o `ruptures` se serve:
    in quel caso va nominato qui prima di partire).
- CLI `training-aerobic-efficiency` e `make aerobic_efficiency`: tabella
  per anno e ultimi 6 mesi; report in
  `summary/06.analysis/aerobic_efficiency.md`, in inglese.

## Vincoli

- Solo corse (`sport == "running"`), e solo quelle con FC al secondo.
- Nessuna dipendenza nuova oltre a quelle del todo 19.
- Il calcolo per corsa e' costoso: si fa una volta e si mette in cache
  (tabella in `activities.db` con il suo salto di `logic_version`, come il
  todo 13), non a ogni giro.
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Caldo, terreno, fatica** cambiano la FC a parita' di velocita': l'indice
  di una corsa da sola e' rumoroso, conta la tendenza.
- **Sensore**: la FC dal polso sbaglia nei primi minuti e negli scatti; per
  questo i primi 10 minuti si scartano.
- **Corse senza tratti stabili** (trail, ripetute) non hanno indice: restano
  fuori, non diventano zero.

## Verifica

1. Una corsa facile in piano: indice plausibile (velocita' prevista vicina a
   quella media della corsa, se la FC media e' vicina a 135).
2. Una corsa di trail: nessun indice, con il motivo.
3. Il numero di corse con indice per anno, stampato: nessun anno con valori
   inventati.
4. Due giri: stessi numeri.
