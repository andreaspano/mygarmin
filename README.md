# mygarmin

## Configurazione

Tutta la configurazione sta in `user/config.yaml`: la cartella dei dati, il
token di login, il fuso orario, l'inizio dello storico, la pausa fra le
richieste a Garmin e le finestre in giorni. Cosa fa ogni chiave e' scritto nei
commenti del file.

Tutte le chiavi sono obbligatorie e non ci sono default nel codice: se il file
manca, se manca una chiave, se ce n'e' una sconosciuta o un valore e' del tipo
sbagliato, il programma si ferma all'avvio con un `ConfigError` che elenca
tutti i problemi insieme. Il file si cerca sempre nella radice del repo,
qualunque sia la cartella da cui si lancia il comando.
