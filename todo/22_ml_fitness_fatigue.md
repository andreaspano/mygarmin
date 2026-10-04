---
status: todo
---

# ML: modello fitness-fatica (Banister) con le tue costanti

Il modello impulso-risposta di Banister: ogni seduta aggiunge **forma** (che
sale piano e dura a lungo) e **fatica** (che sale di colpo e passa in fretta).
La prestazione e' forma meno fatica. Adattandolo ai tuoi dati si ricavano le
**tue** costanti di tempo: quanti giorni ti servono per smaltire la fatica, e
quanto dura la forma. E' quello che il carico acuto e cronico di Garmin
approssima con costanti fisse (7 e 28 giorni).

**Da fare dopo i todo 19 e 21**: usa il TRIMP giornaliero (`daily_frame()`)
come carico e l'indice di efficienza aerobica (todo 21) come prestazione.

## Work

- `analysis/fitness_fatigue.py`:
  - forma e fatica come somme esponenziali del TRIMP giornaliero, con costanti
    `tau_fitness`, `tau_fatigue` e pesi `k1`, `k2`;
  - adattamento ai dati con `scipy.optimize.least_squares`, con limiti
    plausibili (`tau_fitness` 20-60 giorni, `tau_fatigue` 3-15);
  - **prestazione osservata**: l'indice di efficienza aerobica delle corse
    (todo 21); in alternativa la readiness del mattino, come confronto;
  - validazione: adattato su tutto tranne gli ultimi 6 mesi, provato su
    quelli;
  - uscita: le costanti adattate, e la curva di forma, fatica e prestazione
    prevista giorno per giorno.
- CLI `training-fitness-fatigue` e `make fitness_fatigue`; report in
  `summary/06.analysis/fitness_fatigue.md`, in inglese: "your fatigue clears
  in about N days, your fitness lasts about M weeks", e cosa vuol dire.
- **Dipendenza nuova**: `scipy` (via `uv add`; arriva gia' con scikit-learn,
  ma va dichiarata perche' la si usa direttamente).

## Vincoli

- Solo dati locali; niente pagine nell'app.
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **Il modello e' fragile**: costanti diverse danno curve simili, e
  l'ottimizzazione puo' fermarsi su un minimo locale. Si parte da piu' punti
  iniziali e si riporta quanto le costanti sono incerte.
- **La prestazione misurata e' rumorosa** (todo 21): se l'adattamento non e'
  migliore di una prestazione costante, il report lo dice invece di
  pubblicare costanti senza senso.
- **TRIMP** solo per le sedute con FC: le altre contano zero, e quanto pesano
  va stampato.

## Verifica

1. Dati sintetici generati con costanti note: l'adattamento le ritrova
   (entro il 10%).
2. Sui dati veri: costanti dentro i limiti e non schiacciate sul bordo (se lo
   sono, il report lo dice).
3. Errore sui 6 mesi di prova confrontato con quello di una prestazione
   costante.
4. Due giri: stessi numeri.
