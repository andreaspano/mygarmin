---
status: done
---

# Il piano giorno per giorno, e Next che lo legge

Il todo 57 ha portato i piani di `plan/` nella pagina. Quelli sono il blocco:
diciotto settimane, i ritmi, i controlli. Quello che manca e' la seduta di
**domani**, e il posto dove serve e' il report, non una pagina da sfogliare.

## Le sedute

Diciotto file in `summary/05.plan/`, uno per settimana col nome del lunedi',
dal `2026-10-26` al `2027-02-22`: la mezza del 28 febbraio 2027 in 2h20. Il
formato e' quello deciso dal todo 14 — front matter YAML per la macchina,
tabella dei sette giorni per chi legge — piu' i ritmi e le soglie di scarico
in fondo a ogni file, cosi' una settimana si legge senza aprire il blocco.

Generati dal piano, non scritti a mano uno per uno: i km, il lungo e il numero
di sedute dure di ogni settimana coincidono con la tabella di
`plan/half_marathon_2.20.md` perche' vengono da quella. Il formato sta in
`summary/05.plan/README.md`.

## Next

`_week_plan` in `api/refresh.py` cerca il file della settimana e, se c'e', lo
nomina nel prompt di Next. Per l'agente la seduta prevista e' il punto di
partenza: la prescrive se le sezioni sono d'accordo, la cambia se non lo sono,
e in quel caso **dice cosa ha cambiato e perche'**. `.claude/agents/06_next.md`
e `w6_next.md` hanno la regola per iscritto, compreso il caso scomodo: se il
piano dice riposo e il corpo sta bene, resta riposo.

**La data non e' quella del report.** Il Next della sera parla di domani e
quello della settimana della settimana che comincia il giorno dopo, quindi la
domenica sera la riga da leggere sta nel file della settimana dopo
(`_next_subject`). Scritto nel primo giro e sbagliato: il prompt chiedeva la
riga del giorno del report.

Il piano lo vede solo Next. Le altre sezioni raccontano com'e' andata, e
quello che era previsto non cambia i loro numeri.

## Vincoli

- Niente file, niente frase nel prompt: i giorni fuori da un blocco si
  scrivono come prima. Un piano che non c'e' non deve diventare
  un'istruzione da inventare.
- Gli agenti hanno `Read` senza restrizioni: nessun permesso nuovo.
- Commenti in italiano senza accenti, piani e report in inglese.

## Verifica

1. I diciotto front matter si leggono con `yaml.safe_load`, hanno sette
   giorni consecutivi da lunedi a domenica, la catena delle settimane non ha
   buchi e la gara cade l'ultima domenica, 21.097 km.
2. I totali di ogni file (km, corsa piu' lunga, sedute dure) coincidono con la
   tabella delle 18 settimane del blocco.
3. Il prompt di Next nei quattro casi: giorno/mattina, giorno/sera,
   domenica/sera (file della settimana dopo), settimana/chiusura; e un giorno
   di settembre, dove la frase non c'e'.
4. Fatto per davvero su una sezione:
   `training-daily-report --day 2026-10-26 --section next --moment evening
   --no-update`. Ha prescritto i 5 km lenti del piano con i suoi ritmi, ha
   tolto gli allunghi per il respiro alto e l'HRV bassa, e l'ha detto.
