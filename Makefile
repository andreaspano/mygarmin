.PHONY: install_cron uninstall_cron daily_report update_activity backfill_activity_names backfill_health backfill fitness_status api frontend frontend_types activity_reports weekly_data daily_data

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
# Un anno di salute sono circa 4.000 chiamate, undici al giorno (30-45
# minuti). Come
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

# L'API, solo su 127.0.0.1 (niente login): letture, piu' il terreno, il tipo di
# corsa e il tasto Refresh (todo 41), che lancia `claude`. Documentazione su
# http://127.0.0.1:8000/docs
api:
	uv run uvicorn training.api.app:app --host 127.0.0.1 --port 8000 --reload

# La pagina Day in React (todo 33 e 34), su http://127.0.0.1:5173. Chiede i dati
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

# Il report giornaliero, scritto dai sette agenti uno alla volta (todo 44).
# Lo stesso lavoro del tasto Refresh, ma da terminale: scarica i dati nuovi,
# prepara i fatti una volta sola e lancia gli agenti in fila.
#   make daily_report                        (oggi, tutte le sezioni)
#   make daily_report DAY=2026-10-07         (un giorno a scelta)
#   make daily_report SECTION=health         (solo una sezione)
daily_report:
	uv run training-daily-report $(if $(DAY),--day $(DAY)) $(if $(SECTION),--section $(SECTION))

# I fatti di un giorno in JSON, per il report giornaliero. Solo dati locali:
# per il giorno aggiornato, prima make update_activity.
#   make daily_data                  (oggi)
#   make daily_data DAY=2026-10-07   (un giorno a scelta)
daily_data:
	uv run training-daily-data $(if $(DAY),--day $(DAY))

# I due giri che scrivono il report da soli (todo 47): le 10 e le 22. Le
# righe stanno in deploy/crontab con tre segnaposto, perche' cron da' un PATH
# scarno e il repo puo' stare dove vuole.
#
# L'installazione e' ripetibile: toglie le righe `# mygarmin` che ci sono gia'
# e rimette queste, senza toccare il resto del tuo crontab.
UV := $(shell command -v uv)
# La cartella di uv entra nel PATH delle righe di cron: il percorso assoluto
# basta a lanciare il comando, non a `make update_activity` che dentro chiama
# un altro `uv run`.
UV_DIR := $(dir $(UV))
CRON_LOG := $(HOME)/.local/state/mygarmin-report.log
install_cron:
	@test -n "$(UV)" || { echo "uv non e' nel PATH"; exit 1; }
	@mkdir -p $(dir $(CRON_LOG))
	@{ crontab -l 2>/dev/null | grep -v '# mygarmin$$' || true; \
	   sed -e 's|__REPO__|$(CURDIR)|' -e 's|__UV__|$(UV)|' -e 's|__UVDIR__|$(UV_DIR:/=)|' \
	       -e 's|__LOG__|$(CRON_LOG)|' \
	       deploy/crontab | grep '# mygarmin$$'; } | crontab -
	@echo "Installato. Il crontab adesso:"
	@crontab -l | grep '# mygarmin$$'
	@echo "Il registro dei giri: $(CRON_LOG)"

# Toglie i due giri e lascia il resto del crontab com'e'.
uninstall_cron:
	@{ crontab -l 2>/dev/null | grep -v '# mygarmin$$' || true; } | crontab -
	@echo "Tolti. Il crontab adesso:"
	@crontab -l 2>/dev/null || echo "  (vuoto)"
