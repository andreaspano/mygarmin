"""I fatti di una settimana (lunedi'-domenica) per il report settimanale.

Lo script prepara i numeri, l'agente `.claude/agents/weekly-report.md` scrive
il testo: i conti non li fa il modello. Legge solo dati locali
(`activities.db`, aggiornato dai FIT e dai JSON gia' scaricati): nessuna
chiamata a Garmin. Per avere la settimana aggiornata si lancia prima
`make update_activity`.

Contratto: una media su zero giorni e' `None` (`null` nel JSON), mai `0`; e
ogni media dice su quanti giorni e' fatta.
"""

import argparse
import contextlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from training.garmin.config import DATA_DIR
from training.interface.db import list_activities
from training.interface.health_db import load_health_db

# Le misure di recupero di ogni mattina, in `days`. L'HRV e' sempre quella
# della notte (`hrv_last_night`): media settimanale e stato Garmin li porta
# avanti anche nei giorni senza orologio, e farebbero sembrare misurate notti
# che non lo sono.
RECOVERY_METRICS = (
    "readiness",
    "resting_hr",
    "hrv_last_night",
    "sleep_hours",
    "sleep_score",
    "stress_avg",
    "body_battery_high",
    "body_battery_low",
)

# Le metriche di cui si conta la copertura: quelle che il report commenta.
# Readiness e carico Garmin li calcola anche senza orologio al polso, le altre
# no: per questo la copertura e' per metrica e non per giorno. Niente SpO2,
# che l'orologio non misura.
COVERAGE_METRICS = (
    "readiness",
    "sleep_hours",
    "sleep_score",
    "hrv_last_night",
    "resting_hr",
    "stress_avg",
    "load_acute",
)

# Le medie di recupero confrontate nelle quattro settimane.
TREND_METRICS = ("readiness", "resting_hr", "hrv_last_night", "sleep_hours", "sleep_score", "stress_avg")

# Il carico di Garmin, a fine giornata.
LOAD_METRICS = (
    "load_acute",
    "load_chronic",
    "acwr",
    "acwr_status",
    "training_status",
    "training_status_phrase",
    "load_aerobic_low",
    "load_aerobic_high",
    "load_anaerobic",
    "load_balance_phrase",
)

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# Per i messaggi d'errore, che sono in italiano.
GIORNI = ("lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato", "domenica")


def last_closed_monday(today: date) -> date:
    """Il lunedi' della settimana prima di quella di oggi."""
    return today - timedelta(days=today.weekday() + 7)


def _value(value: Any, digits: int = 1) -> Any:
    """Il valore pronto per il JSON: NaN e None diventano None, i numeri
    arrotondati, il resto (testo) com'e'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        rounded = round(float(value), digits)
        return int(rounded) if digits == 0 else rounded
    return value


def _mean(series: pd.Series, digits: int = 1) -> dict[str, Any]:
    """Media e numero di giorni su cui e' fatta; `None` su zero giorni."""
    values = series.dropna()
    return {"mean": _value(values.mean(), digits) if len(values) else None, "days": int(len(values))}


def _week_activities(activities: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Le attivita' della settimana, in ordine di inizio. Un'attivita' sta nel
    giorno in cui comincia, anche se finisce dopo mezzanotte."""
    if activities.empty:
        return activities
    day = activities["start_time"].dt.date
    week = activities[(day >= start) & (day <= end)].copy()
    return week.sort_values("start_time")


def _week_health(health: pd.DataFrame, start: date) -> pd.DataFrame:
    """I 7 giorni di salute della settimana, uno per riga: NaN dove non c'e'
    il dato, anche fuori dall'intervallo che il database copre."""
    days = pd.date_range(start, periods=7, freq="D", name="day")
    return health.reindex(days)


def _activity_row(row: pd.Series) -> dict[str, Any]:
    start = row["start_time"]
    return {
        "date": start.date().isoformat(),
        "weekday": WEEKDAYS[start.weekday()],
        "start_time": start.strftime("%H:%M"),
        "sport": row["sport"],
        "sub_sport": row["sub_sport"] if row["sub_sport"] not in (None, "", "generic") else None,
        "name": row["activity_name"],
        "distance_km": _value(row["total_distance_km"], 2),
        "duration_min": _value(row["total_time_min"], 0),
        "ascent_m": _value(row["total_ascent_m"], 0),
        "avg_hr": _value(row["avg_heart_rate"], 0),
        "max_hr": _value(row["max_heart_rate"], 0),
    }


def _training(week: pd.DataFrame, start: date, last_day: date, today: date) -> dict[str, Any]:
    """Totali della settimana. Distanza e dislivello solo per sport: sommati
    fra sport diversi non vogliono dire niente. I giorni di riposo contano
    solo fino all'ultimo giorno passato, e oggi senza attivita' non e' ancora
    un riposo: la giornata non e' finita."""
    by_sport = {}
    for sport, group in week.groupby("sport", sort=False):
        by_sport[sport] = {
            "sessions": int(len(group)),
            "time_min": _value(group["total_time_min"].sum(), 0),
            "distance_km": _value(group["total_distance_km"].sum(min_count=1), 1),
            "ascent_m": _value(group["total_ascent_m"].sum(min_count=1), 0),
        }
    active = set(week["start_time"].dt.date) if not week.empty else set()
    elapsed = [start + timedelta(days=i) for i in range((last_day - start).days + 1)]
    rest = [WEEKDAYS[d.weekday()] for d in elapsed if d not in active and d < today]
    return {
        "sessions": int(len(week)),
        "time_min": _value(week["total_time_min"].sum(), 0) if not week.empty else 0,
        "by_sport": by_sport,
        "active_days": len(active),
        "rest_days": rest,
    }


def _days(week: pd.DataFrame, health: pd.DataFrame, start: date, last_day: date) -> list[dict[str, Any]]:
    """Una riga per giorno: le attivita' (o nessuna) e le misure di recupero
    di quella mattina. Il sonno con la data di un giorno e' la notte che porta
    a quel giorno: quello di lunedi' e' la notte fra domenica e lunedi'."""
    rows = []
    for i in range(7):
        day = start + timedelta(days=i)
        today_acts = week[week["start_time"].dt.date == day] if not week.empty else week
        morning = health.loc[pd.Timestamp(day)]
        rows.append(
            {
                "date": day.isoformat(),
                "weekday": WEEKDAYS[i],
                "future": day > last_day,
                "activities": [
                    {
                        "sport": a["sport"],
                        "name": a["activity_name"],
                        "distance_km": _value(a["total_distance_km"], 2),
                        "duration_min": _value(a["total_time_min"], 0),
                    }
                    for _, a in today_acts.iterrows()
                ],
                "recovery": {m: _value(morning[m], 1) for m in RECOVERY_METRICS},
                "sleep_night": f"the night going into {WEEKDAYS[i]}",
            }
        )
    return rows


def _load(health: pd.DataFrame, last_day: date) -> dict[str, Any] | None:
    """Il carico dell'ultimo giorno della settimana che lo ha (Garmin lo da' a
    fine giornata), e quale giorno e'. `None` se non c'e' in nessun giorno."""
    known = health.loc[: pd.Timestamp(last_day), "load_acute"].dropna()
    if known.empty:
        return None
    as_of = known.index[-1]
    row = health.loc[as_of]
    return {"as_of": as_of.date().isoformat(), **{m: _value(row[m], 2) for m in LOAD_METRICS}}


def _vo2max(health: pd.DataFrame, start: date, end: date) -> list[dict[str, Any]]:
    """Le misure di VO2max fatte nella settimana: quelle con `vo2max_date`
    dentro la settimana, una per data (Garmin ripete l'ultima nei giorni
    dopo)."""
    rows = health[["vo2max", "vo2max_date"]].dropna()
    seen = {}
    for _, r in rows.iterrows():
        measured = date.fromisoformat(str(r["vo2max_date"])[:10])
        if start <= measured <= end:
            seen[measured] = float(r["vo2max"])
    return [{"date": d.isoformat(), "value": _value(v, 1)} for d, v in sorted(seen.items())]


def _week_summary(
    activities: pd.DataFrame, health: pd.DataFrame, start: date, last_day: date, today: date
) -> dict[str, Any]:
    """I totali e le medie di una settimana, per il confronto fra settimane."""
    end = start + timedelta(days=6)
    week = _week_activities(activities, start, end)
    week_health = _week_health(health, start)
    training = _training(week, start, last_day, today)
    load = _load(week_health, last_day)
    vo2max = _vo2max(health, start, end)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sessions": training["sessions"],
        "time_min": training["time_min"],
        "by_sport": training["by_sport"],
        "rest_days": len(training["rest_days"]),
        "health_days": int(week_health["sleep_hours"].notna().sum()),
        "recovery": {m: _mean(week_health[m], 1) for m in TREND_METRICS},
        "load_acute": load["load_acute"] if load else None,
        "load_as_of": load["as_of"] if load else None,
        "vo2max": vo2max[-1]["value"] if vo2max else None,
    }


def build_weekly_data(monday: date, data_dir: Path = DATA_DIR, today: date | None = None) -> dict[str, Any]:
    """I fatti della settimana che comincia `monday`, come dizionario pronto
    per il JSON. Una settimana non ancora finita si puo' chiedere: `partial`
    e `last_day` dicono fin dove arriva."""
    if monday.weekday() != 0:
        raise ValueError(f"{monday} non e' un lunedi'")
    today = today or date.today()
    if monday > today:
        raise ValueError(f"la settimana del {monday} non e' ancora cominciata")

    end = monday + timedelta(days=6)
    partial = end >= today
    last_day = min(end, today)

    activities = list_activities(data_dir)
    health = load_health_db(data_dir)

    week = _week_activities(activities, monday, end)
    week_health = _week_health(health, monday)

    return {
        "week": {
            "start": monday.isoformat(),
            "end": end.isoformat(),
            "partial": partial,
            "last_day": last_day.isoformat(),
        },
        "health_days": int(week_health["sleep_hours"].notna().sum()),
        "activities": [_activity_row(r) for _, r in week.iterrows()],
        "days": _days(week, week_health, monday, last_day),
        "training": _training(week, monday, last_day, today),
        "load": _load(week_health, last_day),
        "vo2max": _vo2max(health, monday, end),
        "coverage": {m: int(week_health[m].notna().sum()) for m in COVERAGE_METRICS},
        # Dalla piu' vecchia a questa; le tre prima sono sempre chiuse.
        "four_weeks": [
            _week_summary(activities, health, start, min(start + timedelta(days=6), last_day), today)
            for start in (monday - timedelta(weeks=k) for k in (3, 2, 1, 0))
        ],
    }


def _monday(text: str) -> date:
    try:
        day = date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data non valida: {text!r} (serve YYYY-MM-DD)")
    if day.weekday() != 0:
        raise argparse.ArgumentTypeError(f"{day} e' {GIORNI[day.weekday()]}, non lunedi'")
    return day


def main() -> None:
    """Stampa il JSON della settimana su stdout; i messaggi delle funzioni
    chiamate vanno su stderr, per lasciare stdout pulito a chi legge il
    JSON."""
    parser = argparse.ArgumentParser(description="I fatti di una settimana, in JSON, per il report settimanale.")
    parser.add_argument(
        "--week",
        type=_monday,
        help="il lunedi' della settimana (YYYY-MM-DD); di default l'ultima settimana chiusa",
    )
    args = parser.parse_args()
    monday = args.week or last_closed_monday(date.today())
    try:
        with contextlib.redirect_stdout(sys.stderr):
            data = build_weekly_data(monday)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
