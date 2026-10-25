---
status: done
---

# Il backfill non deve chiudere un periodo che non e' finito

Sabato 24 ottobre alle 22:32 un backfill ha scritto il riassunto di
chiusura della settimana del 19 ottobre. La settimana aveva ancora la
domenica davanti.

Il testo si legge come un verdetto: *"A week that gave more than it cost"*.
Gli 8 km della domenica mattina, quelli che hanno portato il VO2max a 42,2,
in quel riassunto non ci sono — non erano ancora stati corsi.

Il cron non c'entra: `0 22 * * 0` e' la domenica alle 22, e in
`mygarmin-report.log` di giri settimanali non ce n'e' nemmeno uno. Il
backfill e' stato lanciato a mano dopo il merge del todo 50.

## Perche' succede

Due pezzi che da soli stanno in piedi e insieme no.

**Il backfill usa sempre il giro di chiusura.** In `sections.py:169`:

```python
_WEEK_BACKFILL = (
    ("end", ("health", "recovery", "load", "fitness", "training", "next", "summary_end")),
    ("start", ("summary_start",)),
)
```

Nessuno guarda se la settimana e' finita. E il momento `end` dice
all'agente (`sections.py:149`): *"This is the Sunday evening run: the week
is finished, and the next one starts tomorrow."* Su una settimana in corso
quella riga e' falsa.

**L'intervallo arriva fino al periodo in corso.** In `refresh.py:646` il
`last` passato a `_backfill_cli` e' **il lunedi' della settimana di oggi**
(per il giornaliero, oggi). `--to` prende quello di default, e il controllo
e' `end > last`: il periodo in corso ci sta dentro.

Il commento sopra `_WEEK_BACKFILL` il presupposto lo dichiara —
*"li' si scrive il presente e qui un periodo finito"* — ma niente lo fa
rispettare.

**Il giornaliero ha la stessa forma.** `_DAY_BACKFILL` apre con il giro
`evening` e chiude con `summary_evening`: su un backfill che arriva a oggi,
prima di sera, scrive la sera di una giornata che non e' finita.

## La scelta

Il backfill riscrive **periodi conclusi**, e basta.

- `--to` di suo si ferma **all'ultimo periodo finito**: la settimana prima
  di quella in corso, il giorno prima di oggi.
- Un `--to` esplicito piu' avanti e' un errore del comando, con scritto
  cosa usare al posto suo (`training-weekly-report` senza `--from`, che il
  presente lo scrive gia' bene).
- Il guardiano sta anche dentro `backfill()`, non solo nella riga di
  comando: l'invariante e' della funzione — il suo docstring lo dichiara
  gia' — e chi la chiamasse domani senza passare dal comando la trova
  rispettata. Oggi a chiamarla c'e' solo `_backfill_cli`.

Scartate due alternative:

- **Scrivere il periodo in corso col momento giusto** (quello che userebbe
  il timer in questo istante). Fa quello che serve, ma raddoppia la logica
  dei momenti in un posto dove oggi non c'e' e che il todo 50 aveva
  apposta tenuto semplice.
- **Saltarlo in silenzio.** Un backfill che dice "riscrivo 8 settimane" e
  ne riscrive 7 mente nel riepilogo. Se il limite c'e', va stampato.

## Work

### 1. L'ultimo periodo finito — `src/training/api/refresh.py`

Una funzione sola che lo dice, perche' serve in due posti e la regola non
deve stare scritta due volte:

- settimanale: il lunedi' della settimana **precedente** a quella di oggi;
- giornaliero: **ieri**.

### 2. Il controllo nel comando — `_backfill_cli`

`--to` senza valore prende l'ultimo finito invece di `last`. Un `--to`
oltre quello fa `parser.error` con il messaggio che manda al comando
giusto. Resta l'errore di adesso per l'intervallo al contrario.

Il `last` che `main` passa serve ancora agli altri controlli (`--week`,
`--day`): non si tocca.

### 3. Il controllo nella funzione — `backfill()`

Se l'intervallo arriva oltre l'ultimo finito, i periodi in piu' **non si
scrivono** e il riepilogo lo dice: un campo accanto a `subjects` con quanti
ne sono stati lasciati fuori, e la riga stampata che lo riporta. Niente
tagli muti.

Dal comando quella riga non si vede mai, perche' il controllo del punto 2
ferma l'intervallo prima: e' la rete per chi chiama la funzione
direttamente.

### 4. Rimettere a posto la settimana del 19 ottobre

Il giro della domenica sera riscrive `summary_end.md` da se', perche' il
percorso dei timer non salta le sezioni che esistono. Se al momento di
implementare e' gia' passato, non c'e' niente da fare; se no, si lascia
fare a lui. **Non si riscrive a mano niente dentro `summary/`.**

## Vincoli

- Niente dipendenze nuove.
- La riga di comando non cambia forma: stessi `--from` e `--to`.
- Il giro dei timer non si tocca: quello il presente lo scrive apposta, ed
  e' giusto cosi'.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Un backfill che arriva a ieri e' quasi sempre quello che si vuole**, ma
  chi lanciava `--from X` aspettandosi di toccare anche la settimana in
  corso adesso vede un periodo in meno. Per questo il riepilogo deve dirlo
  a chiare lettere, non lasciarlo dedurre dai numeri.
- **Il confine della settimana e' il lunedi', non le 22 della domenica.**
  Una settimana finita domenica resta "in corso" per il backfill fino al
  lunedi'. E' voluto: il giro delle 22 e' quello che la chiude, e un
  backfill lanciato domenica alle 23 non deve rifare quello che il timer ha
  appena scritto.

## Verifica

1. `training-weekly-report --from 2026-09-28` (senza `--to`) si ferma alla
   settimana prima di quella in corso, e lo stampa.
2. `--to` sulla settimana in corso esce con l'errore e il consiglio.
3. `backfill()` chiamata a mano con un intervallo che sborda rende il
   riepilogo con i periodi lasciati fuori contati.
4. Lo stesso per il giornaliero: `--from` senza `--to` arriva a ieri.
5. `uv run python -c "from training.api import refresh"` e un backfill vero
   su un intervallo tutto nel passato: si comporta come prima, nessuna
   sezione in meno.

## Come e' andata

Fatto come previsto, tutto in `refresh.py`.

`_last_complete(kind, today)` sta accanto a `_subjects` e dice l'ultimo
periodo concluso: ieri, o il lunedi' della settimana prima di quella in
corso. Da li' in giu' due guardie: `_backfill_cli` ci appoggia il valore di
`--to` e ci misura un `--to` esplicito, e `backfill()` toglia da `subjects`
quello che sborda contandolo in `left_out`.

Tre cose trovate per strada:

- **Il todo aveva una riga falsa.** Diceva che `backfill()` la chiama anche
  l'API: non e' vero, l'unica chiamata e' `_backfill_cli`. La guardia nella
  funzione resta — l'invariante e' suo e il docstring lo dichiarava gia' —
  ma la ragione era un'altra, e la riga e' stata corretta.
- **La riga stampata su `left_out` dal comando non si vede mai**, perche' il
  controllo a monte ferma l'intervallo prima di chiamare la funzione. E' la
  rete per chi `backfill()` la chiama direttamente, e sta scritto nel punto
  3 del Work invece di lasciarlo scoprire a chi legge il codice.
- **`date.today()` si legge due volte**, una per guardia. Un backfill che
  attraversa la mezzanotte userebbe due confini diversi: il secondo e' piu'
  stretto del primo, quindi al massimo lascia fuori un periodo in piu' e lo
  conta. Non vale un parametro in piu' nella firma.

La settimana del 19 ottobre non e' stata toccata a mano: la riscrive il giro
delle 22 di domenica, che al contrario del backfill non salta le sezioni che
esistono gia'.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_56'$" --format=%H -1)
```

Effetti fuori dal repo: **i report gia' scritti restano come sono**.
`summary/` e' in `.gitignore` (riga 15), quindi non e' git a tenerli: il
revert rimette il backfill com'era, non disfa nessun testo. In particolare
il `summary_end.md` scritto in anticipo resta finche' un giro dei timer non
lo riscrive.

Dopo il revert, rifare il merge di `todo_56` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
