---
status: done
---

# Le tre viste della Week: Snap, Trend, Plan

Il todo 55 ha spezzato la barra in due righe — sopra il periodo, sotto cosa
se ne guarda — ma la seconda riga l'ha riempita solo sotto Day. La voce era
una sola, `{ view: "trend", only: "day" }`, e con una voce sola il `<nav>`
non si disegnava nemmeno: la Week aveva un asse solo, e quello che mostrava
non aveva un nome.

Adesso ce l'ha, e sono tre: **Snap**, **Trend**, **Plan**.

## Perche' Snap e non Report

Sotto Day la vista si chiama Report perche' li' il report c'e' per davvero:
sette agenti che scrivono sette sezioni. Sotto Week il report settimanale
c'e' anche (todo 53), ma quello che la pagina mostra non e' solo lui — sono i
numeri dei sette giorni con le loro fasce, le sedute, il grafico del lavoro
per sport, e **dentro ogni card** il testo della sua sezione. E' l'istantanea
della settimana com'e' andata, non un documento: **Snap**.

La distinzione serve perche' le altre due viste guardano altrove. Lo Snap
guarda **indietro**, a una settimana chiusa o in corso. Il Plan guarda
**avanti**. Il Trend non guarda una settimana, guarda la fila delle
settimane.

## Le due caselle vuote

Nascono vuote di proposito: la riga del menu e il vocabolario dell'URL si
fanno una volta, il contenuto arriva quando arriva.

**Trend.** Il todo 55 lo scrive gia': «"Day" qui vuol dire granularita'
giornaliera, non "un giorno solo": un punto per giorno. Quando ci sara' il
Trend della Week sara' un punto per settimana, e la griglia restera'
coerente». Quello e' questo, e la vista ha il nome e la chiave che avra'
allora, cosi' il Trend non cambia indirizzo quando si riempie.

**Plan.** I file `summary/05.plan/<lunedi>.md` sono le diciotto settimane del
blocco, una per file, con le sette sedute nel front matter. Oggi li legge
solo `refresh.py`, che ne passa il percorso all'agente Next: arrivano
all'utente di rimbalzo, dentro la prosa di qualcun altro, e **nessuna API li
serve**. La casella e' per loro — il piano della settimana che si sta
guardando — e quando la si riempie c'e' gia' `todo/14_plan_vs_done.md`, che
chiede il passo dopo: il pianificato contro il fatto, giorno per giorno.

Il piano di `plan/`, invece, resta dove sta: in alto a destra, fuori dai
periodi. Un blocco di diciotto settimane non e' la vista di una settimana.

## Come l'URL e' cambiato

Prima la vista di partenza era `report` per tutti: `hrefFor` cancellava
`?view=` quando valeva quello, e `viewFromUrl` ci ricadeva per qualunque
valore diverso da `trend`. La Week parte da `snap`, quindi **la vista di
partenza e' di ogni periodo**, non del programma: e' la prima della sua lista
in `VIEWS` (`navigation.ts`), e il parametro si scrive solo quando non e'
quella. Cosi' `?period=week` da solo apre lo Snap — cioe' quello che quel
link apriva anche prima che le viste esistessero — e i link scritti fin qui
restano buoni, forma vecchia `?page=week` compresa.

La lista per periodo ha preso il posto del campo `only`, che filtrava una
lista piatta: con due periodi che hanno viste diverse, e in ordine diverso,
la lista si legge dove serve.

**La vista si porta dietro dove esiste.** Il Trend sta in tutte e due le
liste, perche' e' la stessa domanda, e da Day/Trend si clicca Week e si
arriva su Week/Trend — vuoto, per ora. Da Week/Snap o Week/Plan si clicca Day
e si arriva su Day/Report, che `snap` e `plan` la Day non li ha.

## Cosa e' condiviso fra le tre viste

Le stesse cose che la Day condivide fra Report e Trend: l'intestazione — il
titolo con il cerotto «N of 7 days», le frecce, il calendario, il tasto che
riscrive la settimana — e la striscia delle otto settimane. La settimana
scelta serve a tutte e tre, e cambiandola **la vista resta**.

Sotto, solo lo Snap ha qualcosa. E solo lo Snap chiede i suoi dati: il testo
del report, le sedute e gli sport non si scaricano sulle altre due viste. I
numeri della settimana si', sempre: il cerotto nel titolo li vuole.
