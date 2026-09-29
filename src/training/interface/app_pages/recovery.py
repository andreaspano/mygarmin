"""Recovery page: how the body is taking the training load, day by day.

Le altre pagine guardano quello che si e' fatto (Day, Week, Month); questa
guarda quello che il corpo ne ha fatto. I dati arrivano dai JSON di salute
(`interface/health.py`), non da SQLite: non passano dai file FIT e non hanno
niente da spartire con le attivita', tranne l'asse del tempo.

L'asse del tempo e' pero' il punto: i grafici stanno uno sopra l'altro in un
`vconcat`, con in fondo i minuti di allenamento del giorno. Un crollo della
readiness sopra una barra alta il giorno prima si spiega da solo; gli stessi
due grafici in due posti diversi non spiegherebbero niente.
"""

import altair as alt
import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.data import load_activities, load_health_metrics
from training.interface.filters import date_range

# Larghezza fissa, per la stessa ragione spiegata in cima a `period_page.py` e
# con lo stesso numero: i pannelli devono stare in una vista Vega sola perche'
# l'asse x sia davvero lo stesso e restino allineati, cioe' in un `vconcat`, e
# un `concat` non si adatta al contenitore (l'`autosize` di Vega-Lite vale solo
# per una vista singola). Provato `width="stretch"`: il frontend passa ai figli
# la larghezza misurata del contenitore, ma per un `concat` quella e' l'area di
# disegno, e il totale usciva 1239px in un contenitore da 1074 — sbordava a
# destra. Qui si toglie in anticipo quello che Vega aggiunge intorno.
#
# Il numero non e' importato da `period_page.py`: quel modulo e' la macchina
# delle pagine a periodi, e questa pagina non ne usa nient'altro.
PANEL_TOTAL_WIDTH = 914
_AXIS_WIDTH = 55  # l'asse y, fuori dall'area di disegno
_VEGA_PADDING = 94  # margini interni e titolo dell'asse y
PANEL_WIDTH = PANEL_TOTAL_WIDTH - _AXIS_WIDTH - _VEGA_PADDING

CHART_HEIGHT = 130
# Il sonno e' l'unico con le barre e una legenda a colori: gli serve piu' aria.
SLEEP_HEIGHT = 150

# Verde-giallo-rosso al contrario: 100 e' buono. `domain` fisso da 0 a 100 e
# non sui valori presenti, cosi' lo stesso colore vuol dire lo stesso punteggio
# cambiando periodo.
SLEEP_SCORE_SCHEME = "redyellowgreen"
SLEEP_SCORE_DOMAIN = [0, 100]

READINESS_COLOR = "#4c78a8"
BODY_BATTERY_COLOR = "#72b7b2"
HRV_COLOR = "#b279a2"
HRV_AVG_COLOR = "#9d755d"
RESTING_HR_COLOR = "#e45756"
LOAD_COLOR = "#f97316"


def _hours_label(hours: float | None) -> str:
    """Le ore di sonno come "7h14", non come 7,23."""
    if hours is None or pd.isna(hours):
        return "-"
    whole = int(hours)
    return f"{whole}h{int(round((hours - whole) * 60)):02d}"


def _delta(today: float | None, yesterday: float | None, unit: str = "") -> str | None:
    """La differenza rispetto al giorno prima, o None se manca un pezzo.

    None e non zero: senza il giorno prima non si sa se e' salito o sceso, e
    uno zero direbbe "uguale a ieri", che e' un'altra affermazione."""
    if today is None or yesterday is None or pd.isna(today) or pd.isna(yesterday):
        return None
    return f"{today - yesterday:+.0f}{unit}"


def _value(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    return None if value is None or pd.isna(value) else float(value)


st.title("Recovery")

activities = load_activities(DATA_DIR)
health = load_health_metrics(DATA_DIR)

if activities.empty:
    st.info(f"No *_ACTIVITY.fit file found in {DATA_DIR.resolve()}.")
    st.stop()

# Gli estremi delle date vengono dalle attivita' e non dai giorni di salute,
# che oggi sono molto meno (le attivita' partono da gennaio 2025, la salute da
# quando `fitness_status` ha iniziato a scaricarla). Cosi' si puo' scegliere
# anche un periodo senza dati e leggere il messaggio che lo dice, invece di
# trovarsi il calendario bloccato sull'unico mese disponibile.
start_date, end_date = date_range(
    activities,
    invalid_message="'From' is later than 'To': swap the two dates to see the metrics.",
    presets=True,
    period="weeks",
    key="recovery_range",
    # Quattro settimane e non dodici come la Week: qui i punti sono giornalieri
    # e tre mesi ne mettono novanta per riga, illeggibili.
    default_preset="4 weeks",
)

in_range = health[
    (health.index.date >= start_date) & (health.index.date <= end_date)
] if not health.empty else health

# Un giorno senza nessuna misura non e' un giorno da disegnare: `load_health()`
# riempie il calendario, e fuori dal periodo scaricato sarebbe tutto NaN.
measured = in_range.dropna(how="all") if not in_range.empty else in_range

if measured.empty:
    st.info("No health data in this period.")
    st.stop()

# I minuti di allenamento del giorno: la riga in fondo, e il motivo per cui
# una metrica scende. Solo i giorni con attivita' hanno una barra; gli altri
# non hanno un "zero", non hanno proprio niente da mostrare.
in_range_activities = activities[
    (activities["start_time"].dt.date >= start_date)
    & (activities["start_time"].dt.date <= end_date)
]
load_by_day = (
    in_range_activities.assign(day=in_range_activities["start_time"].dt.normalize())
    .groupby("day")["total_time_min"]
    .sum()
    .rename("load_min")
    .reset_index()
)

# ---------------------------------------------------------------- metriche
# L'ultimo giorno con almeno una misura, e quello prima per i delta.
last_day = measured.index[-1]
last = measured.loc[last_day]
previous = measured.iloc[-2] if len(measured) > 1 else pd.Series(dtype="float64")

st.caption(f"Latest day with data: {last_day:%d %b %Y}")

# I numeri grandi dentro un riquadro, come le schede per sport di Day, Week e
# Month: li' le metriche stanno in un `container(border=True)`, e senza bordo
# qui galleggiavano fra il titolo e i grafici senza farsi leggere come un
# blocco solo. La larghezza e' quella totale dei pannelli qui sotto e non
# "stretch": il riquadro e' l'intestazione di quei grafici, e un bordo che
# arriva piu' a destra di loro si vedrebbe che non lo e'.
metrics_row = st.container(horizontal=True, border=True, width=PANEL_TOTAL_WIDTH)

readiness = _value(last, "readiness")
metrics_row.metric(
    "Training readiness",
    f"{readiness:.0f}" if readiness is not None else "-",
    _delta(readiness, _value(previous, "readiness")),
    help="Garmin's readiness score at wake-up, 0-100.",
)

hrv = _value(last, "hrv_last_night")
hrv_avg = _value(last, "hrv_weekly_avg")
# Il delta dell'HRV non e' il giorno prima ma la media a 7 giorni: una notte
# sola oscilla parecchio, e quello che dice qualcosa e' se sta sopra o sotto la
# propria base. Per le altre metriche il confronto col giorno prima va bene.
metrics_row.metric(
    "HRV last night",
    f"{hrv:.0f} ms" if hrv is not None else "-",
    f"{hrv - hrv_avg:+.0f} vs 7-day avg" if hrv is not None and hrv_avg is not None else None,
    help="Overnight average heart rate variability, against its own 7-day average.",
)

resting_hr = _value(last, "resting_hr")
metrics_row.metric(
    "Resting HR",
    f"{resting_hr:.0f} bpm" if resting_hr is not None else "-",
    _delta(resting_hr, _value(previous, "resting_hr"), " bpm"),
    # Piu' basso e' meglio: senza questo la freccia verde direbbe il contrario.
    delta_color="inverse",
    help="Resting heart rate. Lower is better, so the arrow is reversed.",
)

sleep_hours = _value(last, "sleep_hours")
previous_sleep = _value(previous, "sleep_hours")
metrics_row.metric(
    "Sleep",
    _hours_label(sleep_hours),
    (
        f"{sleep_hours - previous_sleep:+.1f} h"
        if sleep_hours is not None and previous_sleep is not None
        else None
    ),
    help="Time asleep.",
)

sleep_score = _value(last, "sleep_score")
metrics_row.metric(
    "Sleep score",
    f"{sleep_score:.0f}" if sleep_score is not None else "-",
    _delta(sleep_score, _value(previous, "sleep_score")),
    help="Garmin's sleep score, 0-100.",
)

# ---------------------------------------------------------------- grafici
# I NaN restano NaN e non diventano zero: un giorno senza misura deve lasciare
# un buco, non un punto a fondo scala. Ci pensa il comportamento di default di
# Vega-Lite per le linee ("break-paths-filter-invalid-values"): il percorso si
# spezza sul valore mancante e riprende dopo. Da non forzare a `invalid=None`,
# che vuol dire l'opposto ("mostrali lo stesso"): provato, e i sette giorni
# senza orologio di inizio settembre finivano tutti appoggiati sul minimo
# dell'asse, cioe' un battito a riposo di 45 e un HRV di 40 mai misurati.
chart_data = measured.reset_index().rename(columns={"day": "date"})

# Lo stesso dominio per tutti i pannelli, scritto a mano invece di lasciarlo
# dedurre dai dati: la riga dei carichi ha giorni suoi (le attivita'), e senza
# un dominio comune finirebbe larga diversamente dalle altre.
X_DOMAIN = [chart_data["date"].min().isoformat(), chart_data["date"].max().isoformat()]
_x_scale = alt.Scale(domain=X_DOMAIN)

# Le tacche ogni due giorni, scritte e non lasciate scegliere a Vega: con i
# marchi a barre ne metteva meno che con le linee, e le stesse date finivano
# etichettate in modo diverso da un pannello all'altro. La scala e' la stessa e
# i pannelli restano allineati comunque, ma si leggono come un asse solo
# quando anche le etichette cadono negli stessi punti.
_X_TICKS = alt.TickCount(interval="day", step=2)


def _x(title: str | None = None) -> alt.X:
    return alt.X(
        "date:T",
        axis=alt.Axis(format="%d %b", title=title, grid=True, tickCount=_X_TICKS),
        scale=_x_scale,
    )


x_axis = _x()


def _panel(title: str, layers: list, height: int = CHART_HEIGHT) -> alt.LayerChart:
    return alt.layer(*layers).properties(
        width=PANEL_WIDTH, height=height, title=alt.TitleParams(title, anchor="start")
    )


readiness_panel = _panel(
    "Training readiness",
    [
        alt.Chart(chart_data)
        .mark_line(color=READINESS_COLOR, point=alt.OverlayMarkDef(size=25))
        .encode(
            x=x_axis,
            y=alt.Y("readiness:Q", title="score", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("readiness:Q", title="Readiness", format=".0f"),
            ],
        )
    ],
)

body_battery_panel = _panel(
    "Body battery",
    [
        alt.Chart(chart_data)
        .mark_area(color=BODY_BATTERY_COLOR, opacity=0.45)
        .encode(
            x=x_axis,
            y=alt.Y("body_battery_low:Q", title="0-100", scale=alt.Scale(domain=[0, 100])),
            y2="body_battery_high:Q",
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("body_battery_low:Q", title="Lowest", format=".0f"),
                alt.Tooltip("body_battery_high:Q", title="Highest", format=".0f"),
            ],
        )
    ],
)

hrv_panel = _panel(
    "HRV",
    [
        # La media a 7 giorni e' la linea, la notte sono i punti: la notte
        # salta, la media no, e messe insieme si vede quando una notte esce
        # dalla propria base.
        alt.Chart(chart_data)
        .mark_line(color=HRV_AVG_COLOR, strokeDash=[4, 3])
        .encode(x=x_axis, y=alt.Y("hrv_weekly_avg:Q", title="ms", scale=alt.Scale(zero=False))),
        alt.Chart(chart_data)
        .mark_point(color=HRV_COLOR, filled=True, size=35)
        .encode(
            x=x_axis,
            y=alt.Y("hrv_last_night:Q", title="ms", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("hrv_last_night:Q", title="Last night", format=".0f"),
                alt.Tooltip("hrv_weekly_avg:Q", title="7-day avg", format=".0f"),
                alt.Tooltip("hrv_status:N", title="Status"),
            ],
        ),
    ],
)

resting_hr_panel = _panel(
    "Resting heart rate",
    [
        alt.Chart(chart_data)
        .mark_line(color=RESTING_HR_COLOR, point=alt.OverlayMarkDef(size=25))
        .encode(
            x=x_axis,
            y=alt.Y("resting_hr:Q", title="bpm", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("resting_hr:Q", title="Resting HR", format=".0f"),
            ],
        )
    ],
)

sleep_panel = _panel(
    "Sleep",
    [
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=x_axis,
            y=alt.Y("sleep_hours:Q", title="h"),
            color=alt.Color(
                "sleep_score:Q",
                scale=alt.Scale(scheme=SLEEP_SCORE_SCHEME, domain=SLEEP_SCORE_DOMAIN),
                legend=alt.Legend(title="Sleep score"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("sleep_hours:Q", title="Hours", format=".2f"),
                alt.Tooltip("sleep_score:Q", title="Score", format=".0f"),
            ],
        )
    ],
    height=SLEEP_HEIGHT,
)

# I giorni di allenamento, in fondo e sullo stesso asse x: e' la riga che
# spiega le altre. Il dominio dell'asse e' quello dei giorni di salute anche
# qui, se no una settimana di sole attivita' allargherebbe questa riga e non le
# altre, e l'allineamento salterebbe.
load_panel = _panel(
    "Training load",
    [
        alt.Chart(load_by_day if not load_by_day.empty else pd.DataFrame({"day": [], "load_min": []}))
        .mark_bar(color=LOAD_COLOR, opacity=0.8)
        .encode(
            x=alt.X(
                "day:T",
                axis=alt.Axis(format="%d %b", title="day", grid=True, tickCount=_X_TICKS),
                scale=_x_scale,
            ),
            y=alt.Y("load_min:Q", title="min"),
            tooltip=[
                alt.Tooltip("day:T", title="Day", format="%d %b %Y"),
                alt.Tooltip("load_min:Q", title="Training", format=".0f"),
            ],
        )
    ],
)

charts = alt.vconcat(
    readiness_panel,
    body_battery_panel,
    hrv_panel,
    resting_hr_panel,
    sleep_panel,
    load_panel,
    spacing=8,
).resolve_scale(color="independent")

st.altair_chart(charts, width="content")

st.caption(
    "Training load is the total activity time of the day: the bottom row is why "
    "the rows above move."
)
