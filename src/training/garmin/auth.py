"""Login a Garmin Connect, riusando un token salvato quando possibile."""

import getpass

from garminconnect import Garmin

from .config import TOKEN_STORE


def _ask_mfa_code() -> str:
    return input("Codice MFA/one-time inviato da Garmin: ").strip()


def init_api() -> Garmin:
    """Prova a riusare un token salvato; se non c'e' o non e' valido,
    chiede email e password e fa un login completo."""
    try:
        api = Garmin()
        api.login(TOKEN_STORE)
        print("Login effettuato riusando il token salvato.")
        return api
    except Exception:
        print("Nessun token valido trovato: serve un login completo.\n")
        email = input("Email Garmin: ").strip()
        password = getpass.getpass("Password Garmin (non verra' mostrata): ")
        api = Garmin(email=email, password=password, prompt_mfa=_ask_mfa_code)
        api.login(TOKEN_STORE)
        print("Login riuscito. Il token e' stato salvato per i prossimi avvii.\n")
        return api
