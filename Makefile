.PHONY: update_activity backfill_activity_names backfill_health fitness_status interface activity_reports

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

fitness_status:
	uv run training-fitness-status

interface:
	uv run streamlit run src/training/interface/app.py

activity_reports:
	uv run training-activity-reports
