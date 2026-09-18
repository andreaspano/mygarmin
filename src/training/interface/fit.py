"""Parsing dei file FIT delle attivita' (data/*_ACTIVITY.fit)."""

import json
import re
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fitparse import FitFile

_ACTIVITY_ID_RE = re.compile(r"(\d+)_ACTIVITY\.fit$")
_SEMICIRCLE_TO_DEGREES = 180 / 2**31
_NAMES_FILENAME = "activity_names.json"
LOCAL_TZ = ZoneInfo("Europe/Rome")


def _to_local(dt):
    """FIT timestamps are naive UTC (fitparse uses utcfromtimestamp);
    convert to naive local time so displayed times match the wall clock."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)


def load_activity_names(data_dir: Path) -> dict:
    path = Path(data_dir) / _NAMES_FILENAME
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _semicircles_to_degrees(value: int | None) -> float | None:
    return value * _SEMICIRCLE_TO_DEGREES if value is not None else None


def list_activity_files(data_dir: Path = Path("data")) -> list[Path]:
    return sorted(Path(data_dir).glob("*_ACTIVITY.fit"))


def activity_id_from_path(path: Path) -> int | None:
    match = _ACTIVITY_ID_RE.search(Path(path).name)
    return int(match.group(1)) if match else None


def load_activity_summary(path: Path) -> dict:
    """Legge il messaggio 'session' del file FIT: una riga di riepilogo."""
    fit = FitFile(str(path))
    session = next(fit.get_messages("session"), None)
    values = session.get_values() if session else {}

    return {
        "activity_id": activity_id_from_path(path),
        "path": str(path),
        "sport": values.get("sport"),
        "sub_sport": values.get("sub_sport"),
        "start_time": _to_local(values.get("start_time")),
        "total_distance_km": (values.get("total_distance") or 0) / 1000,
        "total_time_min": (values.get("total_elapsed_time") or 0) / 60,
        "avg_heart_rate": values.get("avg_heart_rate"),
        "max_heart_rate": values.get("max_heart_rate"),
        "avg_speed_kmh": (values.get("avg_speed") or 0) * 3.6,
        "total_calories": values.get("total_calories"),
        "total_ascent_m": values.get("total_ascent"),
        "total_descent_m": values.get("total_descent"),
    }


def load_activity_records(path: Path) -> pd.DataFrame:
    """Legge i messaggi 'record' del file FIT: una riga per ogni istante campionato."""
    fit = FitFile(str(path))
    rows = []
    for record in fit.get_messages("record"):
        values = record.get_values()
        rows.append(
            {
                "timestamp": _to_local(values.get("timestamp")),
                "heart_rate": values.get("heart_rate"),
                "speed_kmh": (values.get("enhanced_speed") or values.get("speed") or 0) * 3.6,
                "altitude_m": values.get("enhanced_altitude") or values.get("altitude"),
                "cadence": values.get("cadence"),
                "power": values.get("power"),
                "lat": _semicircles_to_degrees(values.get("position_lat")),
                "lon": _semicircles_to_degrees(values.get("position_long")),
                "distance_km": (values.get("distance") or 0) / 1000,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.set_index("timestamp")
    return df
