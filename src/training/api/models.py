"""I modelli delle risposte dell'API.

Sono il contratto con il frontend: dall'OpenAPI che FastAPI ne ricava si
generano i tipi TypeScript. Per questo i nomi dei campi sono quelli delle
colonne di `activities` e `records`, e le descrizioni sono in inglese.

Un valore che manca e' `null`, mai `NaN` e mai `0`: la conversione la fa
chi costruisce il modello (`app.py`). Gli interi con buchi (`avg_heart_rate`)
arrivano da pandas come float, e qui sono `int | None`."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# I terreni di `interface/terrain.TERRAINS`, nello stesso ordine.
Terrain = Literal["track", "road", "gravel", "trail", "mountain"]
# I tipi di corsa di `interface/run_type.RUN_TYPES`, nello stesso ordine.
RunType = Literal["race", "intervals", "long", "tempo", "easy"]


class Activity(BaseModel):
    """One activity, as stored in the `activities` table."""

    activity_id: int
    sport: str | None
    sub_sport: str | None
    start_time: datetime = Field(description="Local time, no time zone.")
    activity_name: str | None
    total_distance_km: float | None
    total_time_min: float | None = Field(description="Elapsed time, pauses included.")
    total_ascent_m: float | None
    total_descent_m: float | None
    avg_speed_kmh: float | None = Field(description="Average speed over moving time.")
    equiv_speed_kmh: float | None = Field(description="Average grade-adjusted speed (on-foot sports).")
    avg_heart_rate: int | None
    max_heart_rate: int | None
    total_calories: int | None
    vo2max: float | None
    aerobic_te: float | None = Field(description="Garmin's aerobic Training Effect, 0-5.")
    anaerobic_te: float | None = Field(description="Garmin's anaerobic Training Effect, 0-5.")
    terrain: Terrain | None = Field(
        description="Terrain of on-foot activities: the user's choice, or else a guess. Null for other sports."
    )
    terrain_source: Literal["guess", "user"] | None = Field(
        description="Whether `terrain` is a guess or set by the user. Null when there is no terrain."
    )
    run_type: RunType | None = Field(
        description="Type of a run (race, intervals, long, tempo, easy): the user's choice, or else a guess "
        "from the planned workout and the duration. Null for sports other than running."
    )
    run_type_source: Literal["guess", "user"] | None = Field(
        description="Whether `run_type` is a guess or set by the user. Null when there is no run type."
    )


class RunTypeUpdate(BaseModel):
    """The run type chosen by the user for one run."""

    run_type: RunType | None = Field(description="Null clears the choice and goes back to the guess.")


class TerrainUpdate(BaseModel):
    """The terrain chosen by the user for one activity."""

    terrain: Terrain | None = Field(description="Null clears the choice and goes back to the guess.")


class EffectSeconds(BaseModel):
    """Seconds spent in each training effect, estimated from heart rate."""

    low_aerobic_s: float
    high_aerobic_s: float
    anaerobic_s: float


class ActivityDetail(Activity):
    """One activity with its heart-rate settings and estimated effects."""

    hr_zone_bounds: list[int] | None = Field(description="Upper limits of zones Z1-Z4, in bpm.")
    threshold_hr: int | None = Field(description="Anaerobic threshold, in bpm.")
    effect_seconds: EffectSeconds | None = Field(
        description="Null when the zones, the threshold or the heart rate are missing."
    )


class ChartBin(BaseModel):
    """One 30-second interval of the activity chart. Times in minutes from the start."""

    start: float
    end: float
    minute: float = Field(description="Middle of the interval.")
    hr: float | None
    speed: float | None = Field(description="Speed, smoothed over 30 s, in km/h.")
    equiv: float | None = Field(description="Grade-adjusted speed, in km/h.")
    slope_pct: float | None
    slope_deg: float | None


class ZoneBand(BaseModel):
    """A stretch of time in one heart-rate zone. Times in minutes from the start."""

    start: float
    end: float
    zone: int = Field(description="Heart-rate zone, 1-5.")
    hr: float = Field(description="Average heart rate in the band, in bpm.")


class Pause(BaseModel):
    """A pause in the recording. Times in minutes from the start."""

    start: float
    end: float


class ChartData(BaseModel):
    """The data behind the activity chart, for clients that draw it themselves."""

    bins: list[ChartBin]
    zone_bands: list[ZoneBand]
    pauses: list[Pause]
    hr_zone_bounds: list[int] | None
    threshold_hr: int | None


class Route(BaseModel):
    """The GPS track of an activity."""

    points: list[tuple[float, float]] = Field(description="[lat, lon] pairs, in recording order.")


class ReportSection(BaseModel):
    title: str | None = Field(description="Null for the text before the first section.")
    body: str = Field(description="Markdown.")
    icon: str | None = Field(description="Icon file name, served under /icons. Null when the section has none.")


class Report(BaseModel):
    """A written daily report, split into its sections."""

    day: date
    sections: list[ReportSection]


class Sport(BaseModel):
    """A sport found in the activities."""

    sport: str = Field(description="The key used in `Activity.sport`.")
    label: str = Field(description="The name to show.")
    icon: str | None = Field(description="Icon file name, served under /icons.")


class SportList(BaseModel):
    """The sports found in the activities, and the icon for rest days."""

    sports: list[Sport]
    rest_icon: str = Field(description="Icon file name for days without activities, served under /icons.")


# I fatti del giorno (`/api/daily/{day}`), tipati per la Day in React (todo
# 34). Sono i campi di `daily_data.build_daily_data`: i nomi e la forma non si
# cambiano qui, si descrivono. `sessions` e `hr_zones` restano senza tipo
# perche' la pagina non li usa (le attivita' le prende da `/api/activities`).
#
# Alcuni modelli hanno un campo `date`: dentro la classe il nome copre il
# tipo, per questo il tipo li' si chiama `Date`.
Date = date


class Mean(BaseModel):
    """An average over a window, with the number of days it is made of."""

    mean: float | None = Field(description="Null when no day in the window has a value.")
    days: int


class Measure(BaseModel):
    """One morning measure, with its 7- and 28-day averages."""

    value: float | None
    date: Date = Field(description="The day the value is read from.")
    avg_7d: Mean
    avg_28d: Mean
    delta_vs_28d: float | None


class Range(BaseModel):
    low: float
    high: float


class Morning(BaseModel):
    """Recovery and health measures of the morning. Stress and the body battery low are the
    day before's; everything else is the night/morning of the day."""

    readiness: Measure
    resting_hr: Measure
    hrv_last_night: Measure
    hrv_weekly_avg: Measure
    resp_sleep: Measure
    sleep_hours: Measure
    sleep_score: Measure
    stress_avg_yesterday: Measure
    body_battery_morning: Measure
    body_battery_low_yesterday: Measure
    spo2_avg: Measure
    hrv_status: str | None = Field(description="Garmin's word for the HRV status.")
    hrv_baseline: Range | None = Field(description="Garmin's balanced HRV range, in ms.")


class SleepLast7(BaseModel):
    hours: dict[date, float | None] = Field(description="Hours of sleep, night by night.")
    short_nights: int = Field(description="Nights under 7 h.")
    nights_measured: int


class Alert(BaseModel):
    """A warning sign, with its own numbers in extra fields."""

    model_config = ConfigDict(extra="allow")

    kind: str
    detail: str


class LoadNow(BaseModel):
    """Garmin's training load as of one day."""

    as_of: date
    load_acute: float | None
    load_chronic: float | None
    acwr: float | None
    acwr_status: str | None
    training_status: float | None
    training_status_phrase: str | None
    load_aerobic_low: float | None = Field(description="Monthly load, low aerobic.")
    load_aerobic_high: float | None = Field(description="Monthly load, high aerobic.")
    load_anaerobic: float | None = Field(description="Monthly load, anaerobic.")
    load_balance_phrase: str | None


class TargetRange(BaseModel):
    min: float
    max: float


class LoadTargets(BaseModel):
    """Garmin's target ranges for the monthly load of each effect."""

    load_aerobic_low: TargetRange
    load_aerobic_high: TargetRange
    load_anaerobic: TargetRange


class Vo2maxChange(BaseModel):
    now: float
    days_ago_28: float
    change: float


class Load(BaseModel):
    now: LoadNow | None
    targets: LoadTargets | None = Field(description="Null when the health files have no targets.")
    week_ago: LoadNow | None
    vo2max_change: Vo2maxChange | None = Field(description="Only when VO2max moved by 0.5 or more in 28 days.")


class Vo2maxNow(BaseModel):
    """The latest VO2max up to the day, shown even when it did not move."""

    now: float
    as_of: date = Field(description="The day Garmin measured it.")
    days_ago_28: float | None = Field(description="Null when there is no value 28 days before.")
    change: float | None = Field(description="Null when there is no value 28 days before.")


class ScoreNow(BaseModel):
    """The latest Garmin score up to the day (endurance or hill), shown even when it did not move."""

    now: int
    as_of: date = Field(description="The day of the health file it is read from.")
    days_ago_28: int | None = Field(description="Null when there is no value 28 days before.")
    change: int | None = Field(description="Null when there is no value 28 days before.")


class EnduranceNow(ScoreNow):
    level: str | None = Field(
        description="Garmin's level for the score (Recreational, Intermediate, Trained, Well-trained, "
        "Expert, Superior, Elite), from the limits in the same answer."
    )


class ThresholdHr(BaseModel):
    """The threshold heart rate saved by the watch in the latest on-foot activity with zones."""

    value: int = Field(description="In bpm.")
    as_of: date = Field(description="The day of the activity it is read from.")


class LactateThreshold(BaseModel):
    """Garmin's latest running lactate threshold. Only the latest one is known, so it is shown
    from the day it was detected on."""

    heart_rate: int | None = Field(description="In bpm.")
    speed_kmh: float | None
    pace_s_per_km: int | None = Field(description="Seconds per km, from the speed.")
    as_of: date = Field(description="The day Garmin detected it.")


class Fitness(BaseModel):
    """What the athlete can do, changing slowly over weeks (the Fitness card, todos 37 and 38).
    Only in the API: the daily report's JSON does not have it."""

    vo2max: Vo2maxNow | None = Field(description="Null when there is no VO2max up to the day.")
    endurance: EnduranceNow | None = Field(description="Garmin's endurance score. Null when there is none up to the day.")
    hill: ScoreNow | None = Field(description="Garmin's hill score. Null when there is none up to the day.")
    lactate_threshold: LactateThreshold | None = Field(
        description="Null before the day it was detected, or when it has not been downloaded."
    )
    threshold_hr: ThresholdHr | None = Field(
        description="Same as `hr_zones.threshold_hr`. Null when no activity has a valid threshold."
    )


class DayActivities(BaseModel):
    date: Date
    weekday: str
    activities: list[str] = Field(description='One line per activity, e.g. "running 8.1 km".')


class RecentActivity(BaseModel):
    date: Date
    sport: str | None
    distance_km: float | None
    duration_min: float | None
    aerobic_te: float | None
    anaerobic_te: float | None


class Recent(BaseModel):
    """The days before the day. Counts ignore what was done on the day itself."""

    trained_today: bool
    last_activity_before_today: date | None
    days_since_last_activity_before_today: int | None
    last_hard_session_before_today: date | None
    days_since_last_hard_session_before_today: int | None
    hard_session_rule: str
    rest_days_last_7: int
    consecutive_training_days_before_today: int
    consecutive_rest_days_before_today: int
    last_7_days: list[DayActivities]
    activities_last_14_days: list[RecentActivity]


class DailyData(BaseModel):
    """Everything known about one day, as built for the daily report."""

    day: date
    weekday: str
    health_data_up_to: date | None
    morning: Morning
    sleep_minutes: int | None = Field(
        description="Last night's sleep in whole minutes (sleep_hours is rounded to 0.1 h)."
    )
    sleep_last_7: SleepLast7
    alerts: list[Alert] = Field(description="Empty when there are no warning signs.")
    load: Load
    sessions: dict[str, Any]
    recent: Recent
    hr_zones: dict[str, Any] | None
    missing: list[str]
    fitness: Fitness
