.PHONY: update_activity backfill_activity_names backfill_health backfill fitness_status interface api frontend frontend_types activity_reports weekly_data daily_data

update_activity:
	uv run python -c "from training.garmin import update_activity; update_activity()"
	$(MAKE) activity_reports

backfill_activity_names:
	uv run python -c "from training.garmin import backfill_activity_names; backfill_activity_names()"

# Lo storico delle metriche di salute, da history_start (user/config.yaml) a
# oggi: 30-45 minuti di chiamate a Garmin per ogni anno. Si puo' interrompere
# con Ctrl+C e rilanciare, riprende da dove era arrivato.
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

# L'API in sola lettura, solo su 127.0.0.1 (niente login). Documentazione su
# http://127.0.0.1:8000/docs
api:
	uv run uvicorn training.api.app:app --host 127.0.0.1 --port 8000 --reload

# La pagina Day in React (todo 33), su http://127.0.0.1:5173. Chiede i dati
# all'API: prima make api. La prima volta: cd frontend && npm ci
frontend:
	cd frontend && npm run dev

# Rigenera i tipi TypeScript (frontend/src/api/schema.ts) dall'OpenAPI, dopo
# ogni cambio ai modelli dell'API. Con l'API accesa (make api).
frontend_types:
	cd frontend && npm run gen:api

activity_reports:
	uv run training-activity-reports

# I fatti di una settimana in JSON, per il report settimanale. Solo dati
# locali: per la settimana aggiornata, prima make update_activity.
#   make weekly_data                   (l'ultima settimana chiusa)
#   make weekly_data WEEK=2026-09-21   (un lunedi')
weekly_data:
	uv run training-weekly-data $(if $(WEEK),--week $(WEEK))

# I fatti di un giorno in JSON, per il report giornaliero. Solo dati locali:
# per il giorno aggiornato, prima make update_activity.
#   make daily_data                  (oggi)
#   make daily_data DAY=2026-10-07   (un giorno a scelta)
daily_data:
	uv run training-daily-data $(if $(DAY),--day $(DAY))
