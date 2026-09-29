"""Lettura delle metriche giornaliere di salute dai JSON di Garmin.

Un file per giorno e per endpoint, in `DATA_DIR/health/<endpoint>/<data>.json`
(li scrive `garmin/health.py`). Qui se ne leggono cinque dei nove: quelli che
la pagina Recovery disegna. Gli altri quattro (stress, spo2, respiration,
training_status) restano su disco e non vengono nemmeno aperti: `sleep/` da
solo pesa piu' di tutti gli altri messi insieme, perche' porta il sonno minuto
per minuto, e aprire quello che non serve costa e basta.

Niente SQLite, al contrario delle attivita': un JSON al giorno per qualche
centinaio di giorni si legge in fretta, e il parsing FIT che giustifica la
cache delle attivita' qui non c'e'. La cache di Streamlit sta in `data.py`,
come per `load_activities()`.

I JSON di Garmin cambiano forma, e un giorno senza orologio al polso ha `null`
al posto dei dizionari: succede davvero (dal 2026-09-01 al 2026-09-08 `sleep`
e `stats` hanno i campi a `null`, e dal 4 all'8 `hrvSummary` e' `null` tutto
intero). Per questo ogni campo passa da `_dig()`, che su qualunque sorpresa
torna `None`: un campo che manca diventa `NaN`, mai un'eccezione e mai uno
zero. Uno zero direbbe "battito a riposo zero", che e' falso; `NaN` dice "non
lo sappiamo", ed e' il buco che i grafici devono mostrare.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from training.garmin.config import DATA_DIR

# Gli endpoint che servono a questa pagina, sui nove che `export_daily_health`
# scarica. L'ordine non conta: e' solo l'insieme dei file da aprire.
_USED_ENDPOINTS = ("training_readiness", "hrv", "resting_heart_rate", "sleep", "stats")

# Il punteggio di readiness da tenere, fra i piu' di uno che Garmin registra in
# un giorno: quello al risveglio. E' il numero che dice come si parte la
# mattina, ed e' uno solo per giorno. Gli altri arrivano dopo un allenamento
# (`AFTER_POST_EXERCISE_RESET`) o da un aggiornamento in corsa
# (`UPDATE_REALTIME_VARIABLES`), e dicono un'altra cosa.
_WAKEUP_CONTEXT = "AFTER_WAKEUP_RESET"

# Le colonne del DataFrame, nell'ordine in cui la pagina le usa.
COLUMNS = [
    "readiness",
    "body_battery_low",
    "body_battery_high",
    "hrv_last_night",
    "hrv_weekly_avg",
    "hrv_status",
    "resting_hr",
    "sleep_hours",
    "sleep_score",
]


def _dig(obj: Any, *keys: str) -> Any:
    """Il valore annidato sotto `keys`, o None appena qualcosa non torna.

    Serve perche' i JSON di Garmin non garantiscono niente: la chiave puo'
    mancare, il dizionario intermedio puo' essere `null`, e in mezzo puo'
    esserci una lista dove ci si aspetta un dizionario. Tutti questi casi
    valgono "non lo sappiamo", cioe' None."""
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _number(value: Any) -> float | None:
    """Il valore come numero, o None se non lo e'.

    I `bool` sono `int` in Python ma non sono misure: se un campo che ci
    aspettiamo numerico arriva booleano, e' cambiata la forma del JSON e il
    valore non va usato."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _read_json(path: Path) -> Any:
    """Il contenuto del file, o None se manca o non e' JSON valido.

    Un file troncato (scaricamento interrotto con Ctrl+C, che il backfill
    permette) non deve far cadere la pagina intera."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _readiness_score(payload: Any) -> float | None:
    """Il punteggio di readiness del risveglio, fra le misure del giorno.

    Se il risveglio non c'e', si prende la prima della giornata: "prima" per
    ora dell'orologio, non per posizione nella lista. La lista che arriva da
    Garmin non e' ordinata nel tempo (il 21 settembre ha prima quella delle
    17:54 e poi quella delle 06:04), quindi prendere `[0]` darebbe l'ultima."""
    if not isinstance(payload, list):
        return None
    entries = [e for e in payload if isinstance(e, dict) and _number(e.get("score")) is not None]
    if not entries:
        return None

    wakeup = [e for e in entries if e.get("inputContext") == _WAKEUP_CONTEXT]
    if wakeup:
        return _number(wakeup[0].get("score"))

    def _when(entry: dict) -> datetime:
        stamp = entry.get("timestamp")
        if isinstance(stamp, str):
            try:
                return datetime.fromisoformat(stamp)
            except ValueError:
                pass
        return datetime.max

    return _number(min(entries, key=_when).get("score"))


def _resting_hr(payload: Any) -> float | None:
    """La frequenza a riposo, in fondo a `allMetrics.metricsMap`.

    La lista ha una voce per giorno chiesto: qui il file e' quello di un
    giorno solo, quindi la prima e' quella giusta."""
    metrics = _dig(payload, "allMetrics", "metricsMap", "WELLNESS_RESTING_HEART_RATE")
    if not isinstance(metrics, list) or not metrics:
        return None
    return _number(_dig(metrics[0], "value"))


def _day_row(health_dir: Path, day: str) -> dict[str, Any]:
    """Una riga: tutte le grandezze di un giorno, lette dai cinque file."""
    payloads = {
        name: _read_json(health_dir / name / f"{day}.json") for name in _USED_ENDPOINTS
    }

    sleep_seconds = _number(_dig(payloads["sleep"], "dailySleepDTO", "sleepTimeSeconds"))

    return {
        "readiness": _readiness_score(payloads["training_readiness"]),
        "body_battery_low": _number(_dig(payloads["stats"], "bodyBatteryLowestValue")),
        "body_battery_high": _number(_dig(payloads["stats"], "bodyBatteryHighestValue")),
        "hrv_last_night": _number(_dig(payloads["hrv"], "hrvSummary", "lastNightAvg")),
        "hrv_weekly_avg": _number(_dig(payloads["hrv"], "hrvSummary", "weeklyAvg")),
        "hrv_status": _dig(payloads["hrv"], "hrvSummary", "status"),
        "resting_hr": _resting_hr(payloads["resting_heart_rate"]),
        # In ore, non in secondi: e' l'unita' con cui si legge il sonno, e la
        # pagina non deve dividere per 3.600 ogni volta che lo tocca.
        "sleep_hours": sleep_seconds / 3600 if sleep_seconds is not None else None,
        "sleep_score": _number(
            _dig(payloads["sleep"], "dailySleepDTO", "sleepScores", "overall", "value")
        ),
    }


def available_days(data_dir: Path = DATA_DIR) -> list[date]:
    """I giorni per cui c'e' almeno un file, in ordine.

    Si guarda l'unione dei cinque endpoint e non uno solo: un giorno in cui
    manca il sonno ma c'e' la readiness e' comunque un giorno da mostrare."""
    health_dir = Path(data_dir) / "health"
    days: set[date] = set()
    for name in _USED_ENDPOINTS:
        for path in (health_dir / name).glob("*.json"):
            try:
                days.add(date.fromisoformat(path.stem))
            except ValueError:
                # Un file che non si chiama come una data non e' un giorno.
                continue
    return sorted(days)


def load_health(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Le metriche di salute, una riga per giorno e una colonna per grandezza.

    L'indice e' `day` (date), continuo dal primo all'ultimo giorno trovato: i
    giorni senza file ci sono comunque, con tutto a `NaN`, cosi' l'asse del
    tempo non si accorcia sui buchi e una linea che salta un giorno si vede.

    DataFrame vuoto (con le colonne giuste) se non c'e' niente su disco."""
    data_dir = Path(data_dir)
    days = available_days(data_dir)
    if not days:
        return pd.DataFrame(columns=COLUMNS, index=pd.DatetimeIndex([], name="day"))

    health_dir = data_dir / "health"
    rows = [_day_row(health_dir, day.isoformat()) for day in days]

    frame = pd.DataFrame(rows, columns=COLUMNS, index=pd.DatetimeIndex(days, name="day"))
    # Il calendario completo fra il primo e l'ultimo giorno: `reindex` mette
    # NaN dove il giorno non c'era.
    full_range = pd.date_range(days[0], days[-1], freq="D", name="day")
    return frame.reindex(full_range)
