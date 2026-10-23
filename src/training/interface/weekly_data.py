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

import numpy as np
import pandas as pd

from training.garmin.config import DATA_DIR
from training.interface.db import list_activities
from training.interface.health_db import load_health_db
from training.interface.sports import has_distance

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

# Le misure che la pagina Week mostra con la loro barra (todo 52), con
# l'etichetta a schermo, l'unita' e i decimali. Health e Recovery sono
# **medie** dei sette giorni: il corpo in quella settimana. Il carico e la
# forma no, sono stati di fine settimana, e stanno altrove.
WEEK_MEASURES: tuple[tuple[str, str, str, str, int], ...] = (
    ("health", "resting_hr", "Resting heart rate", "bpm", 0),
    ("health", "hrv_last_night", "HRV", "ms", 0),
    ("health", "resp_sleep_avg", "Breathing in sleep", "/min", 1),
    ("health", "stress_avg", "Stress", "", 0),
    ("recovery", "readiness", "Readiness", "", 0),
    ("recovery", "sleep_hours", "Sleep", "h", 1),
    ("recovery", "body_battery_high", "Body battery, wake-up", "", 0),
    ("recovery", "body_battery_low", "Body battery, low", "", 0),
)

# Le misure che vivono fra 0 e 100, come `MORNING_LIMITS` per il giorno: la
# fascia non deve promettere un valore che la misura non puo' avere.
WEEK_LIMITS: dict[str, tuple[float, float]] = {
    name: (0, 100)
    for name in ("readiness", "stress_avg", "body_battery_high", "body_battery_low")
}

# Quante settimane guarda indietro una fascia della Week, e quante ne
# servono perche' valga qualcosa (todo 52). Dodici settimane sono tre mesi:
# abbastanza da contenere un blocco di lavoro intero, abbastanza poche da
# seguire un cambio di passo. **Non sono i 28 giorni della Day**: attorno a
# una media settimanale quella fascia non direbbe niente, perche' una media
# di sette giorni oscilla molto meno di un singolo giorno e cadrebbe quasi
# sempre dentro.
BAND_WEEKS = 12
MIN_BAND_WEEKS = 6

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# Per i messaggi d'errore, che sono in italiano.
GIORNI = ("lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato", "domenica")


def last_closed_monday(today: date) -> date:
    """Il lunedi' della settimana prima di quella di oggi."""
    return today - timedelta(days=today.weekday() + 7)


def _value(value: Any, digits: int = 1) -> Any:
    """Il valore pronto per il JSON: NaN e None diventano None, i numeri
    arrotondati, il resto (testo) com'e'.

    Gli interi di numpy vanno dichiarati: `np.float64` e' un `float` per
    Python, `np.int64` non e' un `int`, e passando di qui intatto faceva
    fallire `json.dumps` (la potenza massima, che e' una colonna di interi)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float, np.integer)):
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
    measured = has_distance(row["sport"])
    return {
        "date": start.date().isoformat(),
        "weekday": WEEKDAYS[start.weekday()],
        "start_time": start.strftime("%H:%M"),
        "sport": row["sport"],
        "sub_sport": row["sub_sport"] if row["sub_sport"] not in (None, "", "generic") else None,
        "name": row["activity_name"],
        # Niente distanza per il tapis roulant: e' una stima del polso (todo
        # 45). Di quelle sedute restano i minuti e il battito.
        "distance_km": _value(row["total_distance_km"], 2) if measured else None,
        "duration_min": _value(row["total_time_min"], 0),
        "ascent_m": _value(row["total_ascent_m"], 0),
        "avg_hr": _value(row["avg_heart_rate"], 0),
        "max_hr": _value(row["max_heart_rate"], 0),
    }


def _training(week: pd.DataFrame, start: date, last_day: date, today: date) -> dict[str, Any]:
    """Totali della settimana. Distanza e dislivello solo per sport: sommati
    fra sport diversi non vogliono dire niente, e per gli sport senza
    distanza (il tapis roulant) la distanza non si somma affatto. I giorni di riposo contano
    solo fino all'ultimo giorno passato, e oggi senza attivita' non e' ancora
    un riposo: la giornata non e' finita."""
    by_sport = {}
    for sport, group in week.groupby("sport", sort=False):
        by_sport[sport] = {
            "sessions": int(len(group)),
            "time_min": _value(group["total_time_min"].sum(), 0),
            "distance_km": (
                _value(group["total_distance_km"].sum(min_count=1), 1)
                if has_distance(sport)
                else None
            ),
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
                        "distance_km": (
                            _value(a["total_distance_km"], 2) if has_distance(a["sport"]) else None
                        ),
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


def _week_mean(health: pd.DataFrame, column: str, monday: date) -> float | None:
    """La media di `column` nei sette giorni che cominciano `monday`, o
    `None` se non c'e' nemmeno un valore."""
    week = health.reindex(pd.date_range(monday, periods=7, freq="D"))[column].dropna()
    return float(week.mean()) if len(week) else None


def _week_measures(health: pd.DataFrame, monday: date) -> dict[str, dict[str, Any]]:
    """Le misure di Health e Recovery della settimana (todo 52): la media
    dei sette giorni e la fascia in cui si e' mossa nelle `BAND_WEEKS`
    settimane precedenti.

    **La fascia non e' quella della Day.** Li' il confronto e' fra il valore
    di un giorno e i 28 giorni prima; qui fra una media settimanale e le
    dodici medie settimanali che la precedono. Attorno a una media la fascia
    giornaliera non direbbe niente: sette giorni oscillano molto meno di
    uno, e il valore cadrebbe quasi sempre dentro.

    `_band` e' la stessa della Day, con il minimo dei valori abbassato a
    `MIN_BAND_WEEKS`: e' importata qui dentro e non in testa al modulo
    perche' `daily_data` importa gia' da qui, e in testa sarebbe un giro
    chiuso."""
    from training.interface.daily_data import _band

    out: dict[str, dict[str, Any]] = {}
    for card, column, label, unit, digits in WEEK_MEASURES:
        before = pd.Series(
            [_week_mean(health, column, monday - timedelta(weeks=k)) for k in range(1, BAND_WEEKS + 1)],
            dtype="float64",
        )
        out[column] = {
            "card": card,
            "label": label,
            "unit": unit,
            "value": _value(_week_mean(health, column, monday), digits),
            "band": _band(before, WEEK_LIMITS.get(column), digits, MIN_BAND_WEEKS),
            "weeks": int(before.notna().sum()),
        }
    return out


def _as_of(week_health: pd.DataFrame, last_day: date) -> date:
    """L'ultimo giorno della settimana che porta dei dati di salute, o
    `last_day` se non ce n'e' nessuno.

    Serve al carico, ai bersagli e alla forma: sono stati di fine settimana,
    e in una settimana ancora in corso l'ultimo giorno e' oggi, i cui file
    arrivano solo col giro della sera."""
    known = week_health[week_health["load_acute"].notna() | week_health["readiness"].notna()]
    if known.empty:
        return last_day
    return min(known.index[-1].date(), last_day)


def _load_targets_on(day: date, data_dir: Path) -> dict[str, Any] | None:
    """I bersagli di Garmin per il carico mensile, nel giorno `day`."""
    from training.interface.daily_data import _load_targets

    return _load_targets(day.isoformat(), data_dir)


def _week_fitness(
    health: pd.DataFrame, activities: pd.DataFrame, last_day: date, data_dir: Path
) -> dict[str, Any]:
    """La forma alla fine della settimana (todo 52): VO2max, i due punteggi,
    gli acclimatamenti e la soglia.

    Non si media: sono stati, non cose che succedono nei sette giorni. Vale
    quello dell'ultimo giorno — della domenica, o di oggi se la settimana e'
    ancora aperta. Sono gli stessi numeri della card Fitness della Day, con
    le loro fasce a 28 giorni: quelle restano giornaliere perche' qui il
    valore e' di un giorno solo, non una media."""
    from training.interface.daily_data import _hr_zones, fitness_on
    from training.interface.health import load_lactate_threshold

    fitness = fitness_on(health, last_day)
    lactate = load_lactate_threshold(data_dir)
    fitness["lactate_threshold"] = (
        lactate if lactate and lactate["as_of"] <= last_day.isoformat() else None
    )
    # La soglia dell'orologio, il ripiego di quando Garmin non ne ha
    # rilevata una: viene dalle zone dell'ultima attivita' a piedi, come
    # nella Day (`api/daily.daily_payload`).
    zones = _hr_zones(activities, last_day)
    fitness["threshold_hr"] = (
        {"value": zones["threshold_hr"], "as_of": zones["as_of"]}
        if zones and zones.get("threshold_hr") is not None
        else None
    )
    return fitness


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
        # Health e Recovery come medie dei sette giorni, con la fascia delle
        # dodici settimane prima; Fitness come stava alla fine (todo 52).
        "measures": _week_measures(health, monday),
        # **Non `last_day` ma l'ultimo giorno che ha dei dati.** In una
        # settimana in corso l'ultimo giorno e' oggi, e i file di oggi
        # arrivano col giro della sera: fino ad allora carico, bersagli e
        # acclimatamenti sarebbero vuoti, e le card senza barre.
        "fitness": _week_fitness(health, activities, _as_of(week_health, last_day), data_dir),
        # Le fasce obiettivo del carico, per la barra della card Load: sono
        # di Garmin e stanno nel file del giorno, come nella Day, che le
        # cerca nel giorno del carico e non in quello chiesto.
        "load_targets": _load_targets_on(_as_of(week_health, last_day), data_dir),
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
