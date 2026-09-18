"""Punto di ingresso: orchestra login ed esportazione di tutti i dati."""

from . import config
from .activities import export_activities
from .auth import init_api
from .health import export_daily_health
from .misc import export_misc


def main() -> None:
    out_dir = config.OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Backup completo dati Garmin Connect")
    print(f"Cartella di destinazione: {out_dir.resolve()}")
    print("=" * 70)

    try:
        api = init_api()

        export_activities(api, out_dir)
        print()
        export_misc(api, out_dir, config.START_DATE, config.END_DATE)
        print()
        export_daily_health(api, out_dir, config.START_DATE, config.END_DATE)

        print()
        print("Fatto! Tutti i dati sono in:", out_dir.resolve())
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Rilancia lo script quando vuoi: riprendera' da dove eri arrivato.")
