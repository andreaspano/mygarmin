---
status: todo
---

# Revisione di tutto il codice

Il repo porta il suo progetto nei commenti e nel `README.md`: chi legge il
codice si fida di quello che c'e' scritto sopra. Il 2026-10-19, in
`frontend/vite.config.ts`, il commento diceva che su mutolo Vite ascoltava
sull'indirizzo Tailscale: non lo ha mai fatto, ascolta solo su 127.0.0.1, e
dalla tailnet ci arriva `tailscale serve`. Il codice era giusto, il commento
mentiva. Questo todo e' una passata su tutto il repo per due cose: i commenti
e i documenti che non dicono il vero, e il codice che si puo' accorciare o
non ripetere.

Non e' una caccia ai bug: la correttezza e l'integrita' dei dati restano
fuori (scelta di Andrea), e questo fa si' che nessuna correzione cambi il
comportamento.

## Decisioni

Prese con Andrea il 2026-10-19:

- **Tutto il repo**: `src/training` (circa 5.000 righe in 31 file),
  `frontend/src` (circa 3.200 righe in 20 file), piu' `Makefile` e
  `README.md`.
- **Due dimensioni sole**: (1) commenti, docstring e `README.md` che
  contraddicono il codice; (2) riuso e semplificazione. Niente caccia ai bug
  di correttezza, niente revisione dell'integrita' dei dati.
- **Si corregge quello che si trova**, sul ramo `todo_42`.
- **Il commit lo fa Andrea.** Il lavoro resta non committato, e in `main`
  non si unisce niente.

### Cosa cambia rispetto a `/atodo`

Il todo e' la specifica e vince sul protocollo della skill. Di `/atodo`
restano il ramo `todo_42`, le regole di autonomia, "mai riparare da soli per
far tornare verde" e la scala delle verifiche. **Non** si fanno i passi 5-8:
niente `status: done`, niente commit, niente `git merge --no-ff`, nessuna
sezione `## Revert` (vedi in fondo). Alla fine il ramo `todo_42` esiste con
le modifiche nel working tree, e `git status` le mostra.

## Work

### 1. I commenti e i documenti che mentono

Per ogni modulo si legge il commento (o la docstring) contro il codice che
descrive. Quando non vanno d'accordo **si corregge il testo, non il
codice**: il codice funziona, ed e' quello che gira.

Da guardare, nell'ordine:

- `src/training/api/`: `app.py`, `refresh.py`, `models.py`, `context.py` e la
  cache della salute. La cache e' il codice piu' nuovo e meno riletto
  (commit `b89338b`, "cache health for a minute, read it once per daily
  request"): il commento dice per quanto vale e quando si butta, e va
  verificato contro quello che fa davvero.
- `src/training/garmin/`: `cli.py`, `auth.py`, `health.py`, `activities.py`,
  `misc.py`, `client.py`, `config.py`. Qui i commenti spiegano i tempi delle
  chiamate a Garmin e cosa si riprende dopo un Ctrl+C: si controlla che i
  numeri e le condizioni citate siano ancora quelli del codice.
- `src/training/interface/`.
- `frontend/src/`: `api/client.ts` e i `components/`.
- `Makefile`: il commento sopra ogni target dice cosa fa e cosa serve prima.
  Si confronta con la ricetta.
- `README.md`: ogni sezione contro il codice di adesso. La pagina Day, l'API,
  il tasto Refresh e la parte della tailnet sono le piu' esposte, perche' il
  codice si e' mosso di recente.

Un commento solo stringato, o che dice poco, non e' un rilievo: si tocca
solo quello che e' **falso** o che e' rimasto indietro.

### 2. Riuso e semplificazione

- logica duplicata in due o piu' punti;
- codice che rifa' a mano qualcosa che nel repo c'e' gia': nel rilievo si
  scrive **il nome della funzione o del modulo esistente** da usare;
- strade piu' lunghe del necessario, a comportamento uguale.

L'intervento e' il piu' piccolo che toglie il difetto. Non si riscrive
codice che funziona per gusto.

### 3. Il comportamento non si tocca

Qualunque modifica cambierebbe quello che il codice produce - un numero
diverso in un report, un'altra cosa a schermo, una risposta dell'API
diversa - **esce dallo scopo**: va nei rilievi come consiglio, non corretta.
E' la regola "expected-result change" di `/atodo`, applicata prima invece
che dopo.

## Findings

Da riempire durante la revisione, raggruppati per file, cosi' Andrea puo'
committare o buttare un rilievo alla volta. Una riga per rilievo:

```
<file>:<riga> - <cosa non andava> - <cosa si e' fatto>
```

oppure, per quello che non si corregge:

```
<file>:<riga> - <cosa non andava> - non corretto: <perche'>
```

(l'elenco va qui sotto)

## Vincoli

- Il comportamento non cambia.
- Nessuna dipendenza nuova.
- Non si toccano gli altri file di `todo/`, ne' il loro `status`.
- Non si scrive in `summary/` ne' nell'albero dei dati.
- `frontend/src/api/schema.ts` non si modifica a mano: lo genera
  `make frontend_types`.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Riscrivere invece di correggere**: una passata di qualita' su 8.200
  righe senza test suite puo' scivolare nel rifare codice che gia' va. Il
  mandato e' la modifica minima.
- **Il ramo resta sporco**: finche' Andrea non committa, `git status` su
  `todo_42` mostra le modifiche, e `/atodo` su un altro todo si rifiuta di
  partire (precondizione 3). E' voluto.

## Verifica

1. `uv run python -c "import training"`, piu' un import di ogni modulo
   toccato (es. `uv run python -c "from training.api import app, refresh"`).
2. `cd frontend && npm run typecheck` e `npm run build`: nessun errore.
3. Se si e' toccato un modello dell'API, con l'API accesa
   `make frontend_types` deve lasciare `frontend/src/api/schema.ts`
   invariato.
4. `git diff` riletto contro l'elenco dei Findings: ogni pezzo di diff
   corrisponde a un rilievo, e ogni rilievo corretto a un pezzo di diff.
5. Mai `make update_activity`, `make backfill_health`, `make backfill` ne'
   `make backfill_activity_names`: vanno in rete e scrivono nei dati.

## Revert

Non serve: non si committa e non si unisce niente. Per buttare tutto,
`git checkout -- .` sul ramo `todo_42`, o si cancella il ramo.
