---
status: done
---

# I file di salute di un giorno si riscaricano finche' il giorno non e' finito

Oggi `export_daily_health` salta un file gia' su disco, tranne quelli di oggi
(`force_dates={today}`). Un giorno scaricato di mattina resta cosi' per sempre:
quello che Garmin aggiorna dopo, durante il giorno o dopo un allenamento, non
arriva mai.

Il caso che l'ha fatto vedere: il file `training_status` del 2026-10-15 e'
stato salvato alle 13:20, la corsa (Rip_4x5) e' delle 19:50. La Day del 15
mostra VO2max 41.4 "misurato il 13", mentre Garmin il 15 l'aveva portato a
41.5; nello stesso file il carico mensile high aerobic e' 333.8, nel file del
16 456.3 (manca la seduta della sera), e i passi del giorno sono 609.

Negli ultimi 60 giorni (al 2026-10-18) **19 giorni** hanno i file salvati
durante il giorno stesso.

## Decisioni

Prese con Andrea il 2026-10-18:

- **Un file di un giorno e' completo solo se e' stato salvato dopo la fine
  di quel giorno**: mtime >= mezzanotte del giorno dopo. Un file che manca o
  che non e' completo si scarica (di nuovo). E' la regola generale di cui
  `force_dates={today}` era il caso di oggi: copre da sola oggi, ieri dopo
  un aggiornamento fatto ieri di giorno, e i 19 giorni gia' rimasti a meta'.
- **La regola vale per `export_daily_health`, quindi per tutti e tre i
  comandi**: `update_activity` (gli ultimi `health_refresh_days` giorni, 3),
  `backfill_health` e `backfill`. Dopo il merge, un `make backfill_health`
  di Andrea riscarica solo i giorni a meta' (circa 20 giorni per 11
  chiamate) e salta tutti gli altri.
- **`force_dates` resta** (lo usa `build_fitness_status` e non costa
  niente), ma con la regola nuova non serve piu' per oggi.
- **Tutti gli endpoint giornalieri**, non solo `training_status`: i valori
  che cambiano durante il giorno sono anche il body battery piu' basso
  (`stats`), lo stress medio e massimo (`stress`), il respiro da sveglio
  (`respiration`), endurance e hill score. Quelli della notte (sonno, HRV,
  frequenza a riposo, readiness al risveglio) non cambiano, ma riscaricarli
  costa poco ed evita una lista da tenere aggiornata.
- **La cache si aggiorna da sola**: `health_db.sync_health` rilegge un giorno
  quando uno dei suoi file e' piu' nuovo della riga, e un file riscaricato lo
  e'. Nessun salto di `HEALTH_LOGIC_VERSION`.
- **I report gia' scritti non cambiano**: i report giornalieri di quei giorni
  in `summary/01.daily/` restano come sono. Rifarli e' un'altra cosa.

## Work

- `src/training/garmin/health.py`:
  - una funzione `_is_complete(path, day)`: il file c'e' e il suo mtime e'
    dalla mezzanotte del giorno dopo in poi (ora locale, come le date dei
    file);
  - in `export_daily_health`, `if target.exists() and d not in force_dates`
    diventa "salta se `_is_complete(target, d)` e `d` non e' in
    `force_dates`";
  - le docstring di `export_daily_health`, `refresh_recent_health` e
    `backfill_health` dicono la regola nuova (oggi dicono "saltando i giorni
    gia' presenti su disco");
  - il messaggio di avanzamento dice anche quanti file ha scaricato, cosi'
    un backfill che riscarica 20 giorni su 656 si capisce.
- `src/training/interface/health_db.py`: il commento che cita
  `force_dates={today}` dice la regola nuova.
- `README.md`: dove si parla di `update_activity` e `backfill_health`, una
  riga sulla regola, e che un `make backfill_health` sistema i giorni
  rimasti a meta'.

## Vincoli

- Nessuna dipendenza nuova.
- **Nessuna chiamata a Garmin nella verifica**: si usa un oggetto finto al
  posto di `Garmin`, che conta le chiamate. `make update_activity` e `make
  backfill_health` li lancia Andrea dopo il merge.
- Commenti in italiano senza accenti.

## Rischi

- **Una corsa a tarda sera sincronizzata il mattino dopo**: se
  l'aggiornamento gira dopo mezzanotte ma prima della sincronizzazione
  dell'orologio, il giorno risulta completo senza la corsa. E' raro, e il
  VO2max di quella corsa compare comunque nel file del giorno dopo.
- **Gli mtime e la sincronizzazione cloud**: la cartella dati sta in una
  cartella sincronizzata (ci sono copie `.conflict`). Se una copia da un
  altro computer portasse mtime piu' recenti, un giorno a meta' sembrerebbe
  completo: si sbaglia nel verso di oggi (il file resta com'e'), mai
  riscaricando all'infinito.
- **Il primo `update_activity` dopo il merge** riscarica i giorni della
  finestra (3) che non sono completi: una ventina di chiamate in piu', una
  volta.

## Verifica

1. `uv run python -c "import training; from training.garmin import health, activities, fitness_status"`.
2. `_is_complete` su file finti in una cartella temporanea (con `os.utime`):
   un file del giorno D salvato alle 13:00 di D -> no; alle 23:59 di D ->
   no; alle 00:00 di D+1 -> si'; un file che manca -> no.
3. Su una copia temporanea della cartella `health` vera, con un `Garmin`
   finto che conta le chiamate e risponde `{}`: `export_daily_health` dal
   2026-08-20 al 2026-10-18 chiede esattamente i giorni i cui file non sono
   completi (il 2026-10-15 si', il 2026-10-14 no), e nessun altro. Il
   conteggio torna con quello calcolato a parte sugli mtime.
4. `export_daily_health` con `force_dates={giorno completo}` lo riscarica
   comunque.
5. `make daily_data DAY=2026-10-15` sulla cartella vera da' lo stesso JSON di
   prima (il codice di lettura non cambia).
6. La cartella dati vera non e' stata toccata: nessun file con mtime di oggi
   creato dalla verifica.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_39'$" --format=%H -1)
```

Effetti fuori dal repo: i file di salute riscaricati dai prossimi `make
update_activity` e `make backfill_health` restano nella cartella dati: sono
gli stessi file di prima, solo completi, e il codice vecchio li legge come
gli altri.

Dopo il revert, rifare il merge di `todo_39` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
