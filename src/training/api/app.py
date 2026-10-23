"""L'API della pagina Day (todo 32). Tutto in sola lettura (`GET`), tranne il
terreno di un'attivita' a piedi (`PUT`, todo 35), il tipo di una corsa
(`PUT`, todo 36) e il tasto Refresh (`POST`, todo 41), che aggiorna i dati e
riscrive un report.

Lancio: `make api` (solo su 127.0.0.1: non c'e' ancora il login, e sono dati
di salute). La documentazione interattiva e' su `/docs`.

Gli endpoint sono sincroni: i calcoli (`db`, `run_chart`, `daily_data`) sono
codice bloccante, e FastAPI li serve su un pool di thread."""

import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from training.api import refresh
from training.api.cache import invalidate, load_activities, load_health
from training.api.context import ICONS_DIR, REPO_ROOT, UserContext, get_user_context
from training.api.daily import daily_payload
from training.api.sections import SECTIONS
from training.api.models import (
    Activity,
    ActivityDetail,
    ChartBin,
    ChartData,
    DailyData,
    EffectSeconds,
    Pause,
    RefreshStatus,
    Report,
    ReportSection,
    Route,
    RunTypeUpdate,
    Sport,
    SportList,
    TerrainUpdate,
    WeeklyData,
    ZoneBand,
)
from training.interface.daily_data import build_daily_data, fitness_on
from training.interface.weekly_data import build_weekly_data
from training.interface.db import _clean, load_activity_records
from training.interface.health import load_lactate_threshold
from training.interface.report_text import parse_report, section_icon
from training.interface.run_chart import (
    EFFECTS,
    bins,
    effects,
    has_effects,
    pauses,
    run_analysis_chart,
    week_sports_chart,
    zone_bands,
    zone_settings,
)
from training.interface.run_type import save_run_type_override
from training.interface.sports import REST_ICON_FILE, SPORT_ICON_FILES, has_distance, sport_label
from training.interface.terrain import save_terrain_override

# I giorni prima di `end` quando `start` non c'e': quattro settimane, `end`
# compreso.
DEFAULT_WINDOW_DAYS = 27

app = FastAPI(
    title="Training API",
    description=(
        "Read-only access to activities, charts, daily data and daily reports. "
        "The only writes are the terrain of an on-foot activity, the type of a run "
        "and the Refresh job, which downloads new data and rewrites a daily report."
    ),
    version="0.1.0",
)

Context = Annotated[UserContext, Depends(get_user_context)]

# Le icone degli sport e delle sezioni dei report, in sola lettura: le
# risposte danno solo il nome del file, e il frontend lo chiede qui.
app.mount("/icons", StaticFiles(directory=ICONS_DIR), name="icons")


def _records_dicts(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    """Le righe di `frame`, solo `columns`, con `None` al posto di `NaN`."""
    return [{col: _clean(row[col]) for col in columns} for _, row in frame.iterrows()]


# Quello che la pagina non deve vedere degli sport senza distanza (todo 45):
# la distanza che il polso ha stimato e tutto quello che ne discende. Il
# database le tiene, cosi' se un giorno arriva un sensore calibrato il dato
# vecchio e' ancora li'; la pagina al loro posto mostra le calorie.
_DISTANCE_FIELDS = ("total_distance_km", "avg_speed_kmh", "equiv_speed_kmh")


def _activity_fields(row: pd.Series) -> dict[str, Any]:
    fields = {name: _clean(row[name]) for name in Activity.model_fields if name != "start_time"}
    fields["start_time"] = row["start_time"].to_pydatetime()
    if not has_distance(row["sport"]):
        fields.update(dict.fromkeys(_DISTANCE_FIELDS))
    return fields


def _activity_row(activity_id: int, ctx: UserContext) -> pd.Series:
    """La riga di `list_activities` dell'attivita', o 404."""
    activities = load_activities(ctx.data_dir)
    match = activities[activities["activity_id"] == activity_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found.")
    return match.iloc[0]


@app.get("/api/activities", response_model=list[Activity], summary="List activities")
def get_activities(
    ctx: Context,
    start: Annotated[date | None, Query(description="First day, included. Default: 27 days before `end`.")] = None,
    end: Annotated[date | None, Query(description="Last day, included. Default: today.")] = None,
    sport: Annotated[list[str] | None, Query(description="Keep only these sports. Repeatable.")] = None,
) -> list[Activity]:
    """Activities whose start day falls between `start` and `end`, most recent first."""
    end = end or date.today()
    start = start or end - timedelta(days=DEFAULT_WINDOW_DAYS)
    if start > end:
        raise HTTPException(status_code=422, detail="`start` must not be after `end`.")
    activities = load_activities(ctx.data_dir)
    days = activities["start_time"].dt.date
    selected = activities[(days >= start) & (days <= end)]
    if sport:
        selected = selected[selected["sport"].isin(sport)]
    selected = selected.sort_values("start_time", ascending=False)
    return [Activity(**_activity_fields(row)) for _, row in selected.iterrows()]


@app.get("/api/sports", response_model=SportList, summary="List sports")
def get_sports(ctx: Context) -> SportList:
    """The sports found in the activities, sorted by key, with their label and icon."""
    activities = load_activities(ctx.data_dir)
    return SportList(
        sports=[
            Sport(sport=sport, label=sport_label(sport), icon=SPORT_ICON_FILES.get(sport))
            for sport in sorted(activities["sport"].dropna().unique())
        ],
        rest_icon=REST_ICON_FILE,
    )


@app.get("/api/activities/{activity_id}", response_model=ActivityDetail, summary="Activity detail")
def get_activity(activity_id: int, ctx: Context) -> ActivityDetail:
    """One activity, with its heart-rate zones, threshold and estimated time per training effect."""
    row = _activity_row(activity_id, ctx)
    bounds, threshold = zone_settings(row)
    effect_seconds = None
    if has_effects(bounds, threshold):
        records = load_activity_records(activity_id, ctx.data_dir)
        if not records.empty and records["heart_rate"].notna().any():
            seconds = effects(records, bounds, threshold)
            effect_seconds = EffectSeconds(
                low_aerobic_s=seconds[EFFECTS[0]],
                high_aerobic_s=seconds[EFFECTS[1]],
                anaerobic_s=seconds[EFFECTS[2]],
            )
    return ActivityDetail(
        **_activity_fields(row),
        hr_zone_bounds=bounds,
        threshold_hr=threshold,
        effect_seconds=effect_seconds,
    )


@app.put("/api/activities/{activity_id}/terrain", response_model=Activity, summary="Set the terrain")
def put_activity_terrain(activity_id: int, update: TerrainUpdate, ctx: Context) -> Activity:
    """Set the terrain of an on-foot activity, or clear it with `null` to go back to the guess.

    422 for activities without a terrain (sports other than running, walking and hiking,
    and treadmill runs)."""
    row = _activity_row(activity_id, ctx)
    if _clean(row["terrain_source"]) is None:
        raise HTTPException(status_code=422, detail=f"Activity {activity_id} has no terrain.")
    save_terrain_override(ctx.data_dir, activity_id, update.terrain)
    invalidate(ctx.data_dir)
    return Activity(**_activity_fields(_activity_row(activity_id, ctx)))


@app.put("/api/activities/{activity_id}/run_type", response_model=Activity, summary="Set the run type")
def put_activity_run_type(activity_id: int, update: RunTypeUpdate, ctx: Context) -> Activity:
    """Set the type of a run, or clear it with `null` to go back to the guess.

    422 for activities that are not runs."""
    row = _activity_row(activity_id, ctx)
    if _clean(row["run_type_source"]) is None:
        raise HTTPException(status_code=422, detail=f"Activity {activity_id} is not a run.")
    save_run_type_override(ctx.data_dir, activity_id, update.run_type)
    invalidate(ctx.data_dir)
    return Activity(**_activity_fields(_activity_row(activity_id, ctx)))


@app.get("/api/activities/{activity_id}/chart", response_model=ChartData, summary="Activity chart data")
def get_activity_chart(activity_id: int, ctx: Context) -> ChartData:
    """The data of the activity chart: 30-second bins, heart-rate zone bands and pauses.

    Empty lists when the activity has no sampled data."""
    row = _activity_row(activity_id, ctx)
    bounds, threshold = zone_settings(row)
    records = load_activity_records(activity_id, ctx.data_dir)
    if records.empty:
        return ChartData(bins=[], zone_bands=[], pauses=[], hr_zone_bounds=bounds, threshold_hr=threshold)
    bands = zone_bands(records, bounds) if bounds else pd.DataFrame()
    return ChartData(
        bins=[ChartBin(**r) for r in _records_dicts(bins(records), list(ChartBin.model_fields))],
        zone_bands=[ZoneBand(**r) for r in _records_dicts(bands, list(ZoneBand.model_fields))],
        pauses=[Pause(start=a, end=b) for a, b in pauses(records)],
        hr_zone_bounds=bounds,
        threshold_hr=threshold,
    )


@app.get("/api/activities/{activity_id}/chart/vega", summary="Activity chart, Vega-Lite")
def get_activity_chart_vega(
    activity_id: int,
    ctx: Context,
    theme: Literal["light", "dark"] = "light",
) -> dict[str, Any]:
    """The activity chart as a ready-to-render Vega-Lite specification."""
    row = _activity_row(activity_id, ctx)
    bounds, threshold = zone_settings(row)
    records = load_activity_records(activity_id, ctx.data_dir)
    chart = run_analysis_chart(records, bounds, threshold, theme, _clean(row["sport"]))
    if chart is None:
        raise HTTPException(status_code=404, detail="Nothing to plot for this activity.")
    return chart.to_dict()


@app.get("/api/activities/{activity_id}/route", response_model=Route, summary="Activity route")
def get_activity_route(
    activity_id: int,
    ctx: Context,
    max_points: Annotated[int, Query(ge=2, description="Upper limit on the number of points.")] = 2000,
) -> Route:
    """The GPS track as [lat, lon] pairs. Longer tracks keep one point every N, always
    including the first and the last. Empty when the activity has no position."""
    _activity_row(activity_id, ctx)
    records = load_activity_records(activity_id, ctx.data_dir)
    if records.empty:
        return Route(points=[])
    points = records[["lat", "lon"]].dropna().to_numpy()
    if len(points) > max_points:
        step = math.ceil((len(points) - 1) / (max_points - 1))
        keep = list(range(0, len(points) - 1, step)) + [len(points) - 1]
        points = points[np.array(keep)]
    return Route(points=[(float(lat), float(lon)) for lat, lon in points])


@app.get("/api/daily/{day}", response_model=DailyData, summary="Daily data")
def get_daily(day: date, ctx: Context) -> DailyData:
    """Everything known about one day (training, recovery, health, load), as built for the
    daily report."""
    if day > date.today():
        raise HTTPException(status_code=422, detail=f"{day} is in the future.")
    # Gli stessi fatti che l'orchestratore del Refresh mette nel file degli
    # agenti: una strada sola, cosi' la pagina e chi scrive il testo vedono
    # le stesse cose.
    return DailyData(**daily_payload(day, ctx.data_dir))


def _weekly(monday: date, data_dir: Path) -> dict[str, Any]:
    """I fatti della settimana, con salute e attivita' dalla cache: senza,
    ogni richiesta rifa' la scansione dei file di salute (circa un secondo,
    dieci volte il conto della settimana)."""
    return build_weekly_data(
        monday,
        data_dir,
        activities=load_activities(data_dir),
        health=load_health(data_dir),
    )


@app.get("/api/weekly/{monday}", response_model=WeeklyData, summary="Weekly data")
def get_weekly(monday: date, ctx: Context) -> WeeklyData:
    """Everything known about one ISO week, Monday to Sunday (todo 52).

    The Health and Recovery measures are averages of the seven days, each with the band it
    has moved in over the last twelve weeks; load and fitness are the state at the end of
    the week, which is today for a week still running."""
    if monday.weekday() != 0:
        raise HTTPException(status_code=422, detail=f"{monday} is not a Monday.")
    if monday > date.today():
        raise HTTPException(status_code=422, detail=f"The week of {monday} has not started.")
    data = _weekly(monday, ctx.data_dir)
    return WeeklyData(**{name: data[name] for name in WeeklyData.model_fields})


@app.get("/api/weekly/{monday}/chart/vega", summary="Weekly chart, Vega-Lite")
def get_weekly_chart_vega(
    monday: date,
    ctx: Context,
    theme: Literal["light", "dark"] = "light",
) -> dict[str, Any]:
    """The week's work by sport, as a ready-to-render Vega-Lite specification."""
    if monday.weekday() != 0:
        raise HTTPException(status_code=422, detail=f"{monday} is not a Monday.")
    data = _weekly(monday, ctx.data_dir)
    chart = week_sports_chart(data["training"]["by_sport"], theme)
    if chart is None:
        raise HTTPException(status_code=404, detail="No sessions to plot for this week.")
    return chart.to_dict()


def _fragment_sections(folder: Path) -> list[tuple[str | None, str, datetime | None]]:
    """Le sezioni dai frammenti di una cartella (todo 44): un file per
    sezione, nell'ordine in cui si leggono.

    **Le sezioni ci sono tutte, anche quelle senza frammento**, con il corpo
    vuoto. Il file manca quando il suo agente non ha ancora scritto o e'
    fallito, e quella e' una card senza testo, non una card senza nome: la
    pagina prende da qui anche il titolo e l'icona di ogni riquadro, e
    saltando la sezione le toglieva tutte e due. Si vedeva rifacendo una
    sola card su un giorno mai scritto: restava la sua, e le altre sei
    perdevano l'icona.

    Di ognuna si da' anche quando e' stata scritta, cioe' l'`mtime` del suo
    file: dal todo 47 le sezioni di uno stesso giorno portano ore diverse,
    perche' il giro della mattina ne scrive alcune e quello della sera altre,
    e la pagina lo dice sotto ogni testo.

    Niente testo senza titolo: la riga "Data: ..." del file unico la scartava
    gia' `parse_report`, quindi alla pagina non e' mai arrivata."""
    found: list[tuple[str | None, str, datetime | None]] = []
    for section in SECTIONS:
        path = folder / f"{section.key}.md"
        body = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        written = datetime.fromtimestamp(path.stat().st_mtime) if body else None
        found.append((section.title, body, written))
    return found


@app.get("/api/reports/daily/{day}", response_model=Report, summary="Daily report")
def get_daily_report(day: date, ctx: Context) -> Report:
    """The written daily report of `day`, split into its sections.

    Dal todo 44 ogni sezione e' un file suo in `01.daily/<giorno>/`, scritto
    dal suo agente. I giorni di prima hanno il file unico `<giorno>.md`, e si
    continuano a leggere da li'."""
    folder = ctx.summary_dir / "01.daily" / day.isoformat()
    path = ctx.summary_dir / "01.daily" / f"{day.isoformat()}.md"
    if folder.is_dir():
        found = _fragment_sections(folder)
    elif path.exists():
        # Il file unico l'ha scritto un agente solo, in una volta: le sue
        # sezioni portano tutte l'ora del file.
        written = datetime.fromtimestamp(path.stat().st_mtime)
        found = [(title, body, written) for title, body in parse_report(path)]
    else:
        raise HTTPException(status_code=404, detail=f"No daily report for {day}.")
    # Una cartella che esiste ma non ha ancora un frammento scritto vale come
    # un report che non c'e': le sezioni vuote da sole non sono un report.
    if not any(body for _, body, _written in found):
        raise HTTPException(status_code=404, detail=f"No daily report for {day}.")
    sections = [
        ReportSection(
            title=title,
            body=body,
            icon=section_icon(title) if title else None,
            written_at=written,
        )
        for title, body, written in found
    ]
    return Report(day=day, sections=sections)


@app.post(
    "/api/reports/daily/{day}/refresh",
    response_model=RefreshStatus,
    status_code=202,
    summary="Refresh data and rewrite the whole daily report",
)
def post_daily_refresh(day: date, ctx: Context) -> RefreshStatus:
    """Download new data from Garmin and rewrite every section of the daily report of
    `day`, in the background: one agent per section, one after another, so a few minutes.
    One job at a time: while one runs, this returns it and starts nothing. Follow it with
    `GET /api/refresh`."""
    if day > date.today():
        raise HTTPException(status_code=422, detail=f"{day} is in the future.")
    return RefreshStatus(**refresh.start(day, REPO_ROOT, ctx.summary_dir, ctx.data_dir))


@app.post(
    "/api/reports/daily/{day}/refresh/{section}",
    response_model=RefreshStatus,
    status_code=202,
    summary="Rewrite one section of the daily report",
)
def post_daily_refresh_section(day: date, section: str, ctx: Context) -> RefreshStatus:
    """Rewrite a single section: only its agent runs, the other sections keep the text they
    have. 422 for a section that does not exist."""
    if day > date.today():
        raise HTTPException(status_code=422, detail=f"{day} is in the future.")
    try:
        keys = refresh.section_keys(section)
    except KeyError:
        known = ", ".join(s.key for s in SECTIONS)
        raise HTTPException(status_code=422, detail=f"Unknown section {section!r}. Known: {known}.")
    return RefreshStatus(**refresh.start(day, REPO_ROOT, ctx.summary_dir, ctx.data_dir, keys))


@app.get("/api/refresh", response_model=RefreshStatus, summary="Refresh job status")
def get_refresh() -> RefreshStatus:
    """The state of the latest Refresh job."""
    return RefreshStatus(**refresh.status())
