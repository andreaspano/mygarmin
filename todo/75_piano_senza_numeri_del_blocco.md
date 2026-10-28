---
status: done
---

# La card Plan: solo i sette giorni, allineata alle sedute

Tre cose chieste guardando la pagina:

1. **via i quattro numeri del blocco** dalla card Plan della Week:Training —
   fase, settimana del blocco, gara, bersaglio;
2. **allineare Plan e Sessions**;
3. **icone della stessa misura**.

## Perche' i quattro numeri stavano male li'

Sono **del blocco, non della settimana**: fase `base`, `1 of 18`, la gara del
28 febbraio, il bersaglio 2h20. Non cambiano da un lunedi' all'altro, e in
una card che risponde a «cosa chiedeva questa settimana» occupavano due righe
in cima per dire qualcosa che vale per diciotto settimane di fila.

E soprattutto **spingevano in basso la riga del lunedi'**, disallineandola
dalla prima seduta della colonna accanto: le due liste partivano a
settantacinque pixel di distanza.

Restano nella vista Plan, dove il documento li vuole e dove si va per sapere
dove sta questa settimana nel blocco.

## L'allineamento

Tolti i numeri, le due card cominciano con la loro lista subito sotto
l'intestazione. Perche' le righe si corrispondano servono le stesse misure:
stessa icona (26 px, erano 22 e 30), stesso riempimento (`10px 8px`) e lo
stesso margine in testa alla lista.

Le righe **non si corrispondono una a una**, e non devono: il piano ha sette
giorni, le sedute sono quelle che ci sono state, e la prima seduta e' di
martedi' mentre la prima riga del piano e' di lunedi'. Allineare per riga
direbbe una cosa falsa. Quello che si allinea e' **l'inizio delle due liste**
e il loro passo.

## Work

- `WeekPlanCard.tsx`: via `<WeekPlanStats>` dalla card compatta, che torna
  privata — la usa solo la card della vista Plan; icone a 26 px.
- `WeekPage.tsx`: le icone delle sedute da 30 a 26 px.
- `styles.css`: `.plan-days` col riempimento e il margine delle sedute.

## Come e' andata

Fatto, e misurato dal DOM invece che a occhio:

| | Plan | Sessions |
|---|---|---|
| card | 404 px | 404 px |
| intestazione | 425 px | 425 px |
| **prima riga** | **457 px** | **457 px** |
| icona | 26 px | 26 px |

Le icone restano a sei pixel di distanza in verticale, e li' si ferma: una
riga di seduta e' alta 60 px perche' porta due righe di testo, una del piano
46 perche' ne porta una. Pareggiarle vorrebbe dire cento pixel di aria in
piu' nella card del piano per far combaciare due cerchi.

Verificato anche che i quattro numeri **ci sono ancora nella vista Plan**
(`Phase=base`, `Block week=1 of 18`, `Race=28 Feb 2027`, `Target=2:20`) e che
la Day non e' stata toccata: la sua card Plan ha ancora l'icona grande da 44
px, che li' e' un titolo e non una riga di elenco.

Nei due temi, `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_75'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_75` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
