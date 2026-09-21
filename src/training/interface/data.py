"""Lettura delle attivita' per le pagine Streamlit, messa in cache.

`list_activities()` (db.py) chiama `sync()`: scandisce la directory di export,
apre SQLite e fa il parsing FIT dei file nuovi. E' il prezzo giusto da pagare
una volta, ma Streamlit rilancia lo script a ogni interazione, e cosi' quella
scansione finiva per ripetersi a ogni spunta di casella e a ogni click di riga.

Qui si mette in cache il *caricamento*, non i filtri che ci girano sopra:
quelli dipendono dai widget e vanno ricalcolati a ogni giro (sono comunque
operazioni su un DataFrame gia' in memoria).

Il decoratore sta qui e non su `list_activities` perche' quella la usa anche
`training-activity-reports`, che gira fuori da Streamlit: decorandola, la CLI
si porterebbe dietro una dipendenza da Streamlit e i suoi avvisi.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.db import list_activities

# Un minuto: abbastanza da coprire una raffica di interazioni (che e' il caso
# che ci interessa), abbastanza poco da non dover offrire un pulsante di
# aggiornamento. Un'attivita' scaricata mentre l'app e' aperta compare da se'
# entro un minuto, senza riavviare niente.
ACTIVITIES_TTL_SECONDS = 60


@st.cache_data(ttl=ACTIVITIES_TTL_SECONDS)
def load_activities(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Le attivita' come `list_activities()`, ma senza rifare la scansione a
    ogni rerun.

    `st.cache_data` restituisce una copia a ogni chiamata, quindi chi la riceve
    puo' aggiungere colonne (lo fa la pagina Week) senza sporcare la cache."""
    return list_activities(data_dir)
