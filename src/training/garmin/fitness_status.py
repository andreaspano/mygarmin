"""Sintesi dello stato di forma recente: attivita' + metriche di benessere.

Usa una cache locale su disco (data/) e la aggiorna solo dove serve: le
attivita' gia' scaricate e i giorni di salute passati non vengono
richiesti di nuovo, mentre le metriche di oggi vengono sempre riscaricate
perche' possono cambiare nel corso della giornata (es. training readiness
dopo un allenamento mattutino).
"""

import contextlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .activities import download_activities_between
from .auth import init_api
from .client import safe_call
from .config import DATA_DIR, FITNESS_STATUS_WINDOW_DAYS
from .health import DAILY_ENDPOINTS, export_daily_health


def _load_cached_health(data_dir: Path, start_date: date, end_date: date) -> dict[str, dict[str, Any]]:
    health_dir = data_dir / "health"
    result: dict[str, dict[str, Any]] = {name: {} for name in DAILY_ENDPOINTS}

    d = start_date
    while d <= end_date:
        date_str = d.strftime("%Y-%m-%d")
        for name in DAILY_ENDPOINTS:
            path = health_dir / name / f"{date_str}.json"
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    result[name][date_str] = json.load(f)
        d += timedelta(days=1)

    return result


def build_fitness_status(
    data_dir: Path = DATA_DIR, days: int = FITNESS_STATUS_WINDOW_DAYS
) -> dict[str, Any]:
    data_dir = Path(data_dir)
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    api = init_api()

    print(f"Aggiorno i dati recenti ({start_date} -> {today})...")
    download_activities_between(api, start_date.isoformat(), today.isoformat(), data_dir)
    export_daily_health(api, data_dir, start_date, today, force_dates={today})

    activities = safe_call(
        api.get_activities_by_date, start_date.isoformat(), today.isoformat(), sortorder="asc"
    ) or []

    health = _load_cached_health(data_dir, start_date, today)

    return {
        "window": {"start": start_date.isoformat(), "end": today.isoformat(), "days": days},
        "activities": activities,
        "health": health,
    }


def main() -> None:
    """Stampa lo snapshot come JSON su stdout; ogni messaggio di
    avanzamento (proprio o delle funzioni chiamate) va su stderr, per
    lasciare stdout pulito a chi consuma l'output come JSON."""
    with contextlib.redirect_stdout(sys.stderr):
        status = build_fitness_status()
    print(json.dumps(status, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
