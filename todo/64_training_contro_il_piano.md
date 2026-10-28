---
status: done
---

# Il Training giudica contro il piano, quando un piano c'e'

La vista Training di un giorno ha due riquadri (todo 63): **Plan**, la seduta
prevista, e **Training**, com'e' andata. Il secondo non sa del primo.

Il commento alla seduta deve venire:

1. **in funzione del piano e delle sedute presenti e passate**, se il piano
   c'e';
2. **in funzione delle sole sedute presenti e passate**, se il piano non c'e'.

Oggi vale sempre il secondo, anche quando il piano c'e'.

## Cosa si legge, nel 27 ottobre

Il piano di quel giorno diceva: *easy 5 km at 7'15"-7'40", then 6 x 20 s
strides. First run back: heart rate under 138.* Si e' corso **9,09 km a
6'34"/km**, battito medio 134.

Il commento scritto dall'agente comincia con «**Nothing was planned on the
watch**, and the "easy" label is only my guess», e finisce con «Against your
other easy runs of the last three months this was a strong one: 9.1 km where
you usually do 7.2 (...) Barely any cost for a lot more running».

Niente di falso, e tutto fuori bersaglio. Il metro era un altro: **+82% di
distanza** e **41-66 secondi al chilometro sotto la fascia** nella prima
uscita di un rientro, in una settimana che il piano stesso spiega cosi' — «la
quality e' giovedi e non martedi: l'HRV e' sotto la sua fascia e il respiro
nel sonno a 16, e vogliono prima due giorni tranquilli». Il tetto del battito
e' l'unica cosa rispettata, e non gliene da' merito. Il verdetto finale loda
esattamente quello che il piano chiedeva di non fare.

**Non e' l'agente distratto, e' l'agente cieco.** Il piano glielo si deve
dare, e non glielo si dava: in `_prompt` la frase che lo nomina era `if plan
is not None and section.key == "next"`. Di "previsto" il Training conosceva
solo `workout_name`, cioe' l'allenamento caricato sull'orologio — da cui
«nothing was planned on the watch», vero di quel file e di nient'altro.

## Le due date

Il piano non si passa una volta per tutte, perche' **le due sezioni che lo
leggono guardano date diverse**: Next prescrive per il giorno dopo, il
Training giudica quello del report. La domenica sera i due giorni cadono in
settimane diverse, cioe' in **due file diversi**. Per questo il percorso si
calcola sezione per sezione (`_planned`) e non una volta in `_run`.

## Il silenzio quando il piano non c'e'

Caso 2: la frase nel prompt non c'e', e il prompt torna quello di sempre.
All'agente **non si dice ne' che un piano c'e' ne' che non c'e'**: dirgli «per
questo giorno non era previsto niente» e' peggio del tacere, perche' una frase
sull'assenza si legge come un verdetto sulla seduta — ed e' esattamente
l'inciampo del 27 ottobre, dove «nothing was planned» parlava del file
dell'orologio e sembrava parlare della giornata.

I giorni senza piano sono la maggior parte dello storico: il blocco parte dal
26 ottobre 2026, e prima c'e' solo la settimana del 28 settembre, che vale
come senza piano (todo 63). Per tutti quelli il testo resta quello di adesso.

## Work

- `api/refresh.py`: la frase del piano in una funzione sua, `_planned(kind,
  section, subject, moment, summary_dir)`, che sceglie **data e file sezione
  per sezione**. `_run` non calcola piu' un percorso: passa la cartella, e
  `_write_section` e `_prompt` la portano giu'.
- `api/refresh.py`: la frase va anche nel ramo delle sezioni che **non**
  leggono i frammenti, dov'era mai arrivata — il Training e' una di quelle.
- `.claude/agents/05_training.md`: il piano come primo metro quando c'e', il
  silenzio quando non c'e', e la riga che tiene separate le due cose che si
  somigliano — **l'allenamento sull'orologio non e' il piano**. Piu' un
  esempio per ciascuno dei due casi.
- `README.md`: non e' piu' «Next li legge», sono due sezioni e due date.

## Vincoli

- **Il confronto con le sedute passate non si sostituisce**, ci si somma: il
  piano dice cosa era chiesto, lo storico dice cosa e' normale per lui. Un
  commento che perde il secondo e' un commento peggiore di quello di adesso.
- **Le altre sezioni non cambiano.** Health, Recovery, Load e Fitness
  raccontano dei numeri, e quello che era previsto non li cambia. Il Training
  della settimana resta fuori: li' il confronto e' con la forma dei sette
  giorni, un'altra domanda.
- Next non cambia di una parola: stessa frase, stessa data.
- Nessun campo nuovo nei fatti, nessun cambio all'API: il piano l'agente lo
  legge dal file, che e' quello che Next fa gia'.

## Rischi

- **Il paragrafo si allunga.** Erano 120 parole per lo storico; adesso ce n'e'
  un metro in piu'. Se cresce troppo e' l'esempio che va accorciato, non il
  confronto che va tolto.
- **Un piano seguito non e' una notizia.** Il rischio di un metro nuovo e' che
  l'agente lo usi ogni volta: una seduta fatta come era chiesta si dice in una
  riga e si passa oltre, come dice gia' la regola di non cercare un difetto
  per bilanciare un complimento.
- **I report vecchi non si aggiornano da soli.** Il 27 ottobre resta com'e'
  finche' non si rifa' quella sezione.

## Verifica

1. I prompt, senza lanciare nessun agente: sul 27 ottobre il Training nomina
   `05.plan/2026-10-26.md` e la data `2026-10-27`; sul 20 ottobre non nomina
   niente; Health non nomina niente in nessuno dei due.
2. Next invariato: sul 27 ottobre sera prescrive per il 28 con la frase di
   prima.
3. La domenica sera, due file diversi: il Training del 1 novembre legge
   `2026-10-26.md`, il Next legge `2026-11-02.md`.
4. Il Training della settimana non nomina niente.
5. Rifatta la sezione del 27 ottobre, il testo parla dei cinque chilometri
   previsti e dei nove corsi, e del ritmo fuori fascia; rifatta quella di un
   giorno senza piano, non nomina nessun piano.

## Come e' andata

Fatto come scritto, e verificato per intero: i prompt prima, e poi la sezione
del 27 ottobre riscritta per davvero.

### Una cosa che il piano non aveva previsto

La frase del piano **non arrivava nel ramo giusto**. In `_prompt` il
`{planned}` era interpolato solo nel ritorno delle sezioni con
`reads_fragments` — Next e i Summary, cioe' i verdetti che leggono i
frammenti degli altri. Il Training non e' una di quelle (`Section("training",
"Training", "05_training", False)`), quindi passare il percorso non sarebbe
bastato: la frase sarebbe stata calcolata e buttata. Va aggiunto anche
all'ultimo ritorno, quello delle cinque sezioni che guardano i numeri.

E' il genere di cosa che non da' errore: il prompt resta valido, l'agente
scrive, e il piano non c'e'. Si vede solo guardando il prompt.

### Come e' stato verificato

I prompt, **senza lanciare nessun agente**: `_planned` chiamata a mano per
ogni sezione e ogni data.

| | file nominato | data citata |
|---|---|---|
| training 27 ott | `05.plan/2026-10-26.md` | 2026-10-27 |
| training 20 ott | niente | — |
| health 27 ott | niente | — |
| next 27 ott | `05.plan/2026-10-26.md` | 2026-10-28 |
| training 1 nov (domenica) | `05.plan/2026-10-26.md` | 2026-11-01 |
| next 1 nov (domenica) | `05.plan/2026-11-02.md` | 2026-11-02 |
| w5_training | niente | — |

Le due righe della domenica sono il punto: **due file diversi nella stessa
sera**, che il Training giudica la domenica e il Next prescrive per il
lunedi'. Next e' identico a prima, parola per parola.

### Il punto 5: la sezione del 27 ottobre, prima e dopo

Rifatta su richiesta di Andrea con

```bash
cp summary/01.daily/2026-10-27/training.md /tmp/training-27-prima.md
uv run training-daily-report --day 2026-10-27 --section training --no-update
```

Il comando diretto e non `make daily_report`, che il target non passa
`--no-update`: senza quel flag il giro chiama anche Garmin
(`make update_activity`), che per riscrivere un testo di ieri non serve. La
copia prima perche' **`summary/01.daily/` git non lo traccia**: un report
sovrascritto non si ripristina con un `checkout`. Chi rifa' una sezione che
vuole poter confrontare se la copia da parte.

**Prima:** «Out at 19:42 for an hour on the road, after a rest day. Nothing
was planned on the watch (...) Against your other easy runs of the last three
months this was a strong one (...) Barely any cost for a lot more running.»

**Dopo:** «Five easy kilometres at 7'15"-7'40" with six strides, heart rate
under 138: that was the ask for your first run back (...) some forty seconds a
kilometre quicker than the band, and nearly twice the distance. The cap you
kept, 134 average (...) Week one asks you to be bored. The work is Thursday.»

Quello che la regola voleva, c'e' tutto: il piano in apertura invece di
«nothing was planned»; le due deviazioni coi numeri; **il merito al tetto del
battito**, che era l'unica cosa rispettata e prima passava sotto silenzio; e
il confronto con lo storico **tenuto e riformulato** — gli stessi 9,1 km
contro i 7,2 soliti, che da «a strong one» diventano «the big one, and a km/h
faster». Il vincolo del "non si sostituisce, ci si somma" ha retto alla prova.

Due cose da sapere su quel testo:

- **gli strides non li giudica.** Li cita nella richiesta e non dice se sono
  stati fatti: dai campi che ha non si vede, e non ha inventato. Per saperlo
  servirebbero i lap, che nei fatti del giorno non ci sono;
- scrive «about 6'35"/km» partendo da 9,1 km/h arrotondato, mentre il valore
  e' 6'34". L'«about» la copre e la conseguenza (~40 s/km sotto la fascia) e'
  giusta.

Gli altri report vecchi restano come sono. Per i giorni nuovi il giro della
sera scrive gia' col piano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_64'$" --format=%H -1)
```

Effetti fuori dal repo: **i report scritti nel frattempo restano**. Il revert
toglie il piano dai prompt futuri, non riscrive i testi che quel piano ha
gia' prodotto.
