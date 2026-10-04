---
status: todo
---

# ML: classificare le sedute per tipo (facile, medio, ripetute, salita)

Ogni seduta ha un nome ("Canegrate Running") che non dice com'e' stata. Dai
dati al secondo si puo' dire se era un lento, un medio, delle ripetute o una
salita, senza etichettare niente a mano. Ne esce la **distribuzione
d'intensita'** settimana per settimana, cioe' la cosa che il report
settimanale nota come mancante ("almost no harder efforts").

**Da fare dopo il todo 19** (pacchetto `analysis/`). Se il todo 12 (zone di
FC) e' gia' fatto, si riusano le sue zone.

## Work

- `analysis/session_clusters.py`:
  - **caratteristiche per seduta**, dai `records`: durata, FC media e
    massima in percentuale della FC massima, tempo sopra l'80% e il 90%,
    variabilita' della velocita' (coefficiente di variazione), numero di
    blocchi veloci (ripetute), dislivello per km, pendenza media in salita;
  - per sport (corsa e bici separate: le stesse cifre vogliono dire cose
    diverse);
  - standardizzazione e `KMeans` di scikit-learn, con il numero di gruppi
    scelto con il silhouette (fra 3 e 6);
  - **nomi dei gruppi** scritti dal codice a partire dai centri (per esempio
    il gruppo con FC piu' bassa e velocita' costante e' "easy"), non a mano;
  - risultato in una tabella `session_types (activity_id, cluster, label)`
    in `activities.db`, con il suo salto di `logic_version`.
- CLI `training-session-clusters` e `make session_clusters`: i gruppi con il
  loro profilo e qualche seduta di esempio; la distribuzione per settimana
  delle ultime 12 settimane; report in
  `summary/06.analysis/session_clusters.md`, in inglese.

## Vincoli

- Nessuna dipendenza nuova oltre a scikit-learn (todo 19).
- `random_state` fisso.
- Niente pagine nell'app (la distribuzione per settimana nella pagina Week e'
  un todo a parte).
- Commenti in italiano senza accenti, report in inglese.

## Rischi

- **I gruppi possono non avere un senso sportivo**: per questo i nomi
  vengono dai centri, e il report mostra esempi di sedute per gruppo, cosi'
  si controlla a occhio.
- **Sedute senza FC** (vecchi orologi, attivita' senza fascia): restano
  fuori, con il loro conteggio.
- **Cambiano i gruppi aggiungendo dati**: ogni nuovo calcolo puo' rinumerare
  i gruppi. Il nome viene dal profilo, non dal numero, cosi' resta stabile.

## Verifica

1. Una seduta di ripetute nota (per esempio quella del 30 settembre 2026, se
   fatta come da piano) finisce nel gruppo "intervals" o simile.
2. Una corsa lenta finisce nel gruppo "easy".
3. Silhouette e numero di gruppi stampati.
4. Due giri: stessi gruppi e stessi nomi.
