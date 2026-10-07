"""I fatti di un giorno per il report giornaliero (todo 31).

Lo script prepara i numeri, l'agente `.claude/agents/fitness-status.md` scrive
il testo: i conti non li fa il modello, come per il report settimanale
(`weekly_data.py`). Legge solo dati locali (`activities.db` e i JSON di salute
gia' scaricati): nessuna chiamata a Garmin. Per avere il giorno aggiornato si
lancia prima `make update_activity`.

Il report del giorno D parla della mattina di D (readiness, notte appena
passata), della seduta del giorno prima (o del riposo), delle attivita' di D
gia' fatte, e serve a consigliare la seduta di D.

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
from training.interface.db import list_activities, load_activity_records
from training.interface.health import _day_paths, _dig, _read_json
from training.interface.health_db import load_health_db
from training.interface.run_chart import EFFECTS, effects, has_effects
from training.interface.weekly_data import WEEKDAYS, _mean, _value

# Le misure della mattina, con la riga di `health_daily` da cui si leggono:
# 0 e' il giorno D, -1 il giorno prima. Il sonno con la data di D e' la notte
# che porta a D. Stress e minimo della body battery sono quelli del giorno
# prima: la mattina di D quelli di D sono appena cominciati. Il massimo della
# body battery di D e' invece gia' quello del risveglio.
MORNING_METRICS: dict[str, tuple[str, int]] = {
    "readiness": ("readiness", 0),
    "resting_hr": ("resting_hr", 0),
    "hrv_last_night": ("hrv_last_night", 0),
    "hrv_weekly_avg": ("hrv_weekly_avg", 0),
    "resp_sleep": ("resp_sleep_avg", 0),
    "sleep_hours": ("sleep_hours", 0),
    "sleep_score": ("sleep_score", 0),
    "stress_avg_yesterday": ("stress_avg", -1),
    "body_battery_morning": ("body_battery_high", 0),
    "body_battery_low_yesterday": ("body_battery_low", -1),
    "spo2_avg": ("spo2_avg", 0),
}

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

# Le soglie degli allarmi della sezione Health. Sono qui e non nel testo
# dell'agente: il modello racconta gli allarmi, non li decide.
RHR_RISE_BPM = 3  # FC a riposo sopra la media di 28 giorni...
RHR_RISE_DAYS = 2  # ...per tanti giorni di fila (D compreso)
RESP_RISE = 1.0  # atti/min sopra la media di 28 giorni
SHORT_NIGHT_HOURS = 7
SHORT_NIGHTS_ALERT = 3  # notti corte negli ultimi 7 giorni
# Una seduta e' impegnativa con almeno 10 minuti sopra il tetto di Z3 (alto
# aerobico piu' anaerobico, vedi `run_chart.effects`).
HARD_SESSION_MIN = 10
VO2MAX_CHANGE = 0.5
RECENT_DAYS = 14
BASELINE_SHORT = 7
BASELINE_LONG = 28


def _health_row(health: pd.DataFrame, day: date) -> pd.Series:
    """La riga di salute di `day`, tutta NaN se il giorno non c'e'."""
    return health.reindex([pd.Timestamp(day)]).iloc[0]


def _window(health: pd.DataFrame, column: str, end: date, days: int) -> pd.Series:
    """I `days` giorni che finiscono il giorno prima di `end` (escluso)."""
    index = pd.date_range(end - timedelta(days=days), end - timedelta(days=1), freq="D")
    return health.reindex(index)[column]


def _morning(health: pd.DataFrame, day: date) -> dict[str, Any]:
    """Ogni misura: il valore, le medie a 7 e 28 giorni (con quanti giorni) e
    la differenza dalla media a 28. Le medie sono calcolate rispetto al giorno
    da cui si legge la misura."""
    result = {}
    for name, (column, offset) in MORNING_METRICS.items():
        source = day + timedelta(days=offset)
        value = _value(_health_row(health, source)[column], 1)
        short = _mean(_window(health, column, source, BASELINE_SHORT), 1)
        long = _mean(_window(health, column, source, BASELINE_LONG), 1)
        delta = (
            _value(value - long["mean"], 1)
            if value is not None and long["mean"] is not None
            else None
        )
        result[name] = {
            "value": value,
            "date": source.isoformat(),
            "avg_7d": short,
            "avg_28d": long,
            "delta_vs_28d": delta,
        }
    result["hrv_status"] = _value(_health_row(health, day)["hrv_status"])
    result["hrv_baseline"] = _hrv_baseline(day)
    return result


def _hrv_baseline(day: date, data_dir: Path = DATA_DIR) -> dict[str, Any] | None:
    """L'intervallo "balanced" dell'HRV secondo Garmin, dal JSON di salute di
    quel giorno: `health_daily` non lo tiene. `None` se il file non c'e'."""
    path = _day_paths(Path(data_dir) / "health", day.isoformat())["hrv"]
    baseline = _dig(_read_json(path), "hrvSummary", "baseline")
    if not isinstance(baseline, dict) or baseline.get("balancedLow") is None:
        return None
    return {"low": baseline.get("balancedLow"), "high": baseline.get("balancedUpper")}


def _sleep_last_7(health: pd.DataFrame, day: date) -> dict[str, Any]:
    """Le ore di sonno delle ultime 7 notti (quella che porta a D compresa)."""
    nights = health.reindex(pd.date_range(day - timedelta(days=6), day, freq="D"))["sleep_hours"]
    hours = {d.date().isoformat(): _value(v, 1) for d, v in nights.items()}
    known = nights.dropna()
    return {
        "hours": hours,
        "short_nights": int((known < SHORT_NIGHT_HOURS).sum()),
        "nights_measured": int(len(known)),
    }


def _alerts(health: pd.DataFrame, day: date, morning: dict[str, Any], sleep: dict[str, Any]) -> list[dict]:
    """Gli allarmi accesi, ognuno con i suoi numeri. Lista vuota: niente da
    segnalare."""
    alerts = []

    rhr_days = []
    for back in range(RHR_RISE_DAYS):
        source = day - timedelta(days=back)
        value = _health_row(health, source)["resting_hr"]
        baseline = _mean(_window(health, "resting_hr", source, BASELINE_LONG), 1)["mean"]
        rhr_days.append((source, value, baseline))
    if all(pd.notna(v) and b is not None and v >= b + RHR_RISE_BPM for _, v, b in rhr_days):
        alerts.append(
            {
                "kind": "resting_hr_up",
                "detail": f"resting HR {RHR_RISE_BPM}+ bpm above its 28-day average "
                f"for {RHR_RISE_DAYS} days in a row",
                "days": [
                    {"date": d.isoformat(), "value": _value(v, 0), "avg_28d": b} for d, v, b in rhr_days
                ],
            }
        )

    resp = morning["resp_sleep"]
    if resp["delta_vs_28d"] is not None and resp["delta_vs_28d"] >= RESP_RISE:
        alerts.append(
            {
                "kind": "sleep_breathing_up",
                "detail": f"breathing rate during sleep {RESP_RISE:g}+ breaths/min above its 28-day average",
                "value": resp["value"],
                "avg_28d": resp["avg_28d"]["mean"],
            }
        )

    weekly = morning["hrv_weekly_avg"]["value"]
    baseline = morning["hrv_baseline"]
    if weekly is not None and baseline and weekly < baseline["low"]:
        alerts.append(
            {
                "kind": "hrv_below_baseline",
                "detail": "HRV weekly average below the bottom of Garmin's balanced range",
                "value": weekly,
                "baseline_low": baseline["low"],
            }
        )

    if sleep["short_nights"] >= SHORT_NIGHTS_ALERT:
        alerts.append(
            {
                "kind": "short_sleep",
                "detail": f"{sleep['short_nights']} nights under {SHORT_NIGHT_HOURS} h in the last 7",
                "short_nights": sleep["short_nights"],
            }
        )
    return alerts


def _load_on(health: pd.DataFrame, day: date) -> dict[str, Any] | None:
    """Il carico dell'ultimo giorno fino a `day` che lo ha (Garmin lo da' a
    fine giornata, quindi la mattina spesso e' quello del giorno prima)."""
    known = health.loc[: pd.Timestamp(day), "load_acute"].dropna()
    if known.empty:
        return None
    as_of = known.index[-1]
    row = health.loc[as_of]
    return {"as_of": as_of.date().isoformat(), **{m: _value(row[m], 2) for m in LOAD_METRICS}}


def _vo2max_change(health: pd.DataFrame, day: date) -> dict[str, Any] | None:
    """Il VO2max di Garmin oggi e 28 giorni prima, solo se e' cambiato di
    almeno `VO2MAX_CHANGE`: spostamenti piu' piccoli sono rumore."""
    values = health.loc[: pd.Timestamp(day), "vo2max"].dropna()
    if values.empty:
        return None
    before = health.loc[: pd.Timestamp(day - timedelta(days=BASELINE_LONG)), "vo2max"].dropna()
    if before.empty:
        return None
    now, then = float(values.iloc[-1]), float(before.iloc[-1])
    if abs(now - then) < VO2MAX_CHANGE:
        return None
    return {"now": _value(now, 1), "days_ago_28": _value(then, 1), "change": _value(now - then, 1)}


def _zones(activity: pd.Series) -> tuple[list[int] | None, int | None]:
    bounds = json.loads(activity["hr_zone_bounds"]) if isinstance(activity["hr_zone_bounds"], str) else None
    threshold = int(activity["threshold_hr"]) if pd.notna(activity["threshold_hr"]) else None
    return bounds, threshold


def _effect_minutes(activity: pd.Series, data_dir: Path) -> dict[str, float] | None:
    """I minuti per effetto stimato (`run_chart.effects`), o `None` senza zone,
    soglia o battiti."""
    bounds, threshold = _zones(activity)
    if not has_effects(bounds, threshold):
        return None
    records = load_activity_records(int(activity["activity_id"]), data_dir)
    if records.empty or records["heart_rate"].isna().all():
        return None
    seconds = effects(records, bounds, threshold)
    return {name: _value(seconds[name] / 60, 1) for name in EFFECTS}


def _session(activity: pd.Series, data_dir: Path) -> dict[str, Any]:
    start = activity["start_time"]
    return {
        "date": start.date().isoformat(),
        "weekday": WEEKDAYS[start.weekday()],
        "start_time": start.strftime("%H:%M"),
        "sport": activity["sport"],
        "name": activity["activity_name"],
        "distance_km": _value(activity["total_distance_km"], 2),
        "duration_min": _value(activity["total_time_min"], 0),
        "ascent_m": _value(activity["total_ascent_m"], 0),
        "avg_hr": _value(activity["avg_heart_rate"], 0),
        "max_hr": _value(activity["max_heart_rate"], 0),
        "aerobic_te": _value(activity["aerobic_te"], 1),
        "anaerobic_te": _value(activity["anaerobic_te"], 1),
        "grade_adjusted_speed_kmh": _value(activity["equiv_speed_kmh"], 1),
        "effect_minutes": _effect_minutes(activity, data_dir),
    }


def _on(activities: pd.DataFrame, day: date) -> pd.DataFrame:
    return activities[activities["start_time"].dt.date == day].sort_values("start_time")


def _recent(activities: pd.DataFrame, day: date, data_dir: Path) -> dict[str, Any]:
    """Il contesto prima di D: da quanto non ci si allena, da quanto non si fa
    una seduta impegnativa, i riposi della settimana e le attivita' delle
    ultime due settimane in una riga ciascuna."""
    dates = activities["start_time"].dt.date
    before = activities[dates < day].sort_values("start_time")
    last = before.iloc[-1]["start_time"].date() if not before.empty else None

    last_hard = None
    window = before[before["start_time"].dt.date >= day - timedelta(days=BASELINE_LONG)]
    for _, activity in window.iloc[::-1].iterrows():
        minutes = _effect_minutes(activity, data_dir)
        if minutes and minutes[EFFECTS[1]] + minutes[EFFECTS[2]] >= HARD_SESSION_MIN:
            last_hard = activity["start_time"].date()
            break

    week = {day - timedelta(days=k) for k in range(1, 8)}
    active = set(dates[dates.isin(week)])
    listed = activities[(dates >= day - timedelta(days=RECENT_DAYS - 1)) & (dates <= day)].sort_values("start_time")
    return {
        "last_activity": last.isoformat() if last else None,
        "days_since_last_activity": (day - last).days if last else None,
        "last_hard_session": last_hard.isoformat() if last_hard else None,
        "days_since_last_hard_session": (day - last_hard).days if last_hard else None,
        "hard_session_rule": f"{HARD_SESSION_MIN}+ minutes above the top of Z3, "
        f"looked for in the last {BASELINE_LONG} days",
        "rest_days_last_7": len(week - active),
        "activities_last_14_days": [
            {
                "date": a["start_time"].date().isoformat(),
                "sport": a["sport"],
                "distance_km": _value(a["total_distance_km"], 1),
                "duration_min": _value(a["total_time_min"], 0),
                "aerobic_te": _value(a["aerobic_te"], 1),
                "anaerobic_te": _value(a["anaerobic_te"], 1),
            }
            for _, a in listed.iterrows()
        ],
    }


def build_daily_data(day: date, data_dir: Path = DATA_DIR) -> dict[str, Any]:
    """I fatti del giorno `day`, come dizionario pronto per il JSON."""
    activities = list_activities(data_dir)
    health = load_health_db(data_dir)

    morning = _morning(health, day)
    sleep = _sleep_last_7(health, day)
    load_now = _load_on(health, day)
    load_week_ago = _load_on(health, day - timedelta(days=7))
    health_known = health.index[health["sleep_hours"].notna() | health["resting_hr"].notna()]

    return {
        "day": day.isoformat(),
        "weekday": WEEKDAYS[day.weekday()],
        "health_data_up_to": health_known.max().date().isoformat() if len(health_known) else None,
        "morning": morning,
        "sleep_last_7": sleep,
        "alerts": _alerts(health, day, morning, sleep),
        "load": {
            "now": load_now,
            "week_ago": load_week_ago,
            "vo2max_change": _vo2max_change(health, day),
        },
        "sessions": {
            "yesterday": [_session(a, data_dir) for _, a in _on(activities, day - timedelta(days=1)).iterrows()],
            "today": [_session(a, data_dir) for _, a in _on(activities, day).iterrows()],
        },
        "recent": _recent(activities, day, data_dir),
        "missing": [name for name, item in morning.items() if isinstance(item, dict) and "value" in item and item["value"] is None],
    }


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data non valida: {text!r} (serve YYYY-MM-DD)")


def main() -> None:
    """Stampa il JSON del giorno su stdout; i messaggi delle funzioni chiamate
    vanno su stderr, per lasciare stdout pulito a chi legge il JSON."""
    parser = argparse.ArgumentParser(description="I fatti di un giorno, in JSON, per il report giornaliero.")
    parser.add_argument("--day", type=_day, help="il giorno (YYYY-MM-DD); di default oggi")
    args = parser.parse_args()
    day = args.day or date.today()
    if day > date.today():
        parser.error(f"il {day} non e' ancora arrivato")
    with contextlib.redirect_stdout(sys.stderr):
        data = build_daily_data(day)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
