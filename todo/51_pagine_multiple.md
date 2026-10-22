---
status: done
---

# Piu' di una pagina

La barra in alto elenca cinque pagine — Day, Week, Month, Recovery,
Activities — ma quattro sono scritte in grigio con `title="Coming soon"`:
l'unica che esiste e' la Day. `main.tsx` monta `<DayPage />` e basta, non
c'e' nessun router.

Questo todo non porta contenuti nuovi: porta **il posto dove metterli**. La
Week diventa la seconda pagina vera, con quello che si puo' gia' mostrare
senza un conto nuovo; i numeri della settimana e le sue fasce arrivano col
todo 52, i testi col 53.

## Decisioni

Prese con Andrea il 2026-10-22:

- **Tre todo invece di uno.** 51 le pagine, 52 i dati e i grafici, 53 il
  report. Il primo si prova da solo: la pagina esiste, ci si naviga, mostra
  la settimana giusta.
- **Niente dipendenze nuove, nessun router di libreria.** La Day gestisce
  gia' il suo stato nell'URL con `pushState` e `popstate`
  (`DayPage.dayFromUrl`): la stessa idea, allargata.

## Work

### 1. Dove sta la pagina nell'URL

`?page=week`, accanto a quello che c'e' gia'. Senza `page` si apre la Day,
cosi' tutti i collegamenti di oggi (`?day=2026-10-07`) continuano a
funzionare e non serve toccare `tailscale serve` ne' il modo in cui l'API
serve i file.

La settimana sta in `?monday=2026-10-19`, sempre un lunedi: fuori range o
malformato, la settimana di oggi.

**Niente percorsi veri** (`/week`): richiederebbero il fallback a
`index.html` nel server di sviluppo e in quello dell'API, e non vale il
prezzo per due pagine.

### 2. Il router — `frontend/src/main.tsx` e un `App.tsx` nuovo

Un componente che legge `page` dall'URL, sceglie fra `DayPage` e
`WeekPage`, e ascolta `popstate`. Una funzione sola per cambiare pagina, che
fa `pushState` e aggiorna lo stato — la stessa che usa `changeDay` oggi,
estratta dove la possono usare tutte e due.

### 3. La barra — `frontend/src/components/TopBar.tsx`

Day e Week diventano collegamenti veri, con `aria-current` su quella aperta.
Month, Recovery e Activities restano grigie: la barra tiene la sua forma e
si vede dove si sta andando.

### 4. La pagina — `frontend/src/components/WeekPage.tsx`

Con quello che **gia' esiste nell'API**, senza aggiungere endpoint:

- **L'intestazione**: `Week 43 · October 2026`. Il numero e' quello ISO, il
  mese e' quello del **giovedi** — la regola ISO per le settimane a cavallo
  di due mesi (la 5 del 2026 va dal 26 gennaio al 1 febbraio ed e' di
  gennaio). Frecce avanti e indietro fra le settimane, e un tasto per
  tornare all'ultima, come la Day.
- **La striscia dei sette giorni**: `WeekStrip` cosi' com'e', che prende
  gia' `start`, `end`, le attivita' e le icone. Un giorno si clicca e si
  apre la Day di quel giorno.
- **La card Training**: le sedute della settimana, da
  `GET /api/activities?start=&end=` che c'e' gia'. Il grafico delle sedute e
  la torta delle zone sono del todo 52.

Le card Health, Load, Recovery e Fitness **non ci sono ancora**: i loro
numeri settimanali li costruisce il todo 52.

## Vincoli

- Nessuna dipendenza nuova: niente react-router.
- Nessun endpoint nuovo: si usa quello che c'e'.
- Il modello dell'API non cambia, quindi `make frontend_types` deve lasciare
  `schema.ts` identico.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Una pagina a meta'.** Finche' non arriva il 52 la Week mostra la
  striscia e le sedute, e basta. E' voluto, ma va detto: non e' la pagina
  finita.
- **`?page=` e' meno elegante di `/week`**, e se un giorno le pagine
  diventassero molte converrebbe cambiare. Per due e' la scelta che non
  costa niente.
- **`WeekStrip` e' nata per la Day** e mostra otto giorni con quello scelto
  evidenziato. Sulla Week ne servono sette senza selezione: o prende un
  parametro, o la si lascia com'e' accettando l'ottavo giorno.

## Verifica

1. `npm run typecheck` e `npm run build`; `make frontend_types` non cambia
   `schema.ts`.
2. In Firefox headless: `?page=week` apre la Week, `?` apre la Day,
   `?day=2026-10-07` apre ancora la Day di quel giorno.
3. Il tasto indietro del browser torna alla pagina precedente, e la barra
   segna quella giusta.
4. Il titolo su una settimana a cavallo di due mesi: lunedi 26 gennaio 2026
   deve dare `Week 05 · January 2026`.
5. Un clic su un giorno della striscia apre la Day di quel giorno.
6. Nessun errore in console, nei due temi.

## Come e' andata

Fatto come scritto, con due scelte prese per strada.

- **`pushUrl` emette un `popstate` finto.** Il browser lo manda solo su
  avanti e indietro, quindi un tasto dentro la pagina non avvisava nessuno:
  il primo tentativo di `openDay` finiva con un `window.location.reload()`,
  che e' rozzo. Con l'evento sintetico `App` e le pagine si aggiornano da
  sole e la navigazione e' davvero senza ricarica — provato: clic su una
  seduta, la Day compare, il tasto indietro riporta alla Week.
- **`openDay` toglie anche `monday` dall'URL.** Senza, restava appeso
  (`?monday=2026-10-12&day=2026-10-15`): la Day lo ignora, ma un indirizzo
  che si copia e si manda deve essere pulito.

Gli aiuti ISO (`mondayOf`, `isoWeek`, `weekLabel`) sono stati confrontati
con il calendario di Python su sette casi difficili — i due scavalchi
d'anno, la settimana 53 del 2026, la 5 a cavallo fra gennaio e febbraio — e
danno gli stessi numeri.

La barra in alto usa collegamenti veri (`<a href>`), quindi Day e Week si
aprono anche in una scheda nuova. Dentro la pagina, invece, si naviga con
`pushUrl`.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_51'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. La pagina Week non scrive niente: legge
`/api/activities` e `/api/sports`, che esistevano gia'. Dopo il revert un
indirizzo `?page=week` apre la Day, come prima.

Dopo il revert, rifare il merge di `todo_51` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
