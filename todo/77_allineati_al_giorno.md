---
status: done
---

# Plan e Sessions allineati al giorno

Le due card erano affiancate e alte uguali (todo 73 e 76), ma le righe non si
corrispondevano: il piano aveva sette giorni in fila, le sedute erano un
elenco di quello che c'era stato, e per sapere se martedi' avevi fatto quello
che era previsto bisognava contare le righe con il dito.

Adesso **ogni seduta sta sulla riga del suo giorno**. Il martedi' del piano e
la corsa di martedi' sono sulla stessa linea, e un giorno senza sedute lascia
la riga vuota.

## Perche' due griglie non bastano

Ogni card e' un riquadro suo, con la sua griglia, e una griglia conosce solo
le proprie altezze. Se a destra la riga del martedi' e' alta sessanta pixel
(una seduta porta due righe di testo) e a sinistra quarantasei, le due
colonne si sfalsano da li' in giu'. Pareggiare a mano con un'altezza fissa
regge finche' non capita **un giorno con due sedute**, e capita.

La soluzione e' che **le righe non siano di ogni card ma della pagina**: una
per il titolo, sette per i sette giorni, una per il piede. Le due card se le
prendono con `subgrid`, e allora la riga del martedi' e' una sola, alta
quanto il piu' alto dei due contenuti, e li alza tutti e due insieme.

## Work

- `WeekPlanCard.tsx`: il piano disegna **sempre sette righe**, una per giorno
  della settimana, prese da `monday` e non dall'elenco delle sedute previste
  — che e' quello che garantisce che le righe ci siano tutte anche se il
  front matter ne saltasse una.
- `WeekPage.tsx`: le sedute si raggruppano per giorno (`byDay`) e la card
  disegna sette righe, ognuna con le sedute di quel giorno — zero, una, o
  due.
- `styles.css`: `.week-work` con nove righe esplicite, `.week-days` che le
  eredita con `grid-template-rows: subgrid`, e il piede ancorato all'ultima
  (`grid-row: -2 / -1`), se no il "written at" del piano finirebbe sulla riga
  del lunedi'.
- Nel telefono la griglia **si scioglie**: una colonna sola, le card una
  sotto l'altra, le righe tornano blocchi normali e quelle vuote spariscono.
  Affiancate tenevano il posto; impilate sarebbero cinque fili di
  separazione uno sull'altro.

## Una cosa che cambia nel contenuto

Nella riga di una seduta la data intera e' diventata il **solo giorno della
settimana**: «Running · Tue · 19:42» invece di «Running · Tue 2026-10-27 ·
19:42». La riga dice gia' di che giorno e', e la settimana sta nel titolo.

Il giorno pero' resta scritto, e non e' ridondanza da togliere: **senza piano
la colonna di sinistra non c'e'**, e una seduta senza giorno in una pagina di
sette giorni non si colloca piu'. Provato sulla settimana del 19 ottobre, che
di piano non ne ha: le sei sedute si leggono ancora, ognuna col suo giorno.

## Come e' andata

Fatto, e misurato dal DOM: sulla settimana del 26 ottobre le sette righe
hanno **lo stesso inizio e la stessa altezza** da una parte e dall'altra —
martedi' e mercoledi' sono alte 61 px invece di 47 perche' le sedute portano
due righe di testo, e la riga del piano di fronte si e' alzata con loro. Le
due card restano alte uguali (457 px).

Il testo del giorno e il nome della seduta restano a due o tre pixel l'uno
dall'altro: e' la differenza fra `0.92rem` e `0.95rem` in grassetto, e
inseguirla con un margine a mano sarebbe peggio del disallineamento.

### Due inciampi, tutti e due trovati guardando

**La pagina bianca.** Ho scritto l'uso di `weekdayShort` e il suo import in
due passaggi: fra l'uno e l'altro Vite ha ricaricato un modulo che usava una
cosa non importata, e **da li' in poi non si e' piu' ripreso** — la pagina
restava bianca con `ReferenceError: weekdayShort is not defined` anche dopo
che il file era giusto, e `npm run build` passava. Si sistema riavviando il
server di sviluppo. Chi vede una pagina bianca con un errore che il codice
non spiega piu', riavvii `make frontend` prima di cercare il bug.

**Il telefono tornato a due colonne.** La media query che scioglieva la
griglia stava nel blocco che il todo 76 aveva riscritto, ed era sparita senza
che nulla lo segnalasse — a 1280 px non si vede. Rimessa, e con lei il
necessario per sciogliere anche `subgrid`: in una colonna sola due card che
occupano le stesse nove righe finirebbero **una sopra l'altra**.

Per poterla sciogliere ho tolto le righe messe con `style={{ gridRow }}`:
una regola inline vince sul foglio di stile, e una media query non avrebbe
potuto spegnerla. Le righe adesso le colloca l'ordine dei figli, che e' gia'
quello giusto.

### Come e' stato verificato

- **Le righe combaciano**: sette a sinistra, sette a destra, stesso inizio e
  stessa altezza riga per riga.
- **Senza piano** (19 ottobre): la card del piano non ha righe, le sei sedute
  restano al loro posto con il giorno scritto.
- **Il telefono** a 760 px: una colonna, il piano sopra le sedute, e delle
  sette righe di destra ne restano visibili due — quelle che hanno qualcosa.
- Nei due temi, `npm run typecheck` e `npm run build` puliti.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_77'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno.

Dopo il revert, rifare il merge di `todo_77` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
