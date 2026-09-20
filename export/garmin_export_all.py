#!/usr/bin/env python3
"""
garmin_export_all.py
=====================

Backup completo (non ufficiale) del tuo account Garmin Connect: attività
(file originali), dati di salute/wellness giorno per giorno, peso,
dispositivi e record personali.

Usa la libreria open source "python-garminconnect", che replica le
chiamate dell'app mobile Garmin Connect. NON e' un'API ufficiale Garmin:
puo' rompersi se Garmin cambia i suoi endpoint interni. Le tue credenziali
restano sul TUO computer: questo script le usa solo per il login e poi
salva un token locale, non le invia mai altrove.

INSTALLAZIONE
--------------
    python3 -m venv venv
    source venv/bin/activate        # su Windows: venv\\Scripts\\activate
    pip install garminconnect

USO
---
    python3 garmin_export_all.py

Al primo avvio ti chiedera' email, password (non verra' mostrata a schermo)
ed eventualmente il codice MFA se lo hai attivato. Il login successivo
riusera' il token salvato in ~/token senza richiedere di nuovo
la password, finche' il token resta valido.

Lo script e' RIPRENDIBILE: se lo interrompi (Ctrl+C) o Garmin ti blocca
temporaneamente per troppe richieste, puoi rilanciarlo e riprendera' da
dove aveva lasciato (salta i file/le date gia' scaricate).

CONFIGURAZIONE
---------------
Modifica le costanti qui sotto prima di lanciarlo, in particolare
START_DATE: l'intervallo di date incide molto sul tempo totale (una
richiesta per ogni giorno x 8 metriche, con una piccola pausa tra una
richiesta e l'altra per non farsi bloccare da Garmin). Con l'intervallo
di default (dal 2015 a oggi) puo' volerci qualche ora: per un primo test
riduci START_DATE a pochi mesi fa.
"""

import json
import os
import sys
import time
import getpass
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from garminconnect import (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
except ImportError:
    sys.exit(
        "Manca la libreria 'garminconnect'. Installala con:\n"
        "    pip install garminconnect\n"
        "e rilancia questo script."
    )

# ----------------------------------------------------------------------
# CONFIGURAZIONE — modifica questi valori secondo le tue esigenze
# ----------------------------------------------------------------------

# Cartella dove verra' salvato tutto (verra' creata se non esiste)
OUTPUT_DIR = Path("~/adrive/data/garmin-export").expanduser()

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


# ----------------------------------------------------------------------
# LOGIN
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# ATTIVITA'
# ----------------------------------------------------------------------

def export_activities(api: Garmin, out_dir: Path) -> list:
    activities_dir = out_dir / "activities"
    fit_dir = activities_dir / "fit"
    fit_dir.mkdir(parents=True, exist_ok=True)

    summary_path = activities_dir / "activities_summary.json"
    all_activities = []

    print("Recupero l'elenco di tutte le attivita'...")
    start, limit = 0, 100
    while True:
        batch = safe_call(api.get_activities, start, limit)
        if not batch:
            break
        all_activities.extend(batch)
        print(f"  ...{len(all_activities)} attivita' trovate finora")
        if len(batch) < limit:
            break
        start += limit
        time.sleep(REQUEST_DELAY)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_activities, f, ensure_ascii=False, indent=2, default=str)
    print(f"Totale attivita' trovate: {len(all_activities)} (elenco salvato in {summary_path})")

    print("Scarico i file originali (FIT, zippati da Garmin) di ogni attivita'...")
    for i, act in enumerate(all_activities, 1):
        activity_id = act.get("activityId")
        if activity_id is None:
            continue
        target = fit_dir / f"{activity_id}.zip"
        if target.exists():
            continue  # gia' scaricata in un run precedente
        data = safe_call(
            api.download_activity, activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL
        )
        if data:
            with open(target, "wb") as f:
                f.write(data)
            if i % 25 == 0 or i == len(all_activities):
                print(f"  [{i}/{len(all_activities)}] scaricate finora...")
        else:
            print(f"  [{i}/{len(all_activities)}] ATTENZIONE: impossibile scaricare l'attivita' {activity_id}")
        time.sleep(REQUEST_DELAY)

    return all_activities


# ----------------------------------------------------------------------
# METRICHE GIORNALIERE DI SALUTE
# ----------------------------------------------------------------------

DAILY_ENDPOINTS = {
    "stats": lambda api, d: api.get_stats(d),
    "sleep": lambda api, d: api.get_sleep_data(d),
    "stress": lambda api, d: api.get_stress_data(d),
    "hrv": lambda api, d: api.get_hrv_data(d),
    "spo2": lambda api, d: api.get_spo2_data(d),
    "respiration": lambda api, d: api.get_respiration_data(d),
    "resting_heart_rate": lambda api, d: api.get_rhr_day(d),
    "training_readiness": lambda api, d: api.get_training_readiness(d),
}


def export_daily_health(api: Garmin, out_dir: Path, start_date: date, end_date: date) -> None:
    health_dir = out_dir / "health"
    for name in DAILY_ENDPOINTS:
        (health_dir / name).mkdir(parents=True, exist_ok=True)

    total_days = (end_date - start_date).days + 1
    print(f"Scarico le metriche giornaliere di salute per {total_days} giorni "
          f"({start_date} -> {end_date})...")
    print("(puoi interrompere con Ctrl+C e rilanciare piu' tardi: riprendera' da dove eri arrivato)")

    d = start_date
    day_count = 0
    while d <= end_date:
        date_str = d.strftime("%Y-%m-%d")
        day_count += 1

        for name, func in DAILY_ENDPOINTS.items():
            target = health_dir / name / f"{date_str}.json"
            if target.exists():
                continue
            data = safe_call(func, api, date_str)
            if data is not None:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            time.sleep(REQUEST_DELAY)

        if day_count % 30 == 0 or d == end_date:
            print(f"  ...elaborati {day_count}/{total_days} giorni (ultimo: {date_str})")

        d += timedelta(days=1)


# ----------------------------------------------------------------------
# DATI VARI: profilo, dispositivi, peso, record personali
# ----------------------------------------------------------------------

def export_misc(api: Garmin, out_dir: Path, start_date: date, end_date: date) -> None:
    misc_dir = out_dir / "misc"
    misc_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    calls = {
        "profile.json": lambda: api.get_full_name(),
        "devices.json": lambda: api.get_devices(),
        "personal_records.json": lambda: api.get_personal_record(),
        "body_composition.json": lambda: api.get_body_composition(start_str, end_str),
        "weigh_ins.json": lambda: api.get_weigh_ins(start_str, end_str),
    }

    print("Scarico profilo, dispositivi, peso e record personali...")
    for filename, func in calls.items():
        data = safe_call(func)
        if data is not None:
            with open(misc_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"  Salvato {filename}")
        else:
            print(f"  Non disponibile: {filename}")
        time.sleep(REQUEST_DELAY)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main() -> None:
    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Backup completo dati Garmin Connect")
    print(f"Cartella di destinazione: {out_dir.resolve()}")
    print("=" * 70)

    api = init_api()

    export_activities(api, out_dir)
    print()
    export_misc(api, out_dir, START_DATE, END_DATE)
    print()
    export_daily_health(api, out_dir, START_DATE, END_DATE)

    print()
    print("Fatto! Tutti i dati sono in:", out_dir.resolve())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Rilancia lo script quando vuoi: riprendera' da dove eri arrivato.")
