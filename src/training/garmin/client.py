"""Wrapper per le chiamate API Garmin con gestione degli errori transitori."""

import time

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


def safe_call(func, *args, retries: int = 3, **kwargs):
    """Esegue una chiamata API gestendo i casi piu' comuni di errore
    transitorio (rate limit, connessione), senza far fallire tutto lo
    script per un singolo giorno/attivita' problematici."""
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except GarminConnectTooManyRequestsError:
            wait = 60 * attempt
            print(f"    Troppe richieste: pausa di {wait}s...")
            time.sleep(wait)
        except GarminConnectConnectionError as e:
            print(f"    Errore di connessione ({e}): nuovo tentativo tra 10s...")
            time.sleep(10)
        except GarminConnectAuthenticationError:
            raise
        except Exception:
            # Molti endpoint restituiscono un errore quando per quel
            # giorno/quella attivita' semplicemente non ci sono dati:
            # non e' un guasto, quindi non insistiamo.
            return None
    return None
