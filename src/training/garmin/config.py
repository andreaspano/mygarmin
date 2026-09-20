"""Costanti di configurazione per il backup Garmin Connect.

Modifica questi valori secondo le tue esigenze, in particolare
START_DATE: l'intervallo di date incide molto sul tempo totale (una
richiesta per ogni giorno x 8 metriche, con una piccola pausa tra una
richiesta e l'altra per non farsi bloccare da Garmin). Con l'intervallo
di default (dal 2015 a oggi) puo' volerci qualche ora: per un primo test
riduci START_DATE a pochi mesi fa.
"""

import os
from datetime import date
from pathlib import Path

# Cartella dove verra' salvato tutto (verra' creata se non esiste): usata
# sia dal backup completo sia dall'interfaccia e dallo stato di forma
DATA_DIR = Path("~/adrive/data/garmin-export").expanduser()
OUTPUT_DIR = DATA_DIR

# Intervallo di date per le metriche giornaliere di salute.
# Garmin Connect esiste dal 2013-2014: se il tuo primo dispositivo Garmin
# e' piu' recente, sposta pure START_DATE in avanti per risparmiare tempo.
START_DATE = date(2015, 1, 1)
END_DATE = date.today()

# Pausa (in secondi) tra una richiesta e l'altra verso Garmin, per non
# superare i limiti di frequenza del servizio (che non sono documentati
# pubblicamente). Se ricevi molti errori "too many requests", aumentala.
REQUEST_DELAY = 0.3

# Dove salvare/riusare il token di login (evita di reinserire la password
# ogni volta che rilanci lo script)
TOKEN_STORE = os.path.expanduser("~/token")

# Numero di giorni (compreso oggi) considerati nella finestra "recente" per
# lo snapshot dello stato di forma (training.garmin.fitness_status)
FITNESS_STATUS_WINDOW_DAYS = 14
