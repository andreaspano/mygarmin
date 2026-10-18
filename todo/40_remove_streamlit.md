---
status: done
---

# Via Streamlit

L'interfaccia di tutti i giorni e' ormai la Day in React con l'API. Il codice
Streamlit (`make interface`) se ne va tutto: le pagine, i moduli che usa solo
lui, la dipendenza e il target del Makefile.

## Decisioni

Prese con Andrea il 2026-10-18:

- **Via tutto Streamlit.** Le pagine che oggi esistono solo li' (Activities,
  Week, Month, Recovery, Profile) spariscono; torneranno in React con todo a
  parte. Nella barra in alto della React restano le voci grigie di oggi.
- **Il codice in comune resta**: quello che usano l'API, i comandi `make` e
  gli agenti dei report.
- **Il pacchetto si chiama ancora `interface`**: rinominarlo toccherebbe ogni
  import per niente.
- **I todo vecchi non si toccano**, anche dove parlano di Streamlit: sono la
  storia.

## Work

### I moduli Streamlit

Importano `streamlit` e li usano solo fra loro (nessun modulo che resta, ne'
l'API, ne' un comando, ne' un agente li importa). Si cancellano:

- `src/training/interface/app.py`, `filters.py`, `data.py`,
  `period_page.py`, `activity_detail.py`, `activity_table.py`,
  `report_view.py`;
- tutta la cartella `src/training/interface/app_pages/` (activities, week,
  month, recovery, profile).

### Il codice che diventa morto

- `health.load_health()`: la usava solo `data.py`. Via, e la docstring di
  `health_db.load_health_db` che la cita dice la forma senza rimandare a lei.
- Tutto il resto che i moduli Streamlit prendevano dai moduli in comune
  (`run_analysis_chart`, `effects`, `has_effects`, `zone_settings`,
  `EFFECTS`, `sport_label`, `SPORT_ICON_FILES`, `parse_report`,
  `section_icon`, ...) lo usano ancora l'API o `daily_data`: resta.

### Dipendenze e Makefile

- `uv remove streamlit` (aggiorna `pyproject.toml` e `uv.lock`). `altair`
  resta (`run_chart.py` e `/api/activities/{id}/chart/vega`), `pyyaml` anche
  (`garmin/config.py`).
- `Makefile`: via il target `interface` e la sua voce in `.PHONY`.

### I testi che parlano di Streamlit

Solo commenti e docstring, che vanno riscritti per dire com'e' oggi (API,
React, report):

- `src/training/interface/__init__.py` (es. "Lettura dei FIT e della
  salute, grafici e fatti per l'API e per i report");
- `src/training/interface/db.py` (verso l. 14), `health.py` (l. 13),
  `sports.py` (l. 3), `report_text.py` (l. 1), `activity_report.py` (l. 3),
  `run_chart.py` (verso l. 508);
- `src/training/api/cache.py` (l. 5-6) e `api/context.py` (l. 15);
- `README.md`: le frasi su Streamlit (verso l. 41, 53, 87) vanno via, e la
  sezione della Day in React dice che l'interfaccia e' solo React con l'API;
- `.claude/skills/atodo/SKILL.md`: il controllo "Streamlit UI" diventa un
  controllo "React UI" (`cd frontend && npm run build`, e la pagina nel
  browser con l'API accesa), cosi' i prossimi todo non cercano Streamlit.

## Vincoli

- Nessuna dipendenza nuova.
- L'API, i comandi (`make daily_data`, `make weekly_data`, `make
  activity_reports`, `make fitness_status`) e la Day in React si comportano
  esattamente come prima.
- Commenti in italiano senza accenti.

## Rischi

- **Un import dimenticato**: un modulo che resta e importa da uno cancellato
  fallirebbe solo quando viene usato. La verifica importa tutti i moduli che
  restano e chiama gli endpoint e i comandi.
- **La `.venv`** perde streamlit al prossimo `uv sync`: se servisse
  riaverlo (revert), basta un altro `uv sync`.

## Verifica

1. `grep -rn -i streamlit src Makefile pyproject.toml README.md .claude` non
   trova niente; `grep -c streamlit uv.lock` da' 0.
2. `uv sync`, poi `uv run python -c "import training; from training.api
   import app; from training.interface import db, fit, health, health_db,
   daily_data, weekly_data, run_chart, report_text, sports, terrain,
   run_type, grade, activity_report"`.
3. Prima di cominciare si salvano `make daily_data DAY=2026-10-15` e `make
   weekly_data WEEK=2026-10-12`; alla fine danno lo stesso JSON, byte per
   byte. `make activity_reports` gira senza errori (0 report nuovi).
4. `TestClient`, sui dati locali: `/api/activities`,
   `/api/activities/{id}`, `/api/activities/{id}/chart`,
   `/api/activities/{id}/chart/vega`, `/api/daily/2026-10-15` e
   `/api/reports/daily/2026-10-15` rispondono 200 con lo stesso corpo di
   prima (salvato prima di cominciare).
5. `cd frontend && npm run build`; `npm run gen:api` e `git diff
   --exit-code frontend/src/api/schema.ts` (l'API non cambia).
6. Nel browser (Claude in Chrome, o Chrome headless se l'estensione non
   c'e'): la Day del 2026-10-15 come prima, senza errori in console. Tutti i
   server avviati per la verifica si fermano.

## Revert

```bash
git revert -m 1 $(git log main --merges --grep="^Merge branch 'todo_40'$" --format=%H -1)
```

Effetti fuori dal repo: nessuno. Dopo il revert serve un `uv sync` perche'
la `.venv` riabbia streamlit.

Dopo il revert, rifare il merge di `todo_40` non riporta le modifiche (git le
considera gia' unite): per riaverle serve il revert del revert.
