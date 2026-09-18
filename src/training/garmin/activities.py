"""Esportazione dell'elenco attivita' e dei relativi file originali (FIT)."""

import io
import json
import re
import time
import zipfile
from pathlib import Path

from garminconnect import Garmin

from .auth import init_api
from .client import safe_call
from .config import REQUEST_DELAY

_ACTIVITY_ID_RE = re.compile(r"(\d+)_ACTIVITY\.fit$")
_NAMES_FILENAME = "activity_names.json"


def _names_path(data_dir: Path) -> Path:
    return Path(data_dir) / _NAMES_FILENAME


def _load_activity_names(data_dir: Path) -> dict:
    path = _names_path(data_dir)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_activity_names(data_dir: Path, names: dict) -> None:
    with open(_names_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2, sort_keys=True)


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


def _existing_activity_ids(data_dir: Path) -> set:
    ids = set()
    for path in data_dir.glob("*_ACTIVITY.fit"):
        match = _ACTIVITY_ID_RE.search(path.name)
        if match:
            ids.add(int(match.group(1)))
    return ids


def download_activities_between(
    api: Garmin, start_date: str, end_date: str, data_dir: Path = Path("data")
) -> list:
    """Scarica in data_dir tutte le attivita' comprese tra start_date e
    end_date (formato 'YYYY-MM-DD', estremi inclusi) non ancora presenti."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    existing_ids = _existing_activity_ids(data_dir)
    names = _load_activity_names(data_dir)

    print(f"Recupero le attivita' tra {start_date} e {end_date} da Garmin Connect...")
    activities = safe_call(api.get_activities_by_date, start_date, end_date)
    activities = activities or []
    to_download = []
    for act in activities:
        activity_id = act.get("activityId")
        if activity_id is None:
            continue
        # Il nome non e' contenuto nel file FIT: arriva solo con l'elenco
        # delle attivita', quindi lo salviamo ora che ce l'abbiamo.
        if act.get("activityName"):
            names[str(activity_id)] = act["activityName"]
        if activity_id not in existing_ids:
            to_download.append(act)

    _save_activity_names(data_dir, names)

    if not to_download:
        print(f"Nessuna nuova attivita' da scaricare per l'intervallo {start_date} .. {end_date}.")
        return []

    print(f"Trovate {len(to_download)} nuove attivita'. Scarico ed estraggo in {data_dir.resolve()}...")
    downloaded = []
    for i, act in enumerate(to_download, 1):
        activity_id = act["activityId"]
        data = safe_call(
            api.download_activity, activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL
        )
        if data is None:
            print(f"  [{i}/{len(to_download)}] ATTENZIONE: impossibile scaricare l'attivita' {activity_id}")
            time.sleep(REQUEST_DELAY)
            continue

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(data_dir)

        downloaded.append(activity_id)
        print(f"  [{i}/{len(to_download)}] estratta attivita' {activity_id}")
        time.sleep(REQUEST_DELAY)

    print(f"Fatto: {len(downloaded)} nuove attivita' aggiunte a {data_dir.resolve()}")
    return downloaded


def update_activity(data_dir: Path = Path("data")) -> list:
    """Si connette a Garmin Connect e scarica in data_dir le attivita' piu'
    recenti di quella gia' presente, estraendo lo zip originale di ognuna.

    Le attivita' vengono richieste dalla piu' recente alla piu' vecchia:
    ci si ferma alla prima gia' presente in data_dir, assumendo che tutte
    quelle precedenti siano gia' state scaricate."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    existing_ids = _existing_activity_ids(data_dir)
    names = _load_activity_names(data_dir)

    api = init_api()

    print("Recupero le attivita' piu' recenti da Garmin Connect...")
    new_ids = []
    start, limit = 0, 100
    while True:
        batch = safe_call(api.get_activities, start, limit)
        if not batch:
            break

        stop = False
        for act in batch:
            activity_id = act.get("activityId")
            if activity_id is None:
                continue
            if act.get("activityName"):
                names[str(activity_id)] = act["activityName"]
            if activity_id in existing_ids:
                stop = True
                break
            new_ids.append(activity_id)

        if stop or len(batch) < limit:
            break
        start += limit
        time.sleep(REQUEST_DELAY)

    _save_activity_names(data_dir, names)

    if not new_ids:
        print("Nessuna nuova attivita' da scaricare.")
        return []

    print(f"Trovate {len(new_ids)} nuove attivita'. Scarico ed estraggo in {data_dir.resolve()}...")
    downloaded = []
    for i, activity_id in enumerate(new_ids, 1):
        data = safe_call(
            api.download_activity, activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL
        )
        if data is None:
            print(f"  [{i}/{len(new_ids)}] ATTENZIONE: impossibile scaricare l'attivita' {activity_id}")
            time.sleep(REQUEST_DELAY)
            continue

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(data_dir)

        downloaded.append(activity_id)
        print(f"  [{i}/{len(new_ids)}] estratta attivita' {activity_id}")
        time.sleep(REQUEST_DELAY)

    print(f"Fatto: {len(downloaded)} nuove attivita' aggiunte a {data_dir.resolve()}")
    return downloaded


def backfill_activity_names(data_dir: Path = Path("data")) -> dict:
    """Recupera da Garmin Connect i nomi di tutte le attivita' gia' presenti
    in data_dir ma non ancora salvate in activity_names.json (ad es. quelle
    scaricate prima che questa funzionalita' esistesse)."""
    data_dir = Path(data_dir)
    existing_ids = _existing_activity_ids(data_dir)
    names = _load_activity_names(data_dir)
    missing = {i for i in existing_ids if str(i) not in names}
    if not missing:
        print("Tutti i nomi delle attivita' sono gia' presenti.")
        return names

    api = init_api()
    print(f"Recupero i nomi di {len(missing)} attivita'...")
    start, limit = 0, 100
    while missing:
        batch = safe_call(api.get_activities, start, limit)
        if not batch:
            break
        for act in batch:
            activity_id = act.get("activityId")
            if activity_id in missing and act.get("activityName"):
                names[str(activity_id)] = act["activityName"]
                missing.discard(activity_id)
        if len(batch) < limit:
            break
        start += limit
        time.sleep(REQUEST_DELAY)

    _save_activity_names(data_dir, names)
    if missing:
        print(f"ATTENZIONE: nome non trovato per {len(missing)} attivita': {sorted(missing)}")
    return names
