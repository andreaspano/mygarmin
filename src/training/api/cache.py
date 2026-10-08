"""Le attivita' di una cartella dati, tenute in memoria per un minuto.

`list_activities()` (db.py) chiama `sync()`, che scandisce la cartella di
export: a ogni richiesta renderebbe lenta ogni chiamata. E' la stessa
ragione di `interface/data.py`, che pero' usa la cache di Streamlit, e l'API
non deve dipendere da Streamlit.

FastAPI serve gli endpoint sincroni su piu' thread: il lock evita che due
richieste insieme facciano due scansioni (e due `sync()` sullo stesso
database)."""

import threading
import time
from pathlib import Path

import pandas as pd

from training.interface.db import list_activities

# Lo stesso minuto di `interface/data.py`: un'attivita' scaricata mentre il
# server gira compare da se', senza riavviarlo.
ACTIVITIES_TTL_SECONDS = 60

_lock = threading.Lock()
_cache: dict[Path, tuple[float, pd.DataFrame]] = {}


def load_activities(data_dir: Path) -> pd.DataFrame:
    """Le attivita' come `list_activities()`, ricaricate al piu' una volta al
    minuto per cartella dati. Rende una copia: chi la riceve puo' filtrarla e
    aggiungere colonne senza sporcare la cache."""
    key = Path(data_dir)
    with _lock:
        cached = _cache.get(key)
        if cached is None or time.monotonic() - cached[0] > ACTIVITIES_TTL_SECONDS:
            cached = (time.monotonic(), list_activities(key))
            _cache[key] = cached
    return cached[1].copy()
