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
from training.interface.activity_report import activity_numbers
from training.interface.db import list_activities, load_activity_records
from training.interface.health import _day_paths, _dig, _primary_entry, _read_json
from training.interface.health_db import load_health_db
from training.interface.grade import EQUIV_SPEED_SPORTS
from training.interface.run_chart import EFFECTS, durations_s, effects, has_effects, zone_settings
from training.interface.weekly_data import WEEKDAYS, _load, _mean, _value

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

# Le soglie degli allarmi della sezione Health. Sono qui e non nel testo
# dell'agente: il modello racconta gli allarmi, non li decide.
RHR_RISE_BPM = 3  # FC a riposo sopra la media di 28 giorni...
RHR_RISE_DAYS = 2  # ...per tanti giorni di fila (D compreso)
RESP_RISE = 1.0  # atti/min sopra la media di 28 giorni
SHORT_NIGHT_HOURS = 7
SHORT_NIGHTS_ALERT = 3  # notti corte negli ultimi 7 giorni
# Una seduta e' impegnativa con almeno 10 minuti sopra il tetto di Z3 (alto
# aerobico piu' anaerobico, vedi `run_chart.effects`).
HARD_SESSION_MIN = 10  # contati con `_minutes_above_z3`, anche senza soglia
VO2MAX_CHANGE = 0.5
RECENT_DAYS = 14
# Il confronto con le sedute simili di prima (todo 43): quanto si guarda
# indietro, e quante ne servono perche' una mediana voglia dire qualcosa. Con
# due sedute la mediana e' un caso, e l'allenatore non deve poterci costruire
# sopra un andamento.
COMPARE_WINDOW_DAYS = 90
MIN_COMPARABLE = 3
# I giorni misurati che servono perche' uno scarto tipo voglia dire qualcosa:
# sotto, la fascia del battito a riposo non si da'.
MIN_BAND_DAYS = 14
BASELINE_SHORT = 7
BASELINE_LONG = 28


def _health_row(health: pd.DataFrame, day: date) -> pd.Series:
    """La riga di salute di `day`, tutta NaN se il giorno non c'e'."""
    return health.reindex([pd.Timestamp(day)]).iloc[0]


def _window(health: pd.DataFrame, column: str, end: date, days: int) -> pd.Series:
    """I `days` giorni che finiscono il giorno prima di `end` (escluso)."""
    index = pd.date_range(end - timedelta(days=days), end - timedelta(days=1), freq="D")
    return health.reindex(index)[column]


def _band(window: pd.Series) -> dict[str, Any] | None:
    """Dove sta di solito una misura: la media della finestra piu' e meno uno
    scarto tipo (`low`, `high`) e piu' e meno due (`outer_low`,
    `outer_high`). Dentro la prima sta la normalita', fuori dalla seconda c'e'
    poco da discutere. La finestra e' quella di `avg_28d`, cosi' la media e la
    fascia raccontano lo stesso periodo.

    Garmin una fascia la manda solo per l'HRV (`_hrv_baseline`); queste si
    calcolano dallo storico. Non sono soglie d'allarme - quello del battito
    a riposo scatta a `RHR_RISE_BPM` sopra la media per `RHR_RISE_DAYS`
    giorni di fila - ma dicono dove la misura sta di solito. `None` sotto
    `MIN_BAND_DAYS` giorni misurati, dove lo scarto tipo sarebbe rumore."""
    values = window.dropna()
    if len(values) < MIN_BAND_DAYS:
        return None
    mean, sd = values.mean(), values.std()
    if pd.isna(mean) or pd.isna(sd):
        return None
    return {
        "low": _value(mean - sd, 1),
        "high": _value(mean + sd, 1),
        "outer_low": _value(mean - 2 * sd, 1),
        "outer_high": _value(mean + 2 * sd, 1),
    }


def _morning(health: pd.DataFrame, day: date) -> dict[str, Any]:
    """Ogni misura: il valore, le medie a 7 e 28 giorni (con quanti giorni) e
    la differenza dalla media a 28. Le medie sono calcolate rispetto al giorno
    da cui si legge la misura."""
    result = {}
    for name, (column, offset) in MORNING_METRICS.items():
        source = day + timedelta(days=offset)
        value = _value(_health_row(health, source)[column], 1)
        short = _mean(_window(health, column, source, BASELINE_SHORT), 1)
        long_window = _window(health, column, source, BASELINE_LONG)
        long = _mean(long_window, 1)
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
            "band": _band(long_window),
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
    # Due decimali e non uno: una notte da 6,98 h e' corta, e a un decimale si
    # leggerebbe "7.0" fra le notti sotto le 7 ore.
    hours = {d.date().isoformat(): _value(v, 2) for d, v in nights.items()}
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


# Le fasce obiettivo del carico mensile per zona, come le chiama Garmin nel
# JSON del training status. `health_daily` non le tiene: si leggono dal file
# del giorno, come la fascia dell'HRV.
LOAD_TARGET_FIELDS = {
    "load_aerobic_low": "monthlyLoadAerobicLow",
    "load_aerobic_high": "monthlyLoadAerobicHigh",
    "load_anaerobic": "monthlyLoadAnaerobic",
}


def _load_targets(as_of: str, data_dir: Path = DATA_DIR) -> dict[str, Any] | None:
    """Le fasce obiettivo (`min`, `max`) del carico per zona nel giorno
    `as_of`, quello del carico di `_load`. `None` se il file non c'e', non
    e' di quel giorno o non ha le fasce."""
    path = _day_paths(Path(data_dir) / "health", as_of)["training_status"]
    entry = _primary_entry(
        _dig(_read_json(path), "mostRecentTrainingLoadBalance", "metricsTrainingLoadBalanceDTOMap")
    )
    if entry is None or entry.get("calendarDate") != as_of:
        return None
    targets = {
        name: {"min": entry.get(f"{field}TargetMin"), "max": entry.get(f"{field}TargetMax")}
        for name, field in LOAD_TARGET_FIELDS.items()
    }
    if any(t["min"] is None or t["max"] is None for t in targets.values()):
        return None
    return targets


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


def _effect_minutes(activity: pd.Series, records: pd.DataFrame) -> dict[str, float] | None:
    """I minuti per effetto stimato (`run_chart.effects`), o `None` senza zone,
    soglia o battiti."""
    bounds, threshold = zone_settings(activity)
    if not has_effects(bounds, threshold):
        return None
    if records.empty or records["heart_rate"].isna().all():
        return None
    seconds = effects(records, bounds, threshold)
    return {name: _value(seconds[name] / 60, 1) for name in EFFECTS}


def _minutes_above_z3(activity: pd.Series, records: pd.DataFrame) -> float | None:
    """I minuti con i battiti sopra il tetto di Z3 (alto aerobico piu'
    anaerobico). Servono solo i tetti delle zone, non la soglia: molti file
    (tutto agosto 2026, le uscite in bici) la salvano a zero o non ce
    l'hanno, e senza questo conto non si troverebbe nessuna seduta
    impegnativa. `None` senza zone o senza battiti."""
    bounds, _ = zone_settings(activity)
    if not bounds:
        return None
    if records.empty or records["heart_rate"].isna().all():
        return None
    above = records["heart_rate"].astype(float) > bounds[2]
    return _value(float(durations_s(records)[above].sum()) / 60, 1)


# Quanti decimali per ogni numero di `activity_numbers`: le velocita' e le
# percentuali uno, i battiti e la cadenza nessuno.
_EXECUTION_DIGITS = {
    "speed_first_half_kmh": 1,
    "speed_second_half_kmh": 1,
    "speed_change_pct": 1,
    "hr_first_half": 0,
    "hr_second_half": 0,
    "hr_change_pct": 1,
    "cadence_mean": 0,
    "cadence_variation_pct": 1,
    "uphill_hr": 0,
    "flat_hr": 0,
}


def _execution(records: pd.DataFrame) -> dict[str, Any] | None:
    """Come e' stata corsa la seduta (todo 43): le due meta' per velocita' e
    battiti, la cadenza, i battiti in salita contro quelli in piano. I conti
    sono quelli di `activity_report.activity_numbers`, gli stessi che vanno
    nei report per attivita'; qui si arrotondano. `None` se dai record non si
    ricava niente (palestra, file senza campioni)."""
    if records.empty:
        return None
    numbers = activity_numbers(records)
    if all(value is None for value in numbers.values()):
        return None
    return {name: _value(value, _EXECUTION_DIGITS[name]) for name, value in numbers.items()}


def _compared_with(activities: pd.DataFrame, activity: pd.Series) -> dict[str, Any]:
    """Le sedute simili dei `COMPARE_WINDOW_DAYS` giorni prima: stesso sport, e
    stesso tipo di corsa quando la seduta ne ha uno. Rende quante sono e le
    mediane con cui confrontarla.

    Il giorno stesso resta fuori: il confronto e' con quello che c'era prima.
    Sotto `MIN_COMPARABLE` sedute le mediane non si danno (restano `None`):
    il numero si da' comunque, cosi' chi scrive sa perche' non c'e' il
    paragone."""
    day = activity["start_time"].date()
    days = activities["start_time"].dt.date
    run_type = _value(activity["run_type"])
    indoor = activity["sub_sport"] == "treadmill"
    similar = activities[
        (activities["sport"] == activity["sport"])
        & (days >= day - timedelta(days=COMPARE_WINDOW_DAYS))
        & (days < day)
    ]
    if run_type is not None:
        similar = similar[similar["run_type"] == run_type]
    # Il nastro con il nastro, la strada con la strada: una corsa sul tapis
    # roulant accanto alla mediana delle uscite all'aperto non dice niente,
    # ne' sulla distanza ne' sul passo.
    similar = similar[(similar["sub_sport"] == "treadmill") == indoor]
    median = None
    if len(similar) >= MIN_COMPARABLE:
        median = {
            "distance_km": _value(similar["total_distance_km"].median(), 2),
            "duration_min": _value(similar["total_time_min"].median(), 0),
            "avg_hr": _value(similar["avg_heart_rate"].median(), 0),
            "grade_adjusted_speed_kmh": _value(similar["equiv_speed_kmh"].median(), 1),
        }
    return {
        "sport": _value(activity["sport"]),
        "run_type": run_type,
        "indoor": bool(indoor),
        "window_days": COMPARE_WINDOW_DAYS,
        "count": int(len(similar)),
        "median": median,
    }


def _power(records: pd.DataFrame) -> dict[str, Any]:
    """La potenza di corsa, media e massima, quando l'orologio la registra.
    Sul tapis roulant e' la misura di sforzo che non dipende da quanto bene
    il polso indovina la distanza."""
    if records.empty or "power" not in records:
        return {"avg_power": None, "max_power": None}
    power = records["power"].dropna()
    if power.empty:
        return {"avg_power": None, "max_power": None}
    return {"avg_power": _value(power.mean(), 0), "max_power": _value(power.max(), 0)}


def _session(activity: pd.Series, data_dir: Path, activities: pd.DataFrame) -> dict[str, Any]:
    start = activity["start_time"]
    # I record una volta sola: li vogliono gli effetti, i minuti sopra Z3 e
    # `_execution`.
    records = load_activity_records(int(activity["activity_id"]), data_dir)
    return {
        "date": start.date().isoformat(),
        "weekday": WEEKDAYS[start.weekday()],
        "start_time": start.strftime("%H:%M"),
        "sport": activity["sport"],
        # Il tapis roulant cambia come si racconta la seduta (non si "esce",
        # non c'e' terreno, il passo e' quello del nastro) e con cosa si
        # confronta: senza questo l'agente vede solo "running".
        "sub_sport": _value(activity["sub_sport"]),
        "indoor": bool(activity["sub_sport"] == "treadmill"),
        "name": activity["activity_name"],
        "distance_km": _value(activity["total_distance_km"], 2),
        "duration_min": _value(activity["total_time_min"], 0),
        "ascent_m": _value(activity["total_ascent_m"], 0),
        "avg_hr": _value(activity["avg_heart_rate"], 0),
        "max_hr": _value(activity["max_heart_rate"], 0),
        # Calorie e potenza: su un tapis roulant sono i segnali onesti, dove
        # distanza e velocita' le stima il polso e in salita sbagliano di
        # molto. Garmin le calorie le da' per tutte le sedute.
        "calories": _value(activity["total_calories"], 0),
        **_power(records),
        "aerobic_te": _value(activity["aerobic_te"], 1),
        "anaerobic_te": _value(activity["anaerobic_te"], 1),
        "grade_adjusted_speed_kmh": _value(activity["equiv_speed_kmh"], 1),
        # Che seduta voleva essere: il tipo (scelto da Andrea o stimato), il
        # terreno e l'allenamento pianificato che l'orologio ha seguito.
        "run_type": _value(activity["run_type"]),
        "run_type_source": _value(activity["run_type_source"]),
        "terrain": _value(activity["terrain"]),
        "workout_name": _value(activity["workout_name"]),
        "workout_active_steps": _value(activity["workout_active_steps"], 0),
        "workout_active_max_s": _value(activity["workout_active_max_s"], 0),
        "effect_minutes": _effect_minutes(activity, records),
        "minutes_above_z3": _minutes_above_z3(activity, records),
        "execution": _execution(records),
        "compared_with": _compared_with(activities, activity),
    }


def _latest_with_change(health: pd.DataFrame, day: date, column: str, digits: int = 1) -> dict[str, Any] | None:
    """Il valore piu' recente di `column` fino a `day`, il giorno della riga
    da cui viene, e la variazione rispetto al valore piu' recente di 28
    giorni prima (None se allora non c'era). None se non c'e' nessun valore."""
    values = health.loc[: pd.Timestamp(day), column].dropna()
    if values.empty:
        return None
    now = float(values.iloc[-1])
    before = health.loc[: pd.Timestamp(day - timedelta(days=BASELINE_LONG)), column].dropna()
    then = float(before.iloc[-1]) if not before.empty else None
    return {
        "now": _value(now, digits),
        "as_of": values.index[-1].date().isoformat(),
        "days_ago_28": _value(then, digits),
        "change": _value(now - then, digits) if then is not None else None,
    }


def fitness_on(health: pd.DataFrame, day: date) -> dict[str, Any]:
    """La card Fitness della Day in React (todo 37 e 38): VO2max, endurance e
    hill score piu' recenti fino a `day`, sempre, con la data e la variazione
    in 28 giorni. Al contrario di `_vo2max_change` non c'e' soglia: la card li
    mostra anche quando non si sono mossi.

    La usa solo `GET /api/daily/{day}`, non `build_daily_data`: il JSON del
    report giornaliero non cambia."""
    vo2max = _latest_with_change(health, day, "vo2max")
    if vo2max is not None:
        # Il giorno in cui Garmin l'ha misurato, non quello del file che lo
        # porta (vedi `health._vo2max`).
        measured = health.at[pd.Timestamp(vo2max["as_of"]), "vo2max_date"]
        if isinstance(measured, str):
            vo2max["as_of"] = measured
    endurance = _latest_with_change(health, day, "endurance_score", digits=0)
    if endurance is not None:
        level = health.at[pd.Timestamp(endurance["as_of"]), "endurance_level"]
        endurance["level"] = level if isinstance(level, str) else None
    return {
        "vo2max": vo2max,
        "endurance": endurance,
        "hill": _latest_with_change(health, day, "hill_score", digits=0),
    }


def _hr_zones(activities: pd.DataFrame, day: date) -> dict[str, Any] | None:
    """Le zone cardiache in bpm in vigore il giorno `day`: quelle dell'ultima
    attivita' a piedi fino a quel giorno che le ha salvate (l'orologio le scrive nel
    FIT e le aggiorna da solo: il 07/10/2026 il tetto di Z3 e' passato da 141 a
    142). Servono al report per dare i bersagli in bpm. `None` se nessuna
    attivita' le ha."""
    known = activities[
        (activities["start_time"].dt.date <= day) & activities["hr_zone_bounds"].notna()
    ].sort_values("start_time")
    # Le zone di un'attivita' a piedi: quelle della bici sono piu' basse e
    # senza soglia, e i bersagli di una corsa presi da li' venivano bassi
    # (il 24/09/2026 Z4 a 138-154 invece di 143-155). Le altre solo se non ce
    # n'e' nessuna a piedi.
    on_foot = known[known["sport"].isin(EQUIV_SPEED_SPORTS)]
    if not on_foot.empty:
        known = on_foot
    if known.empty:
        return None
    activity = known.iloc[-1]
    bounds, threshold = zone_settings(activity)
    if not bounds:
        return None
    z1, z2, z3, z4 = bounds
    zones = {
        "Z1": {"max": z1},
        "Z2": {"min": z1 + 1, "max": z2},
        "Z3": {"min": z2 + 1, "max": z3},
        "Z4": {"min": z3 + 1, "max": z4},
        "Z5": {"min": z4 + 1},
    }
    # Una soglia che non sta sopra Z3 (alcuni file la salvano a zero) non e'
    # una soglia: `None`, e niente fasce degli effetti.
    valid = has_effects(bounds, threshold)
    result = {
        "as_of": activity["start_time"].date().isoformat(),
        "zones": zones,
        "threshold_hr": threshold if valid else None,
    }
    # Le fasce degli effetti, con le stesse regole di `run_chart.effect_of`.
    if valid:
        result["effects"] = {
            EFFECTS[0]: {"max": z3},
            EFFECTS[1]: {"min": z3 + 1, "max": threshold},
            EFFECTS[2]: {"min": threshold + 1},
        }
    return result


def _on(activities: pd.DataFrame, day: date) -> pd.DataFrame:
    return activities[activities["start_time"].dt.date == day].sort_values("start_time")


def _recent(activities: pd.DataFrame, day: date, data_dir: Path) -> dict[str, Any]:
    """Il contesto prima di D: da quanto non ci si allena, da quanto non si fa
    una seduta impegnativa, i riposi della settimana e le attivita' delle
    ultime due settimane in una riga ciascuna.

    L'ultima attivita' e l'ultima seduta impegnativa sono *prima* di D, e lo
    dicono i nomi delle chiavi: un'attivita' gia' fatta in D e' in
    `trained_today` (e in `sessions.today`), cosi' "3 giorni dall'ultima
    attivita'" non sembra vero quando ci si e' gia' allenati oggi."""
    dates = activities["start_time"].dt.date
    before = activities[dates < day].sort_values("start_time")
    last = before.iloc[-1]["start_time"].date() if not before.empty else None

    last_hard = None
    window = before[before["start_time"].dt.date >= day - timedelta(days=BASELINE_LONG)]
    for _, activity in window.iloc[::-1].iterrows():
        records = load_activity_records(int(activity["activity_id"]), data_dir)
        minutes = _minutes_above_z3(activity, records)
        if minutes is not None and minutes >= HARD_SESSION_MIN:
            last_hard = activity["start_time"].date()
            break

    week = {day - timedelta(days=k) for k in range(1, 8)}
    active = set(dates[dates.isin(week)])

    # I fatti di calendario li conta lo script, non il modello: quanti giorni
    # di fila ci si e' allenati (o riposati) fino al giorno prima di D, e i 7
    # giorni prima di D uno per uno. Senza, il modello scriveva "quattro giorni
    # di fila" contando da solo, e sbagliava.
    trained = set(dates)
    streak, rest_streak = 0, 0
    while day - timedelta(days=streak + 1) in trained:
        streak += 1
    while day - timedelta(days=rest_streak + 1) not in trained and rest_streak < BASELINE_LONG:
        rest_streak += 1
    last_7_days = []
    for k in range(7, 0, -1):
        d = day - timedelta(days=k)
        on_day = activities[dates == d].sort_values("start_time")
        last_7_days.append(
            {
                "date": d.isoformat(),
                "weekday": WEEKDAYS[d.weekday()],
                "activities": [
                    f"{a['sport']} {_value(a['total_distance_km'], 1)} km" for _, a in on_day.iterrows()
                ],
            }
        )
    listed = activities[(dates >= day - timedelta(days=RECENT_DAYS - 1)) & (dates <= day)].sort_values("start_time")
    return {
        "trained_today": bool((dates == day).any()),
        "last_activity_before_today": last.isoformat() if last else None,
        "days_since_last_activity_before_today": (day - last).days if last else None,
        "last_hard_session_before_today": last_hard.isoformat() if last_hard else None,
        "days_since_last_hard_session_before_today": (day - last_hard).days if last_hard else None,
        "hard_session_rule": f"{HARD_SESSION_MIN}+ minutes above the top of Z3, "
        f"looked for in the last {BASELINE_LONG} days",
        "rest_days_last_7": len(week - active),
        "consecutive_training_days_before_today": streak,
        "consecutive_rest_days_before_today": rest_streak if streak == 0 else 0,
        "last_7_days": last_7_days,
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


def build_daily_data(
    day: date,
    data_dir: Path = DATA_DIR,
    activities: pd.DataFrame | None = None,
    health: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """I fatti del giorno `day`, come dizionario pronto per il JSON.

    `activities` e `health` sono quelli di `list_activities` e
    `load_health_db`: l'API li passa dalla sua cache, perche' rileggerli a
    ogni richiesta costa un secondo; senza, si leggono qui."""
    if activities is None:
        activities = list_activities(data_dir)
    if health is None:
        health = load_health_db(data_dir)

    morning = _morning(health, day)
    sleep = _sleep_last_7(health, day)
    load_now = _load(health, day)
    load_week_ago = _load(health, day - timedelta(days=7))
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
            "targets": _load_targets(load_now["as_of"], data_dir) if load_now else None,
            "week_ago": load_week_ago,
            "vo2max_change": _vo2max_change(health, day),
        },
        "sessions": {
            "yesterday": [
                _session(a, data_dir, activities)
                for _, a in _on(activities, day - timedelta(days=1)).iterrows()
            ],
            "today": [_session(a, data_dir, activities) for _, a in _on(activities, day).iterrows()],
        },
        "recent": _recent(activities, day, data_dir),
        "hr_zones": _hr_zones(activities, day),
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
