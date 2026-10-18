---
status: done
---

# Un tasto Refresh nella Day

Oggi, per avere la Day aggiornata, Andrea lancia `make update_activity` e poi
chiede il report del giorno. Serve un tasto nella pagina che faccia tutto:
ricarica i dati e riscrive il report del giorno mostrato.

L'agente `fitness-status` (`.claude/agents/fitness-status.md`) fa gia'
entrambe le cose: il passo 1 lancia `make update_activity` (se fallisce va
avanti con i dati locali e lo scrive nel report), il passo 3 salva
`summary/01.daily/<giorno>.md`. Il tasto quindi lo fa partire dall'API con
`claude -p`, in background.

## Decisioni

Prese con Andrea il 2026-10-18:

- **Un tasto `Refresh`** nell'intestazione della Day, accanto a "Pick a
  date", per **qualsiasi giorno** (quello mostrato). `update_activity`
  rinfresca comunque solo gli ultimi giorni; per un giorno vecchio il tasto
  riscrive il report.
- **Il lavoro lo fa l'agente fitness-status**, lanciato con `claude -p`
  (`~/.local/bin/claude`): nessuna logica del report ripetuta, nessuna
  dipendenza nuova. Dura qualche minuto e usa l'abbonamento Claude.
- **Un lavoro alla volta**: un secondo clic mentre il primo gira non ne fa
  partire un altro.
- **Il login a Garmin non si chiede mai dal tasto**: stdin chiuso, quindi con
  il token scaduto `init_api` fallisce, l'agente usa i dati locali e lo dice
  nel report. Il login lo rifa' Andrea da terminale (`make update_activity`).

## Work

### Backend

- Nuovo `src/training/api/refresh.py`:
  - lo stato in memoria, con un lock: `status` (`idle`, `running`, `done`,
    `failed`), `day`, `started`, `finished`, `message` (le ultime righe
    dell'output quando fallisce);
  - `start(day, ...)`: se un lavoro e' gia' `running` rende il suo stato;
    altrimenti un thread lancia, con `cwd` la radice del repo
    (`context.REPO_ROOT`), `stdin=DEVNULL` e un timeout di 15 minuti:

    ```
    claude -p --agent fitness-status \
      --allowedTools "Bash(make update_activity)" "Bash(make -s daily_data:*)" Read "Write(summary/01.daily/**)" \
      "Write the daily report for <giorno>."
    ```

    L'insieme esatto delle regole si prova nell'implementazione (l'agente
    scrive `cd /home/andrea/dev/mygarmin && make ...`); mai
    `--dangerously-skip-permissions` ne' `bypassPermissions`.
  - alla fine: `done` se il processo esce con 0 e il file del report ha un
    mtime successivo all'avvio, altrimenti `failed`; poi
    `cache.invalidate(data_dir)`, cosi' le attivita' nuove compaiono subito.
- `src/training/api/app.py`:
  - `POST /api/reports/daily/{day}/refresh`: 202 con lo stato; 422 per un
    giorno futuro, come `get_daily`;
  - `GET /api/refresh`: lo stato.
- `src/training/api/models.py`: il modello `RefreshStatus`, con le
  descrizioni.
- `make frontend_types` rigenera `frontend/src/api/schema.ts`.
- `Makefile`: il commento di `api` non dice piu' "in sola lettura".

### Frontend

- `api/client.ts`: `startRefresh(day)` e `getRefresh()`.
- `components/DayHeader.tsx`: il tasto `Refresh` (classe `btn`); mentre gira
  dice "Refreshing… m:ss" ed e' disattivato; se fallisce, il messaggio breve
  sotto l'intestazione.
- `components/DayPage.tsx`: al montaggio legge `GET /api/refresh` (un lavoro
  in corso si vede anche dopo aver ricaricato la pagina); mentre e' `running`
  chiede lo stato ogni 3 secondi; a `done` ricarica i dati e il report del
  giorno (gli `useEffect` che ci sono, con un contatore fra le dipendenze).

### Docs

- `README.md`, nella sezione della Day: il tasto, cosa fa, quanto dura, che
  usa `claude`, e che un login Garmin scaduto va rifatto da terminale.

## Vincoli

- Nessuna dipendenza nuova.
- Il frontend non fa conti.
- Nessuna chiamata vera a Claude o a Garmin nella verifica: si usa un
  `claude` finto. La prova vera la fa Andrea dopo il merge.
- Commenti in italiano senza accenti, testi a schermo in inglese.

## Rischi

- **Permessi in `claude -p`**: un permesso che manca non si ferma su una
  domanda, viene negato; l'agente fallisce e lo stato dice `failed` con il
  messaggio. Le regole si provano sul `claude` vero solo per capire la
  forma, poi le prova Andrea.
- **`uvicorn --reload`** guarda `src/`: il lavoro scrive solo in `summary/` e
  nella cartella dati, quindi il server non si riavvia a meta' (e se si
  riavviasse, lo stato in memoria tornerebbe `idle`: accettabile).
- **Il report vecchio** viene sovrascritto: e' quello che si vuole, come
  quando lo si chiede a mano.

## Verifica

1. `uv run python -c "import training; from training.api import app, refresh"`.
2. `TestClient` con un `claude` finto in testa al `PATH` (uno script che
   scrive il report del giorno in una cartella `summary` temporanea ed esce
   0, e uno che esce 1 con un messaggio): POST -> 202 `running`; un secondo
   POST non lancia un secondo processo; GET arriva a `done` o `failed` con il
   messaggio; un giorno futuro -> 422.
3. `cd frontend && npm run build`; `make frontend_types` e lo schema nuovo
   nel commit.
4. Nel browser, con l'API sul `claude` finto: il tasto, "Refreshing…", e alla
   fine il report nuovo nella pagina; nessun errore in console. Tutti i
   server avviati si fermano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_41'$" --format=%H -1)
```

Effetti fuori dal repo: i report giornalieri riscritti dal tasto in
`summary/01.daily/` e i dati scaricati da `make update_activity` restano: sono
gli stessi che si avrebbero chiedendoli a mano.

Dopo il revert, rifare il merge di `todo_41` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
