"""Esportazione delle metriche giornaliere di salute/wellness."""

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from garminconnect import Garmin

from .client import safe_call
from .config import REQUEST_DELAY

DAILY_ENDPOINTS = {
    "stats": lambda api, d: api.get_stats(d),
    "sleep": lambda api, d: api.get_sleep_data(d),
    "stress": lambda api, d: api.get_stress_data(d),
    "hrv": lambda api, d: api.get_hrv_data(d),
    "spo2": lambda api, d: api.get_spo2_data(d),
    "respiration": lambda api, d: api.get_respiration_data(d),
    "resting_heart_rate": lambda api, d: api.get_rhr_day(d),
    "training_readiness": lambda api, d: api.get_training_readiness(d),
    "training_status": lambda api, d: api.get_training_status(d),
}


def export_daily_health(
    api: Garmin,
    out_dir: Path,
    start_date: date,
    end_date: date,
    force_dates: Optional[set[date]] = None,
) -> None:
    """Esporta le metriche giornaliere tra start_date e end_date, saltando i
    giorni gia' presenti su disco. Le date in force_dates vengono invece
    riscaricate e sovrascritte sempre (utile per il giorno corrente, i cui
    valori possono cambiare nel corso della giornata)."""
    force_dates = force_dates or set()
    health_dir = out_dir / "health"
    for name in DAILY_ENDPOINTS:
        (health_dir / name).mkdir(parents=True, exist_ok=True)

    total_days = (end_date - start_date).days + 1
    print(f"Scarico le metriche giornaliere di salute per {total_days} giorni "
          f"({start_date} -> {end_date})...")
    print("(puoi interrompere con Ctrl+C e rilanciare piu' tardi: riprendera' da dove eri arrivato)")

    d = start_date
    day_count = 0
    while d <= end_date:
        date_str = d.strftime("%Y-%m-%d")
        day_count += 1

        for name, func in DAILY_ENDPOINTS.items():
            target = health_dir / name / f"{date_str}.json"
            if target.exists() and d not in force_dates:
                continue
            data = safe_call(func, api, date_str)
            if data is not None:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            time.sleep(REQUEST_DELAY)

        if day_count % 30 == 0 or d == end_date:
            print(f"  ...elaborati {day_count}/{total_days} giorni (ultimo: {date_str})")

        d += timedelta(days=1)
