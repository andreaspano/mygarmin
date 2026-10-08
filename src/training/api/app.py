"""L'API di sola lettura per la pagina Day (todo 32).

Lancio: `make api` (solo su 127.0.0.1: non c'e' ancora il login, e sono dati
di salute). La documentazione interattiva e' su `/docs`.

Gli endpoint sono sincroni: i calcoli (`db`, `run_chart`, `daily_data`) sono
codice bloccante, e FastAPI li serve su un pool di thread."""

import math
from datetime import date, timedelta
from typing import Annotated, Any, Literal

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query

from training.api.cache import load_activities
from training.api.context import UserContext, get_user_context
from training.api.models import (
    Activity,
    ActivityDetail,
    ChartBin,
    ChartData,
    EffectSeconds,
    Pause,
    Report,
    ReportSection,
    Route,
    ZoneBand,
)
from training.interface.daily_data import build_daily_data
from training.interface.db import _clean, load_activity_records
from training.interface.report_text import parse_report
from training.interface.run_chart import (
    EFFECTS,
    bins,
    effects,
    has_effects,
    pauses,
    run_analysis_chart,
    zone_bands,
    zone_settings,
)

# I giorni prima di `end` quando `start` non c'e': quattro settimane, `end`
# compreso.
DEFAULT_WINDOW_DAYS = 27

app = FastAPI(
    title="Training API",
    description="Read-only access to activities, charts, daily data and daily reports.",
    version="0.1.0",
)

Context = Annotated[UserContext, Depends(get_user_context)]


def _records_dicts(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    """Le righe di `frame`, solo `columns`, con `None` al posto di `NaN`."""
    return [{col: _clean(row[col]) for col in columns} for _, row in frame.iterrows()]


def _activity_fields(row: pd.Series) -> dict[str, Any]:
    fields = {name: _clean(row[name]) for name in Activity.model_fields if name != "start_time"}
    fields["start_time"] = row["start_time"].to_pydatetime()
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
    chart = run_analysis_chart(records, bounds, threshold, theme)
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


@app.get("/api/daily/{day}", summary="Daily data")
def get_daily(day: date, ctx: Context) -> dict[str, Any]:
    """Everything known about one day (training, recovery, health, load), as built for the
    daily report. Not yet typed field by field: the shape is still changing."""
    if day > date.today():
        raise HTTPException(status_code=422, detail=f"{day} is in the future.")
    return build_daily_data(day, ctx.data_dir)


@app.get("/api/reports/daily/{day}", response_model=Report, summary="Daily report")
def get_daily_report(day: date, ctx: Context) -> Report:
    """The written daily report of `day`, split into its sections."""
    path = ctx.summary_dir / "01.daily" / f"{day.isoformat()}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No daily report for {day}.")
    return Report(day=day, sections=[ReportSection(title=t, body=b) for t, b in parse_report(path)])
