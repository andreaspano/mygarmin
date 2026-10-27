---
status: done
---

# Il piano della settimana, dove si vede

Il todo 59 ha aperto tre viste sotto Week e due le ha lasciate vuote. Questo
riempie il **Plan**: i file `summary/05.plan/<lunedi>.md`, uno per settimana
del blocco, con le sette sedute, i totali, i ritmi e i segnali per scaricare.

## Erano scritti e non si vedevano

Diciannove file nel repo, generati il 26 ottobre dal blocco
`plan/half_marathon_2.20.md`, e **nessun modo di leggerli dall'interfaccia**.
L'unico che li apriva era l'orchestratore, che ne passa il percorso al prompt
di Next; all'utente arrivavano di rimbalzo, dentro la prosa di qualcun altro,
e sempre e solo la riga di un giorno. Il resto — la tabella dei sette giorni,
i ritmi, il quando-scaricare — restava su disco.

La Week e' il posto giusto perche' la chiave e' la stessa: il lunedi'. Lo Snap
dice com'e' andata la settimana, il Plan come doveva andare, e il selettore in
testa alla pagina — condiviso dalle tre viste — li tiene sugli stessi sette
giorni. Il blocco di `plan/` resta dov'e', in alto a destra: dura quattro mesi
e parla di una gara, non e' la vista di una settimana.

## Dove sta il codice

**Il caricatore sta in `api/plans.py`**, non in un modulo nuovo: il front
matter, il titolo e i coercitori delle date e dei numeri sono li' e sono gli
stessi: un piano settimanale e' un file di piano con altre chiavi. Il nome
della cartella e il percorso del file ci sono ora una volta sola —
`WEEK_PLAN_FOLDER` e `week_plan_path` — e `refresh.py` li prende da li' invece
di tenersi il suo `PLAN_FOLDER` e il suo `_week_plan`. Il perche' solo Next
legga il piano e' rimasto dov'e' vero, cioe' al punto in cui lo si chiede.

**`sessions` l'API non lo manda.** Sono le sette sedute in forma leggibile da
un programma, e servono al confronto previsto/fatto del `todo/14_plan_vs_done.md`,
che non c'e' ancora. Mandarlo adesso vorrebbe dire un campo che nessuno
guarda, mentre la tabella del testo dice le stesse sedute **col perche'
dentro** — «la quality e' giovedi e non martedi: la readiness di oggi vuole
prima due giorni tranquilli» — che e' quello che una persona legge.

**Un lunedi' nel futuro e' permesso**, a differenza di
`GET /api/weekly/<lunedi>`: il piano di una settimana che non e' cominciata e'
il caso normale, un blocco si scrive in avanti. La pagina non ci arriva da
sola, che il selettore non va oltre questa settimana, ma l'endpoint non deve
rifiutare la cosa per cui esiste.

## Una settimana senza piano

404, e la vista lo dice con una frase invece di restare muta: le settimane
prima dell'inizio del blocco non hanno un file, e non e' un errore. La card
tiene separate le due cose che si somigliano — «sto cercando» e «non ce n'e'
uno» — perche' scambiarle fa lampeggiare un piano mancante che invece sta
arrivando.
