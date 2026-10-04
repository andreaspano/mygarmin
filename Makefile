.PHONY: update_activity backfill_activity_names backfill_health backfill fitness_status interface activity_reports

update_activity:
	uv run python -c "from training.garmin import update_activity; update_activity()"
	$(MAKE) activity_reports

backfill_activity_names:
	uv run python -c "from training.garmin import backfill_activity_names; backfill_activity_names()"

# Lo storico delle metriche di salute, dal 2025 a oggi: circa mezz'ora di
# chiamate a Garmin. Si puo' interrompere con Ctrl+C e rilanciare, riprende da
# dove era arrivato.
backfill_health:
	uv run python -c "from training.garmin import backfill_health; backfill_health()"

# Attivita' e metriche di salute di un intervallo a scelta, estremi inclusi:
#   make backfill FROM=2024-01-01 TO=2024-12-31
# Un anno di salute sono circa 3.300 chiamate (30-45 minuti). Come
# backfill_health, si interrompe con Ctrl+C e riprende dai giorni mancanti.
backfill:
	@test -n "$(FROM)" -a -n "$(TO)" || { echo "Uso: make backfill FROM=YYYY-MM-DD TO=YYYY-MM-DD"; exit 2; }
	uv run python -c "\
	from datetime import date; \
	from training.garmin.auth import init_api; \
	from training.garmin.config import DATA_DIR; \
	from training.garmin.activities import download_activities_between; \
	from training.garmin.health import export_daily_health; \
	start, end = date.fromisoformat('$(FROM)'), date.fromisoformat('$(TO)'); \
	assert start <= end, 'FROM deve venire prima di TO'; \
	api = init_api(); \
	download_activities_between(api, start.isoformat(), end.isoformat()); \
	export_daily_health(api, DATA_DIR, start, end)"
	$(MAKE) activity_reports

fitness_status:
	uv run training-fitness-status

interface:
	uv run streamlit run src/training/interface/app.py

activity_reports:
	uv run training-activity-reports
