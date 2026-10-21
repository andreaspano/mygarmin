---
status: done
---

# Due timer: il report si scrive da solo, mattina e sera

Oggi il report esiste solo se qualcuno preme un tasto, e i dati si fermano
dove li lasci: alle 11:00 del 21 ottobre la pagina mostrava numeri scaricati
alle 09:24, perche' fra le due ore nessuno aveva chiamato Garmin. Non c'e'
cron, non c'e' timer, niente.

E il tasto per card, su un giorno mai scritto, lascia un report monco: il
refresh della sola Health quella mattina ha creato
`summary/01.daily/2026-10-21/` con dentro un file solo, e le altre sei card
sono rimaste senza testo (e, finche' non e' stato corretto, senza icona).

Due timer chiudono tutti e due i buchi: la mattina la pagina e' gia' pronta
quando la apri, la sera la seduta del giorno ha il suo commento.

## Decisioni

Prese con Andrea il 2026-10-21:

- **Due giri, non due giri uguali.** La mattina alle 10 sei agenti, la sera
  alle 22 cinque. Health e Recovery solo la mattina: sono misure della
  notte, e alle 22 racconterebbero di nuovo la stessa notte.
- **Training non gira la mattina**: alle 10 non c'e' niente da commentare.
  La card resta senza testo finche' non ti alleni, poi la scrive il giro
  della sera.
- **Gli agenti sanno che ora e'.** Un prompt solo per Summary e per Next,
  con due rami: la mattina giudicano la giornata che comincia, la sera
  quella finita.
- **Ogni card dice quando e' stata scritta**, in una riga piccola sotto il
  testo. Dopo il giro della sera le card portano ore diverse, ed e' giusto
  che si veda.

```
10:00  health  recovery  load  fitness  ->  next  summary          6 agenti
22:00                    load  fitness  training -> next  summary  5 agenti
                                                              11 al giorno
```

## Work

### 1. Il momento del giro — `src/training/api/sections.py`

Accanto a `SECTIONS` e `RUN_ORDER`, i due insiemi e la regola dell'ora:

```python
MOMENT_SECTIONS = {
    "morning": ("health", "recovery", "load", "fitness", "next", "summary"),
    "evening": ("load", "fitness", "training", "next", "summary"),
}
EVENING_FROM_HOUR = 15
```

`_run` gia' scorre `RUN_ORDER` filtrato per chiavi, quindi i sottoinsiemi
rispettano da soli l'ordine (prima i numeri, poi i verdetti) e le due
`assert` del modulo restano valide.

**Il momento e l'insieme sono due cose diverse**, e vanno tenute separate:

- il **momento** decide *come parla* il testo e si ricava sempre dall'ora
  (`morning` sotto le 15, `evening` da li' in poi);
- l'**insieme** decide *chi gira*, e lo scelgono solo i timer.

Cosi' il tasto grande continua a voler dire "rifai tutto" (sette sezioni) a
qualunque ora, e il tastino di una card continua a rifare la sua: cambia solo
la voce di Next e Summary, che seguono l'orologio.

### 2. Gli agenti lo sanno — `refresh._prompt`, `06_next.md`, `07_summary.md`

Il momento entra nel prompt, non nel JSON: e' un fatto del giro, non del
giorno. Una frase in fondo, del tipo "This is the morning run: the day is
ahead of him" / "the evening run: the day is behind him".

- **`06_next`**: oggi decide oggi-contro-domani da `recent.trained_today`.
  **E' un difetto che i timer renderebbero visibile**: la sera di un giorno
  di riposo `trained_today` e' falso e Next proporrebbe una seduta per un
  giorno finito. Il momento diventa il segnale primario — mattina: la seduta
  e' per oggi; sera: per domani — e `trained_today` resta solo per dire se
  oggi e' gia' stato allenato.
- **`07_summary`**: due rami corti. Mattina, verdetto sulla giornata che
  comincia e una clausola di direzione ("train, easy"). Sera, verdetto su
  com'e' andata, con la seduta al centro quando c'e' stata. Resta tutto il
  resto: nessun numero, dire quando le sezioni non concordano, ~45 parole.

### 3. Un lavoro alla volta, davvero — `src/training/api/refresh.py`

Il guardiano di oggi (`_lock` piu' `_state` in memoria) vale **dentro un solo
processo**. Il timer e' un processo diverso dall'API: se parte mentre premi
Refresh, oggi partono due `make update_activity` e due serie di agenti sugli
stessi file, e nessuno dei due se ne accorge.

Serve un lock **su file**: `<data_dir>/.refresh.lock` con `fcntl.flock` non
bloccante, preso da `_run` su tutte e due le strade. Chi lo trova occupato
non aspetta: l'API rende lo stato del lavoro in corso (come adesso), il
comando da terminale stampa "ce n'e' gia' uno in corso" ed esce 0, cosi' un
timer che si accavalla non riempie il log di errori.

### 4. Lo scaricamento che fallisce in silenzio — `refresh._prepare`

`make update_activity` gira con `check=False`, l'output buttato e lo stdin
chiuso apposta, perche' un login scaduto non si pianti ad aspettare la
password. Con Andrea davanti al tasto va bene. **Non sorvegliato e' un
problema**: il timer parte, il login e' scaduto, gli agenti scrivono su dati
di tre giorni fa e niente lo dice.

`_prepare` guarda il codice d'uscita e, quando non e' zero, lo mette nello
stato: `RefreshStatus` guadagna un `download` (`ok`, `message`, le ultime
righe come gia' si fa per le sezioni). Il lavoro **va avanti lo stesso** —
meglio un report sui dati di ieri che nessun report — ma la pagina lo dice,
accanto all'avviso delle sezioni fallite che c'e' gia', e il comando lo
stampa.

### 5. Quando e' stato scritto — modello, API, pagina

- `ReportSection` guadagna `written_at: datetime | None`, preso dall'`mtime`
  del frammento in `_fragment_sections`. Per i giorni vecchi a file unico
  (`parse_report`) vale l'`mtime` di quel file, uguale per tutte le sezioni.
- `frontend/src/markdown.tsx`: accanto a `sectionBody` e `sectionIcon`, un
  `sectionWrittenAt`.
- Le card ricevono la data accanto al testo e la mostrano sotto, in una riga
  piccola e grigia, **solo quando c'e' il testo**. Una funzione sola in
  `Stat.tsx`, accanto a `CardHead` e `MeasureBar`: ora sola se il frammento
  e' del giorno del report ("written at 10:04"), data e ora se e' stato
  scritto dopo ("written 21 Oct, 00:01" — succede gia': la Recovery del 20
  e' stata riscritta a mezzanotte e un minuto).
- Il modello dell'API cambia, quindi `make frontend_types` rigenera
  `schema.ts`, che va committato.

### 6. I timer — `deploy/`, nuova cartella

Unita' systemd **utente**, versionate nel repo e installate da `make`:

- `mygarmin-report@.service`, con `%i` che e' il momento:
  `ExecStart=/home/andrea/.local/bin/uv run training-daily-report --moment %i`,
  `WorkingDirectory` sulla radice del repo. **Il percorso di `uv` va scritto
  per intero**: un servizio utente non ha il `PATH` della shell.
- `mygarmin-report-morning.timer` (`OnCalendar=*-*-* 10:00`) e
  `mygarmin-report-evening.timer` (`OnCalendar=*-*-* 22:00`), tutti e due
  con `Persistent=true`, cosi' un giro saltato a macchina spenta o
  addormentata recupera al risveglio invece di perdersi.
- `make install_timers`: copia in `~/.config/systemd/user/`,
  `daemon-reload`, abilita e avvia i due timer, e **stampa che serve
  `loginctl enable-linger`** (il 21 ottobre e' `no`: senza, i servizi utente
  non girano quando Andrea non e' loggato). **Quel comando lo lancia
  Andrea**, non il todo: chiede i suoi permessi.

Il comando da terminale guadagna `--moment morning|evening`, che sceglie
l'insieme delle sezioni; senza, resta il comportamento di oggi (tutte e
sette). `--section` continua a voler dire una sola.

## Vincoli

- Nessuna dipendenza nuova: `fcntl` e `argparse` sono della libreria
  standard, systemd c'e' gia'.
- `make update_activity` lo lancia solo l'orchestratore, come oggi. Nel
  provare questo todo non si chiama a mano, e le prove degli agenti vanno
  fatte con `--no-update`.
- `make install_timers` si puo' lanciare (scrive solo in
  `~/.config/systemd/user/`), ma i timer vanno lasciati **disabilitati** se
  la verifica non arriva in fondo.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Una seduta sincronizzata dopo le 22** non entra in nessun report: alle
  10 si scrive il giorno nuovo, e quel giorno resta monco per sempre. Il
  rimedio a buon mercato — il giro della mattina guarda se `training.md` di
  ieri e' piu' vecchio della fine dell'ultima attivita' di ieri e rifa'
  quella sola sezione — **non e' in questo todo**: prima si vede se capita.
- **Undici agenti al giorno**, anche i giorni in cui la pagina non si apre.
  Circa 330 al mese.
- **La readiness si muove durante il giorno** e Recovery non si riscrive la
  sera: alle 22 la card puo' mostrare un numero diverso da quello di cui
  parla il suo testo. L'ora di scrittura lo spiega, non lo risolve.
- **Il computer deve essere acceso.** `Persistent=true` recupera il giro
  saltato, ma al risveglio, non all'ora giusta.

## Verifica

1. `uv run python -c "from training.api import refresh, sections"`.
2. `training-daily-report --day 2026-10-20 --moment evening --no-update`:
   gira cinque sezioni, `health.md` e `recovery.md` non cambiano `mtime`, e
   il testo di Next parla di **domani**. Poi `--moment morning --no-update`
   su un giorno senza allenamento: sei sezioni, e Next parla di **oggi**.
3. Due comandi insieme: il secondo dice che ce n'e' gia' uno ed esce subito,
   senza lanciare agenti.
4. Lo scaricamento fallito: con un `PATH` senza `make`, il lavoro va avanti
   e lo stato porta `download.ok` falso con il messaggio.
5. `make frontend_types` (`schema.ts` cambia una volta e si committa; la
   seconda esecuzione non lo tocca), `npm run typecheck`, `npm run build`.
6. La pagina di un giorno con frammenti di ore diverse: ogni card porta la
   sua ora, le card senza testo non portano niente, nessun errore in
   console.
7. `systemd-analyze verify deploy/*.service deploy/*.timer`, poi
   `make install_timers` e `systemctl --user list-timers`: i due timer con
   il prossimo scatto all'ora giusta. Una prova vera con
   `systemctl --user start mygarmin-report@evening.service` e il suo
   `journalctl --user -u ...`.

## Come e' andata

Fatto come scritto. Quattro cose decise o trovate per strada:

- **`--moment` da' anche la voce a una sezione sola.** Serviva per provare il
  ramo della sera a meta' pomeriggio, e si e' rivelata la semantica giusta:
  `--moment` vuol dire "parla come quel giro" sempre, e in piu' sceglie
  l'insieme quando non c'e' `--section`. Senza, la voce la da' l'orologio.
- **I due verdetti hanno avuto bisogno di due giri.** Al primo tentativo Next
  della sera scriveva "Nothing more today" invece di proporre domani, e
  Summary chiudeva con "Train, but let the body set the pace", cioe' un
  consiglio in avanti alle 22. I due prompt adesso lo vietano per nome: la
  sera **tutto** quello che Next propone e' di domani, e Summary finisce sul
  verdetto senza nemmeno una clausola di direzione.
- **Chi non prende il lock lascia lo stato in ordine.** `start()` segna
  "running" prima di lanciare il thread: se poi il lock e' di un altro
  processo, lo stato sarebbe rimasto "running" per sempre. Adesso quel caso
  si chiude da solo con "Another refresh is already running".
- **La riga dell'ora e' una sola guardia**, dentro `WrittenAt`: l'API manda
  `written_at` solo per le sezioni scritte, quindi nessuna card se la ripete.
  In Load sta in fondo alla card e non sotto il testo, perche' sotto ci sono
  ancora il grafico e due numeri.

**I timer sono installati e accesi**: il prossimo giro e' quello delle 22.
Per spegnerli:

```bash
systemctl --user disable --now mygarmin-report-morning.timer mygarmin-report-evening.timer
```

Resta da fare a mano `loginctl enable-linger andrea`: finche' e' `no`, i due
giri partono solo mentre Andrea e' loggato.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_47'$" --format=%H -1)
```

Effetti fuori dal repo: **i timer restano installati e accesi**. Le unita'
sono copie in `~/.config/systemd/user/`, che git non tocca: dopo il revert
continuerebbero a partire e a chiamare un comando che non ha piu'
`--moment`, fallendo due volte al giorno. Vanno spenti a mano con il comando
qui sopra e, volendo, cancellati:

```bash
rm ~/.config/systemd/user/mygarmin-report*; systemctl --user daemon-reload
```

Restano anche i frammenti riscritti del 2026-10-20 (tutti tranne `health.md`
e `recovery.md`) e il `next.md` del 2026-10-21, piu' il file vuoto
`<dati>/.refresh.lock`, che e' innocuo: il codice vecchio non lo guarda.

Dopo il revert, rifare il merge di `todo_47` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.

---

**Nota del 2026-10-21, dopo il merge.** I timer di systemd sono durati poche
ore: Andrea ha chiesto cron, che su questa macchina e' la scelta giusta
(accesa da settimane, mai sospesa, quindi il recupero dei giri saltati non
serve, e cron non vuole il linger). Le unita' sono state spente, rimosse e
cancellate dal repo; al loro posto ci sono `deploy/crontab` e
`make install_cron`. Il `## Revert` qui sopra resta valido per il codice, ma
la sua frase sui timer non vale piu': non ci sono piu' unita' da spegnere a
mano, semmai righe di cron da togliere con `make uninstall_cron`.
