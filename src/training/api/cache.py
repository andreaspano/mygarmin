"""Le attivita' e la salute di una cartella dati, tenute in memoria per un
minuto.

`list_activities()` (db.py) chiama `sync()`, che scandisce la cartella di
export, e `load_health_db()` chiama `sync_health()`, che guarda l'mtime di
ogni file di salute (decine di migliaia, circa un secondo): a ogni richiesta
renderebbero lenta ogni chiamata.

FastAPI serve gli endpoint sincroni su piu' thread: il lock evita che due
richieste insieme facciano due scansioni (e due `sync()` sullo stesso
database)."""

import threading
import time
from pathlib import Path

import pandas as pd

from training.interface.db import list_activities
from training.interface.health_db import load_health_db

# Lo stesso minuto di `interface/data.py`: un'attivita' scaricata mentre il
# server gira compare da se', senza riavviarlo.
ACTIVITIES_TTL_SECONDS = 60

_lock = threading.Lock()
_cache: dict[Path, tuple[float, pd.DataFrame]] = {}
# Un lucchetto a parte: la salute impiega un secondo, le attivita' non
# devono aspettarla.
_health_lock = threading.Lock()
_health_cache: dict[Path, tuple[float, pd.DataFrame]] = {}


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


def load_health(data_dir: Path) -> pd.DataFrame:
    """La salute come `load_health_db()`, ricaricata al piu' una volta al
    minuto come `load_activities()`. Rende una copia."""
    key = Path(data_dir)
    with _health_lock:
        cached = _health_cache.get(key)
        if cached is None or time.monotonic() - cached[0] > ACTIVITIES_TTL_SECONDS:
            cached = (time.monotonic(), load_health_db(key))
            _health_cache[key] = cached
    return cached[1].copy()


def invalidate(data_dir: Path) -> None:
    """Dimentica attivita' e salute di una cartella dati: la prossima richiesta le
    rilegge. Dopo una scrittura (il terreno, todo 35), cosi' la modifica si
    vede subito e non dopo un minuto."""
    with _lock:
        _cache.pop(Path(data_dir), None)
    with _health_lock:
        _health_cache.pop(Path(data_dir), None)
