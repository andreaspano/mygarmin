---
status: todo
---

# Plan: il piano della settimana contro quello che hai fatto

Da settembre 2026 i piani settimanali stanno in `summary/05.plan/`, un file per
settimana con il nome del lunedi' (`2026-09-28.md`). Quello che si e' fatto sta
in `activities.db`. Nessuno li mette uno accanto all'altro, quindi a fine
settimana non si vede cosa e' stato rispettato.

Qui si aggiunge una pagina **Plan** che, giorno per giorno, mostra la seduta
prevista e le attivita' registrate, con un esito per ogni giorno.

## Il problema del formato

Oggi il piano e' solo una tabella markdown pensata per essere letta
(`| **Wed 30 Sep** | **Faster session:** 8 km in total, with 3 x 8 min ...`).
Estrarne sport e distanza con delle regex e' fragile. **Decisione**: il file di
piano ha anche un front matter YAML leggibile dalla macchina, e la tabella
resta per chi legge.

```yaml
---
week: 2026-09-28
sessions:
  - {date: 2026-09-27, sport: cycling, kind: easy, duration_min: [60, 90]}
  - {date: 2026-09-28, sport: running, kind: easy, distance_km: 6}
  - {date: 2026-09-29, sport: rest, optional: cycling}
  - {date: 2026-09-30, sport: running, kind: quality, distance_km: 8}
  - {date: 2026-10-01, sport: rest, optional: cycling}
  - {date: 2026-10-02, sport: rest}
  - {date: 2026-10-03, sport: running, kind: long, distance_km: [10, 11]}
  - {date: 2026-10-04, sport: running, kind: easy, distance_km: 5, optional: rest}
---
```

Un valore puo' essere un numero o un intervallo `[min, max]`. `sport` usa gli
stessi nomi di `activities.sport` (`running`, `cycling`, ...) piu' `rest`.

## Work

- Aggiungere il front matter a `summary/05.plan/2026-09-28.md`, copiando la
  tabella che c'e' gia'. La tabella non si cambia.
- Un loader `load_plans(dir) -> DataFrame`, una riga per seduta, che salta con
  un avviso i file senza front matter.
- L'esito di ogni giorno, confrontando la seduta con le attivita' di quella
  data:
  - **Done**: stesso sport, e distanza o durata dentro l'intervallo (con il
    15% di tolleranza sul numero secco);
  - **Changed**: stesso sport ma fuori dall'intervallo, oppure uno sport
    diverso;
  - **Missed**: seduta prevista, nessuna attivita';
  - **Rest kept**: riposo previsto e nessuna attivita', oppure solo l'attivita'
    indicata in `optional`;
  - **Extra**: riposo previsto e un'attivita' non indicata in `optional`;
  - **Upcoming**: il giorno non e' ancora arrivato.
- La pagina `app_pages/plan.py`, voce **Plan** nella navigazione, icona
  `:material/event_note:`:
  - si sceglie la settimana fra quelle che hanno un file (default: quella in
    corso, altrimenti l'ultima);
  - una tabella di 7 righe: giorno, previsto, fatto (sport, km, tempo, FC
    media), esito con un colore di sfondo per esito;
  - in cima, i totali della settimana previsti contro fatti: km di corsa,
    numero di sedute, sedute di qualita'.
- I piani oggi li scrive Claude a mano, su richiesta, e nessun agente ne ha le
  istruzioni. Scrivere in `summary/05.plan/README.md` il formato del front
  matter, cosi' anche i piani nuovi lo avranno.

## Vincoli

- Niente CSS e niente HTML (i colori dell'esito con `column_config` o con lo
  styler di pandas). Commenti in italiano senza accenti, UI in inglese.
- Non toccare le altre pagine, tranne la voce di navigazione in `app.py`.
- Il loader non deve fallire su un file scritto male: avviso e file saltato.

## Rischi

- Il 27 settembre 2026 sta nel file della settimana dopo (il piano parte dalla
  domenica). Il confronto va fatto per data, non per settimana ISO.
- Due attivita' nello stesso giorno (una camminata e una corsa): per l'esito
  conta quella dello sport previsto, le altre si mostrano ma non cambiano
  l'esito.
- Il piano e' scritto in inglese, l'agente ragiona in italiano: le chiavi YAML
  restano in inglese.

## Verifica

1. Con il file del 2026-09-28 e le attivita' fino al 26 settembre, tutti i
   giorni sono "Upcoming".
2. Aggiungendo a mano, in un database di prova, una corsa di 6.2 km il 28
   settembre, il 28 diventa "Done"; una di 3 km lo fa diventare "Changed".
3. Un file di piano senza front matter produce un avviso, non un'eccezione.
4. `AppTest` su tutte le pagine piu' un giro nel browser.

**Mai** lanciare `make update_activity` o `make backfill_activity_names`:
chiamano l'API Garmin e scrivono nell'albero dati. Il database di prova per la
verifica 2 va fatto su una copia, non su `activities.db`.
