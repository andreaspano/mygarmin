---
status: done
---

# La Week:Training in due colonne

Le informazioni della vista erano giuste e la pagina era brutta. Si rifa' la
forma **senza toccare il contenuto**: stesse tre card, stessi quattro numeri
del blocco, stessi sette giorni, stesse sedute, stesso commento.

## Cosa non andava, guardandola

Tre riquadri a tutta pagina, uno sotto l'altro, e dentro due elenchi che
della larghezza ne usavano **un quarto**: i sette giorni del piano e le
sedute occupavano la colonna di sinistra e lasciavano settecento pixel
bianchi a destra. Il commento, a tutta pagina, aveva righe da centoventi
battute. E le due liste — cosa era previsto e cosa e' successo — stavano
lontane proprio mentre dicono la stessa cosa da due parti: per confrontarle
si scorreva.

## La forma nuova

**Due colonne.** A sinistra il piano, a destra le sedute e sotto il commento
che le giudica.

```
┌─ Plan ──────────────┐  ┌─ Sessions ──────────┐
│ fase · settimana    │  │ Legnano Running     │
│ gara · bersaglio    │  │ Indoor Cycling      │
│                     │  └─────────────────────┘
│ Mon 26  Rest        │  ┌─ Comment ───────────┐
│ Tue 27  easy 5 km   │  │ A quiet start, and  │
│ ...                 │  │ that is all the ... │
└─────────────────────┘  └─────────────────────┘
```

Tre cose che vengono da sole, mettendole cosi':

- **i vuoti spariscono**, che ogni elenco ha la larghezza che gli serve;
- **previsto e fatto si leggono insieme**, uno accanto all'altro;
- **il commento prende la misura giusta** — mezza pagina sono circa settanta
  battute, e oltre quelle l'occhio perde il capo della riga dopo. Non si e'
  stretto il testo a mano: gliel'ha data la colonna.

Sotto i 900 px tornano in colonna, nell'ordine di prima.

## Work

- `WeekPage.tsx`: le tre card dentro `.week-work`, due `div` per le due
  colonne.
- `styles.css`:
  - `.week-work`, due colonne **senza pareggiare le altezze**. La griglia
    delle card (`.cards-grid`) le pareggia di proposito — due card di misure
    affiancate di altezza diversa si leggono come un errore di allineamento —
    ma qui sono due elenchi di lunghezza diversa per natura, sette giorni
    previsti contro le sedute che ci sono state, e allungare il piu' corto
    vuol dire un riquadro mezzo vuoto;
  - `.plan-days` col passo delle sedute nella colonna accanto: una riga ogni
    nove pixel, un filo di separazione, cosi' le due liste si corrispondono;
  - i riposi in secondo piano (`li.rest`), che l'occhio trovi le sedute senza
    contarle. E' la stessa riga, detta piu' piano;
  - i quattro numeri del blocco **a due a due** in mezza larghezza: su una
    riga sola «28 Feb 2027» arrivava addosso al bersaglio, che le colonne
    della griglia sono uguali e il contenuto no.
- `WeekPlanCard.tsx`: la classe `rest` sulle righe di riposo.

## Verifica

Il contenuto non deve cambiare: stesse card, stessi numeri, stesse righe.

## Come e' andata

Fatto guardando, non indovinando: **quattro giri di screenshot** in Firefox
headless, nei due temi, leggendo ogni volta l'immagine prima di decidere il
passo dopo. Senza quelli non si sarebbe visto ne' il vuoto a destra ne' i due
inciampi qui sotto, che sono nati proprio dalle correzioni.

**Il primo**: messe le due card affiancate nella griglia delle card, le
altezze si sono pareggiate e sotto le sedute e' rimasto un buco di trecento
pixel — il difetto di prima, piu' piccolo. Da li' `.week-work` con
`align-items: start` invece di riusare `.cards-grid`.

**Il secondo**: stretto il commento a 72 battute **restando a tutta pagina**,
meta' riquadro e' rimasto bianco, che e' peggio di una riga lunga. La misura
non si stringe dentro una cornice larga: si stringe la cornice. Da li' il
commento nella colonna di destra, dove la misura giusta arriva senza
chiederla.

### Come e' stato verificato

- **Il contenuto, letto dal DOM dopo**: tre card `[Plan, Sessions, Comment]`;
  i quattro numeri `base`, `1 of 18`, `28 Feb 2027`, `2:20`; i sette giorni
  da «Mon 26 Oct Rest» a «Sun 1 Nov Running · long · 14 km»; le due sedute
  con distanza e durata; i due «written at»; il commento di 595 battute.
  Identico a prima.
- **I due temi**, chiaro e scuro, a 1280 px.
- **Il telefono**, a 760 px: le tre card tornano in colonna nell'ordine
  Plan, Sessions, Comment.
- **La Day non e' stata toccata**: il suo commento e' largo 1042 px come
  prima. La regola che stringeva la prosa era scritta su `.comment-card`, che
  e' anche la sua, ed e' stata tolta quando il commento della Week e' andato
  in colonna.
- `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_73'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. E' solo forma.

Dopo il revert, rifare il merge di `todo_73` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
