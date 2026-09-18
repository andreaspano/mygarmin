.PHONY: update_activity backfill_activity_names fitness_status interface activity_reports

update_activity:
	uv run python -c "from training.garmin import update_activity; update_activity()"
	$(MAKE) activity_reports

backfill_activity_names:
	uv run python -c "from training.garmin import backfill_activity_names; backfill_activity_names()"

fitness_status:
	uv run training-fitness-status

interface:
	uv run streamlit run src/training/interface/app.py

activity_reports:
	uv run training-activity-reports
