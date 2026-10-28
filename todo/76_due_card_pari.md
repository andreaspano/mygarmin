---
status: done
---

# Plan e Sessions alte uguali

Il todo 73 aveva messo le due card affiancate **senza pareggiarne le
altezze**, con questo ragionamento: sono due elenchi di lunghezza diversa per
natura — sette giorni previsti contro le sedute che ci sono state — e
allungare il piu' corto vuol dire un riquadro mezzo vuoto.

Guardandola, Andrea ha deciso il contrario: **il gradino fra le due card da'
piu' fastidio del bianco in fondo alle sedute.** Due riquadri affiancati che
finiscono a quote diverse si leggono come una riga sfaldata, ed e' lo stesso
motivo per cui la griglia delle card (`.cards-grid`) le pareggia da sempre.

Quindi la regola della pagina torna a essere quella di tutte le altre: la
piu' alta decide — di solito il piano, che ha sempre sette righe — e l'altra
si allunga.

## Work

- `styles.css`: via `align-items: start` da `.week-work`, e con lui la regola
  `.week-work > div`, che serviva a impacchettare in alto i contenuti delle
  due colonne.
- `WeekPage.tsx`: via i due `div` che avvolgevano le colonne. Reggevano due
  card ciascuno quando il commento stava a destra (todo 73); dal todo 74 il
  commento e' in testa e ne tengono una sola, quindi non servono piu' — e
  anzi impedivano alla card di allungarsi, che a stirarsi era il `div` e non
  lei.

Nient'altro: contenuto, righe, icone e allineamento della prima riga restano
quelli del todo 75.

## Come e' andata

Fatto, e misurato: le due card vanno **da 404 a 832 px tutte e due**, stessa
altezza al pixel. Sette righe nel piano, due sedute, come prima.

Sotto i 900 px la griglia torna a una colonna e le card tornano alte quanto
il loro contenuto: li' non c'e' nessun gradino da pareggiare, e stirarle
sarebbe aria e basta.

Nei due temi, `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_76'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_76` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
