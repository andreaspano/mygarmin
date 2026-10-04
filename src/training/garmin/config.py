"""Configurazione, letta da `user/config.yaml`.

Il file sta nella radice del repo, sotto `user/`, ed e' l'unica fonte: non ci
sono default nel codice e nessuna variabile d'ambiente lo scavalca. Se il file
manca, o manca una chiave, il programma si ferma all'import con un
`ConfigError` che elenca tutto quello che non va in un messaggio solo, cosi'
non si scoprono i problemi uno alla volta. Lo stesso per le chiavi sconosciute
(un refuso come `data_dirr` va detto per nome, non come "manca data_dir") e
per i valori del tipo sbagliato.

Il resto del codice importa i valori da qui, con i nomi di sempre
(`DATA_DIR`, `REQUEST_DELAY`, ...): cosa significa ogni chiave lo dicono i
commenti nel file YAML, che e' dove si cambiano.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

# La radice del repo e non la cartella corrente: la configurazione si deve
# trovare da qualunque cartella si lanci il programma.
CONFIG_PATH = Path(__file__).resolve().parents[3] / "user" / "config.yaml"


class ConfigError(RuntimeError):
    """La configurazione manca, e' incompleta o ha valori sbagliati."""


@dataclass(frozen=True)
class Config:
    data_dir: Path
    token_store: str
    local_tz: ZoneInfo
    history_start: date
    request_delay: float
    health_refresh_days: int
    fitness_status_window_days: int


def _is_number(value: Any) -> bool:
    # I `bool` sono `int` in Python, ma `true` non e' una pausa ne' un numero
    # di giorni: e' una chiave scritta male, e va detto.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _path(value: Any) -> tuple[Any, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "deve essere un path (testo non vuoto)"
    return Path(value).expanduser(), None


def _token_store(value: Any) -> tuple[Any, str | None]:
    path, problem = _path(value)
    return (str(path) if path is not None else None), problem


def _local_tz(value: Any) -> tuple[Any, str | None]:
    if not isinstance(value, str):
        return None, "deve essere un fuso orario, per esempio Europe/Rome"
    try:
        return ZoneInfo(value), None
    except (ZoneInfoNotFoundError, ValueError):
        return None, f"fuso orario sconosciuto: {value!r}"


def _history_start(value: Any) -> tuple[Any, str | None]:
    # YAML legge gia' 2025-01-01 come `date`; una stringa vuol dire che la
    # data e' scritta male (o tra virgolette).
    if not isinstance(value, date):
        return None, "deve essere una data nella forma YYYY-MM-DD"
    if value > date.today():
        return None, f"e' nel futuro: {value}"
    return value, None


def _request_delay(value: Any) -> tuple[Any, str | None]:
    if not _is_number(value) or value < 0:
        return None, "deve essere un numero di secondi, zero o piu'"
    return float(value), None


def _days(value: Any) -> tuple[Any, str | None]:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return None, "deve essere un numero intero di giorni, almeno 1"
    return value, None


# Una funzione per chiave: torna il valore convertito, o il problema.
_FIELDS = {
    "data_dir": _path,
    "token_store": _token_store,
    "local_tz": _local_tz,
    "history_start": _history_start,
    "request_delay": _request_delay,
    "health_refresh_days": _days,
    "fitness_status_window_days": _days,
}


def load_config(path: Path) -> Config:
    """La configurazione letta da `path`, o `ConfigError` con tutti i
    problemi trovati."""
    if not path.exists():
        raise ConfigError(f"Manca il file di configurazione: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} non e' YAML valido:\n{exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} deve contenere delle chiavi (chiave: valore)")

    problems = []
    missing = [key for key in _FIELDS if key not in raw]
    if missing:
        problems.append("chiavi mancanti: " + ", ".join(missing))
    unknown = [str(key) for key in raw if key not in _FIELDS]
    if unknown:
        problems.append("chiavi sconosciute: " + ", ".join(unknown))

    values = {}
    for key, convert in _FIELDS.items():
        if key not in raw:
            continue
        value, problem = convert(raw[key])
        if problem:
            problems.append(f"{key}: {problem}")
        values[key] = value

    if problems:
        raise ConfigError(
            f"Configurazione non valida in {path}:\n" + "\n".join(f"  - {p}" for p in problems)
        )
    return Config(**values)


_config = load_config(CONFIG_PATH)

DATA_DIR = _config.data_dir
# Lo stesso posto: il backup completo e l'interfaccia lavorano sugli stessi file.
OUTPUT_DIR = DATA_DIR
TOKEN_STORE = _config.token_store
LOCAL_TZ = _config.local_tz
HISTORY_START = _config.history_start
REQUEST_DELAY = _config.request_delay
HEALTH_REFRESH_DAYS = _config.health_refresh_days
FITNESS_STATUS_WINDOW_DAYS = _config.fitness_status_window_days
