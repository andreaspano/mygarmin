"""Lettura delle metriche giornaliere di salute dai JSON di Garmin.

Un file per giorno e per endpoint, in `DATA_DIR/health/<endpoint>/<data>.json`
(li scrive `garmin/health.py`). Qui si aprono tutti e nove, ma se ne tengono
solo i valori giornalieri: le serie minuto per minuto (stress, respiro, sonno)
si leggono e si buttano, e restano nei JSON per chi le vuole intere
(`garmin/fitness_status.py` legge i file grezzi per conto suo).

Le righe finiscono in SQLite, nella tabella `health_daily` dentro
`activities.db` (vedi `health_db.py`), ma e' solo una cache derivata: la fonte
restano i JSON, e la tabella si ricostruisce sempre da loro, rileggendo un
giorno quando uno dei suoi file cambia. Qui sta il parsing, la' la cache; la
cache di Streamlit sta in `data.py`, come per `load_activities()`.

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
from training.garmin.health import DAILY_ENDPOINTS

# Gli endpoint da aprire: tutti quelli che `export_daily_health` scarica.
# L'ordine non conta: e' solo l'insieme dei file da leggere per un giorno.
_USED_ENDPOINTS = tuple(DAILY_ENDPOINTS)

# Il punteggio di readiness da tenere, fra i piu' di uno che Garmin registra in
# un giorno: quello al risveglio. E' il numero che dice come si parte la
# mattina, ed e' uno solo per giorno. Gli altri arrivano dopo un allenamento
# (`AFTER_POST_EXERCISE_RESET`) o da un aggiornamento in corsa
# (`UPDATE_REALTIME_VARIABLES`), e dicono un'altra cosa.
_WAKEUP_CONTEXT = "AFTER_WAKEUP_RESET"

# Le colonne del DataFrame, nello stesso ordine della tabella `health_daily`.
# Le prime nove sono quelle della pagina Recovery; le altre servono a chi mette
# la salute accanto alle attivita' (VO2max, carico, training status).
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
    "stress_avg",
    "stress_max",
    "resp_sleep_avg",
    "resp_waking_avg",
    "resp_low",
    "resp_high",
    "spo2_avg",
    "spo2_low",
    "spo2_sleep_avg",
    "vo2max",
    "vo2max_date",
    "training_status",
    "training_status_phrase",
    "load_acute",
    "load_chronic",
    "acwr",
    "acwr_status",
    "load_aerobic_low",
    "load_aerobic_high",
    "load_anaerobic",
    "load_balance_phrase",
]

# Le colonne di testo; tutte le altre sono numeri (`REAL` in SQLite, `float`
# nel DataFrame).
TEXT_COLUMNS = (
    "hrv_status",
    "vo2max_date",
    "training_status_phrase",
    "acwr_status",
    "load_balance_phrase",
)


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


def _text(value: Any) -> str | None:
    """Il valore come stringa, o None se non lo e'.

    Lo stesso contratto di `_number()` per i campi di testo (stati e frasi di
    Garmin): se al posto della stringa arriva un dizionario o una lista, la
    forma del JSON e' cambiata, e SQLite non saprebbe nemmeno salvarlo."""
    return value if isinstance(value, str) else None


def _stress(value: Any) -> float | None:
    """Un livello di stress, o None se Garmin dice che non c'e'.

    Lo stress va da 0 a 100; nei giorni senza orologio al polso Garmin scrive
    `avgStressLevel: -1` (dal 2026-09-01 al 2026-09-07), che non e' una misura
    ma il suo modo di dire "non lo so". Un negativo diventa None."""
    number = _number(value)
    return number if number is not None and number >= 0 else None


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


def _primary_entry(device_map: Any) -> dict | None:
    """La voce dell'orologio principale, in una mappa indicizzata per ID.

    Training status e load balance arrivano come `{"<id orologio>": {...}}`:
    con un solo orologio la voce e' una, con due sarebbero due. Si prende
    quella con `primaryTrainingDevice: true`, non la prima: l'ordine delle
    chiavi non dice niente su quale orologio conta."""
    if not isinstance(device_map, dict):
        return None
    for entry in device_map.values():
        if isinstance(entry, dict) and entry.get("primaryTrainingDevice") is True:
            return entry
    return None


def _vo2max(payload: Any) -> tuple[float | None, str | None]:
    """Il VO2max piu' recente e la data in cui e' stato misurato.

    E' "il piu' recente", non quello del giorno del file: il file del
    2026-09-17 porta ancora il valore del 09-16, e il 40.2 del 09-14 compare
    solo nel file del 09-15. Per questo si tengono valore e data cosi' come
    sono, e il VO2max del giorno D sono le righe con `vo2max_date = D`. Senza
    valore la data non dice niente, e resta None anche lei."""
    generic = _dig(payload, "mostRecentVO2Max", "generic")
    value = _number(_dig(generic, "vo2MaxPreciseValue"))
    if value is None:
        return None, None
    return value, _text(_dig(generic, "calendarDate"))


def _training_status(payload: Any, day: str) -> dict[str, Any]:
    """Training status e carico acuto/cronico dell'orologio principale.

    Sono del giorno (il loro `calendarDate` coincide sempre col nome del
    file), ma il controllo resta: se un giorno Garmin rimanda la voce di un
    giorno prima, quella non e' la misura di oggi, e tutto resta None."""
    entry = _primary_entry(
        _dig(payload, "mostRecentTrainingStatus", "latestTrainingStatusData")
    )
    if entry is None or entry.get("calendarDate") != day:
        entry = None
    load = _dig(entry, "acuteTrainingLoadDTO")
    return {
        # Un intero grezzo (7 = PRODUCTIVE): la traduzione in parole la fa chi
        # lo mostra, perche' i codici sono scelte di Garmin e possono cambiare.
        "training_status": _number(_dig(entry, "trainingStatus")),
        "training_status_phrase": _text(_dig(entry, "trainingStatusFeedbackPhrase")),
        "load_acute": _number(_dig(load, "dailyTrainingLoadAcute")),
        "load_chronic": _number(_dig(load, "dailyTrainingLoadChronic")),
        "acwr": _number(_dig(load, "dailyAcuteChronicWorkloadRatio")),
        "acwr_status": _text(_dig(load, "acwrStatus")),
    }


def _load_balance(payload: Any, day: str) -> dict[str, Any]:
    """Il carico mensile per zona (aerobico basso, alto, anaerobico).

    Stesso controllo sulla data di `_training_status()`."""
    entry = _primary_entry(
        _dig(payload, "mostRecentTrainingLoadBalance", "metricsTrainingLoadBalanceDTOMap")
    )
    if entry is None or entry.get("calendarDate") != day:
        entry = None
    return {
        "load_aerobic_low": _number(_dig(entry, "monthlyLoadAerobicLow")),
        "load_aerobic_high": _number(_dig(entry, "monthlyLoadAerobicHigh")),
        "load_anaerobic": _number(_dig(entry, "monthlyLoadAnaerobic")),
        "load_balance_phrase": _text(_dig(entry, "trainingBalanceFeedbackPhrase")),
    }


def _day_paths(health_dir: Path, day: str) -> dict[str, Path]:
    """I nove file di un giorno, per endpoint (non e' detto che esistano)."""
    return {name: health_dir / name / f"{day}.json" for name in _USED_ENDPOINTS}


def _day_row(health_dir: Path, day: str) -> dict[str, Any]:
    """Una riga: tutte le grandezze di un giorno, lette dai nove file."""
    payloads = {name: _read_json(path) for name, path in _day_paths(health_dir, day).items()}

    sleep_seconds = _number(_dig(payloads["sleep"], "dailySleepDTO", "sleepTimeSeconds"))
    vo2max, vo2max_date = _vo2max(payloads["training_status"])

    return {
        "readiness": _readiness_score(payloads["training_readiness"]),
        "body_battery_low": _number(_dig(payloads["stats"], "bodyBatteryLowestValue")),
        "body_battery_high": _number(_dig(payloads["stats"], "bodyBatteryHighestValue")),
        "hrv_last_night": _number(_dig(payloads["hrv"], "hrvSummary", "lastNightAvg")),
        "hrv_weekly_avg": _number(_dig(payloads["hrv"], "hrvSummary", "weeklyAvg")),
        "hrv_status": _text(_dig(payloads["hrv"], "hrvSummary", "status")),
        "resting_hr": _resting_hr(payloads["resting_heart_rate"]),
        # In ore, non in secondi: e' l'unita' con cui si legge il sonno, e la
        # pagina non deve dividere per 3.600 ogni volta che lo tocca.
        "sleep_hours": sleep_seconds / 3600 if sleep_seconds is not None else None,
        "sleep_score": _number(
            _dig(payloads["sleep"], "dailySleepDTO", "sleepScores", "overall", "value")
        ),
        "stress_avg": _stress(_dig(payloads["stress"], "avgStressLevel")),
        "stress_max": _stress(_dig(payloads["stress"], "maxStressLevel")),
        "resp_sleep_avg": _number(_dig(payloads["respiration"], "avgSleepRespirationValue")),
        "resp_waking_avg": _number(_dig(payloads["respiration"], "avgWakingRespirationValue")),
        "resp_low": _number(_dig(payloads["respiration"], "lowestRespirationValue")),
        "resp_high": _number(_dig(payloads["respiration"], "highestRespirationValue")),
        # L'orologio di oggi non misura la saturazione: queste tre restano
        # None, e si riempiono da sole se un giorno la si attiva.
        "spo2_avg": _number(_dig(payloads["spo2"], "averageSpO2")),
        "spo2_low": _number(_dig(payloads["spo2"], "lowestSpO2")),
        "spo2_sleep_avg": _number(_dig(payloads["spo2"], "avgSleepSpO2")),
        "vo2max": vo2max,
        "vo2max_date": vo2max_date,
        **_training_status(payloads["training_status"], day),
        **_load_balance(payloads["training_status"], day),
    }


def available_days(data_dir: Path = DATA_DIR) -> list[date]:
    """I giorni per cui c'e' almeno un file, in ordine.

    Si guarda l'unione dei nove endpoint e non uno solo: un giorno in cui
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

    DataFrame vuoto (con le colonne giuste) se non c'e' niente su disco.

    Passa dalla tabella `health_daily` (vedi `health_db.load_health_db`), che
    rilegge dai JSON solo i giorni nuovi o cambiati."""
    # Import qui e non in cima: `health_db` importa questo modulo per il
    # parsing, e un import in cima ai due file farebbe un giro circolare.
    from training.interface.health_db import load_health_db

    return load_health_db(data_dir)
