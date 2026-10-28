---
status: done
---

# Il commento in testa, il piano e le sedute sotto

Il todo 73 aveva messo la Week:Training in due colonne: a sinistra il piano,
a destra le sedute e sotto il commento. Andrea lo vuole **sopra**, a tutta
pagina, con piano e sedute affiancati sotto di lui.

```
┌─ Comment ─────────────────────────────────────┐
│ A quiet start, and that is all the week is ... │
└────────────────────────────────────────────────┘
┌─ Plan ──────────────┐  ┌─ Sessions ──────────┐
│ Mon 26  Rest        │  │ Legnano Running     │
│ Tue 27  easy 5 km   │  │ Indoor Cycling      │
│ ...                 │  └─────────────────────┘
└─────────────────────┘
```

E' il verdetto, e un verdetto si legge per primo — la stessa posizione che il
Summary ha nello Snap, del giorno e della settimana.

## Quello che si paga, detto chiaro

Il commento nella colonna di destra (todo 73) risolveva due cose che adesso
tornano:

- **la misura della riga.** A mezza pagina il testo veniva a settanta
  battute, che e' la misura in cui l'occhio trova il capo della riga dopo. A
  tutta pagina sono centoventi.
- **il buco sotto le sedute.** La colonna di destra finisce con l'elenco, e
  se le sedute sono poche — due, in una settimana a meta' — sotto resta
  bianco fino in fondo alla colonna del piano.

Nessuna delle due si sistema stringendo il testo: una misura corta dentro
una cornice larga lascia mezza card vuota, che e' peggio di una riga lunga.
Si e' provato nel todo 73 e si e' buttato. **La misura non si stringe dentro
una cornice larga: si stringe la cornice** — ed e' esattamente quello a cui
si rinuncia mettendo il commento in testa.

Il Summary della Day fa la stessa cosa e **se la cava**: anche li' il testo e'
stretto (510 px) dentro una card larga, ma la card e' a fondo scuro, e il
vuoto a destra si legge come una fascia invece che come un buco. Il commento
e' una card chiara come le altre, e quel trucco non ce l'ha.

## Work

- `WeekPage.tsx`: la card del commento esce dalla colonna di destra e va
  prima di `.week-work`.

Niente altro: la griglia, le righe del piano e i riposi in secondo piano
restano quelli del todo 73.

## Come e' andata

Fatto, un blocco spostato. Verificato che **il contenuto non e' cambiato**,
leggendo dal DOM: `[Comment, Plan, Sessions]` in quest'ordine, sette giorni,
due sedute, i quattro numeri del blocco, il commento di 595 battute. La prosa
e' larga 1042 px, com'era prima del todo 73.

Nei due temi a 1280 px e a 760 px, dove le tre card tornano in colonna nello
stesso ordine. `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_74'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. E' solo forma, e il revert riporta il
commento nella colonna di destra.

Dopo il revert, rifare il merge di `todo_74` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
