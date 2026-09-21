"""Parsing dei file FIT delle attivita' (data/*_ACTIVITY.fit)."""

import json
import re
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from fitparse import FitFile

from training.garmin.config import DATA_DIR

_ACTIVITY_ID_RE = re.compile(r"(\d+)_ACTIVITY\.fit$")
_SEMICIRCLE_TO_DEGREES = 180 / 2**31
_NAMES_FILENAME = "activity_names.json"
_TYPES_FILENAME = "activity_types.json"
LOCAL_TZ = ZoneInfo("Europe/Rome")


def _to_local(dt):
    """FIT timestamps are naive UTC (fitparse uses utcfromtimestamp);
    convert to naive local time so displayed times match the wall clock."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)


def load_activity_names(data_dir: Path) -> dict:
    return _load_json_map(Path(data_dir) / _NAMES_FILENAME)


def load_activity_types(data_dir: Path) -> dict:
    """Il tipo attivita' secondo Garmin Connect (es. "running"), salvato da
    training.garmin.activities: serve quando il FIT non lo sa (sport
    "generic" delle attivita' registrate seguendo un percorso)."""
    return _load_json_map(Path(data_dir) / _TYPES_FILENAME)


def _load_json_map(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _semicircles_to_degrees(value: int | None) -> float | None:
    return value * _SEMICIRCLE_TO_DEGREES if value is not None else None


def list_activity_files(data_dir: Path = DATA_DIR) -> list[Path]:
    return sorted(Path(data_dir).glob("*_ACTIVITY.fit"))


def activity_id_from_path(path: Path) -> int | None:
    match = _ACTIVITY_ID_RE.search(Path(path).name)
    return int(match.group(1)) if match else None


# Il VO2max stimato dall'orologio sta in un messaggio non documentato, il
# numero 140 (lo scrive il motore Firstbeat), nel campo 7, come intero scalato:
# VO2max = raw * 3.5 / 65536 (753282 -> 40.2 ml/kg/min). La formula viene dal
# lavoro di chi ha decodificato i file a mano, ed e' stata controllata contro
# i `vO2MaxValue` che l'API Garmin ha dato a `fitness-status` per le stesse
# corse (settembre 2026: 40.0/40, 39.5/39, 39.4/39, 40.1/40): combaciano, con
# un decimale in piu' nel file.
#
# Non e' sempre una stima fatta *su quella* attivita': e' il valore corrente
# dell'orologio a fine attivita'. Le corse che si qualificano lo aggiornano,
# le altre attivita' se lo portano dietro (lo hanno anche sci e camminate).
_VO2MAX_MESSAGE = 140
_VO2MAX_FIELD = 7
_VO2MAX_SCALE = 3.5 / 65536
# Fuori da qui il numero non e' un VO2max di una persona: il campo non e'
# documentato, un firmware nuovo potrebbe spostarlo, e una cella vuota e'
# meglio di un valore assurdo.
_VO2MAX_PLAUSIBLE = (10.0, 100.0)


def _vo2max(fit: FitFile) -> float | None:
    """Il VO2max dell'orologio a fine attivita', o None se non c'e'.

    Vuole lo stesso `FitFile` gia' aperto per `session`: fitparse il file lo
    legge tutto alla prima richiesta, quindi questa non costa un altro parsing.
    Un campo a zero vuol dire "nessuna stima" (succede per le corse che
    l'orologio non considera, come quelle su sentiero)."""
    for message in fit.get_messages(_VO2MAX_MESSAGE):
        for field in message.fields:
            if field.def_num == _VO2MAX_FIELD and isinstance(field.value, (int, float)):
                value = field.value * _VO2MAX_SCALE
                low, high = _VO2MAX_PLAUSIBLE
                return round(value, 1) if low <= value <= high else None
    return None


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
        "vo2max": _vo2max(fit),
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
