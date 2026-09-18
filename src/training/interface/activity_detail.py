"""Scheda di dettaglio di una singola attivita': metriche, commento, grafici
e traccia.

Sta qui e non nella pagina Activities perche' la stessa scheda si apre anche
dalla pagina Week, cliccando una riga della tabella delle attivita'."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from training.interface.activity_report import load_activity_comments
from training.interface.activity_table import sport_icons
from training.interface.db import load_activity_records

alt.data_transformers.disable_max_rows()

DATA_DIR = Path("data")


def _records(activity_id: int) -> pd.DataFrame:
    return load_activity_records(activity_id, DATA_DIR)


def _with_gap_breaks(df: pd.DataFrame, threshold: pd.Timedelta = pd.Timedelta(seconds=30)) -> pd.DataFrame:
    """Inserisce una riga nulla in corrispondenza dei buchi nei timestamp
    (es. una pausa di registrazione): senza interromperli, i grafici a
    linea/area unirebbero i due lati della pausa con una diagonale,
    disegnando un cambiamento (di FC, velocita', altitudine, ...) che non
    e' mai avvenuto. Vega-Lite interrompe la linea/area sui valori nulli."""
    gap = df.index.to_series().diff() > threshold
    if not gap.any():
        return df
    breaks = pd.DataFrame(index=df.index[gap] - pd.Timedelta(seconds=1), columns=df.columns)
    return pd.concat([df, breaks]).sort_index()


def _synced_series_chart(
    data: pd.DataFrame,
    hover: alt.Parameter,
    y_field: str,
    y_title: str,
    title: str,
    color: str,
    area: bool = False,
    y_scale: alt.Scale | None = None,
    smooth_field: str | None = None,
) -> alt.LayerChart:
    """Grafico temporale che partecipa a un crosshair verticale condiviso:
    passando lo stesso oggetto `hover` a piu' grafici e componendoli in un
    unico vconcat, il mouse su uno qualsiasi sposta la linea verticale (e il
    punto evidenziato) alla stessa ora su tutti, per confrontare facilmente
    FC/velocita'/altitudine nello stesso istante."""
    base = alt.Chart(data).encode(x=alt.X("timestamp:T", title="Time"))
    y_enc = alt.Y(f"{y_field}:Q", title=y_title, scale=y_scale) if y_scale else alt.Y(f"{y_field}:Q", title=y_title)

    series = (
        base.mark_area(line={"color": color}, color=color + "80", clip=True)
        if area
        else base.mark_line(color=color)
    ).encode(y=y_enc)

    layers = [series]
    if smooth_field:
        layers.append(
            base.mark_line(color="red", strokeWidth=2).encode(y=alt.Y(f"{smooth_field}:Q", title=y_title))
        )

    selectors = (
        base.mark_point(opacity=0)
        .encode(
            y=alt.Y(f"{y_field}:Q"),
            tooltip=[alt.Tooltip("timestamp:T", title="Time"), alt.Tooltip(f"{y_field}:Q", title=y_title)],
        )
        .add_params(hover)
    )
    rule = base.mark_rule(color="#9ca3af", strokeDash=[4, 4]).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )
    point = base.mark_point(color=color, size=60, filled=True).encode(
        y=y_enc, opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )
    layers.extend([selectors, rule, point])
    return alt.layer(*layers).properties(title=alt.TitleParams(title, anchor="start"))


def show_activity_detail(activity) -> None:
    """Disegna il dettaglio di `activity` (una riga di `list_activities`)."""
    records = _records(activity.activity_id)

    icon_col, header_col = st.columns([1, 6])

    with header_col:
        st.subheader(f"{activity.sport or '?'} — {activity.start_time:%d %b %Y, %H:%M}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Distance", f"{activity.total_distance_km:.1f} km")
        col2.metric("Duration", f"{activity.total_time_min:.0f} min")
        col3.metric("Avg HR", f"{activity.avg_heart_rate or '-'} bpm")
        col4.metric(
            "Elevation",
            f"+{activity.total_ascent_m:.0f} / -{activity.total_descent_m:.0f} m"
            if pd.notna(activity.total_ascent_m)
            else "-",
        )

    with icon_col:
        icon_uri = sport_icons().get(activity.sport)
        if icon_uri:
            st.markdown(
                f'<img src="{icon_uri}" style="width:100%;max-width:72px;margin-top:8px;">',
                unsafe_allow_html=True,
            )

    st.markdown("**Comment**")
    saved_comments = load_activity_comments(activity.activity_id)
    if saved_comments is None:
        st.info("Report not generated yet for this activity. Run `make activity_reports`.")
    else:
        for comment in saved_comments:
            st.markdown(f"- {comment}")

    if records.empty:
        st.warning("No sampled data (records) in this file.")
    else:
        chart_records = _with_gap_breaks(records)
        for col in ("heart_rate", "speed_kmh"):
            chart_records[f"{col}_smooth"] = chart_records[col].rolling("5min", min_periods=1, center=True).mean()

        altitude_diff_m = chart_records["altitude_m"].astype(float).diff()
        distance_diff_m = (chart_records["distance_km"].astype(float).diff() * 1000).mask(lambda s: s == 0)
        raw_slope_pct = (altitude_diff_m / distance_diff_m) * 100
        chart_records["slope_pct"] = raw_slope_pct.rolling("30s", min_periods=1, center=True).mean().clip(-30, 30)

        chart_data = chart_records.reset_index()
        hover = alt.selection_point(
            fields=["timestamp"], nearest=True, on="pointermove", empty=False, clear="pointerout"
        )

        top_charts = []
        if records["heart_rate"].notna().any():
            top_charts.append(
                _synced_series_chart(
                    chart_data,
                    hover,
                    "heart_rate",
                    "HR (bpm)",
                    "Heart rate",
                    "#60a5fa",
                    smooth_field="heart_rate_smooth",
                ).properties(width="container")
            )

        if records["speed_kmh"].notna().any():
            top_charts.append(
                _synced_series_chart(
                    chart_data,
                    hover,
                    "speed_kmh",
                    "Speed (km/h)",
                    "Speed",
                    "#60a5fa",
                    smooth_field="speed_kmh_smooth",
                ).properties(width="container")
            )

        # Ogni grafico e' incorporato nella sua colonna Streamlit: cosi' la coppia
        # occupa sempre l'intera larghezza della riga (come la tabella), cosa che
        # Vega-Lite non garantisce per un hconcat con figli responsive (i figli
        # senza larghezza esplicita non si dividono lo spazio del contenitore).
        if len(top_charts) == 2:
            top_col1, top_col2 = st.columns(2)
            top_col1.altair_chart(top_charts[0], width="stretch")
            top_col2.altair_chart(top_charts[1], width="stretch")
        elif top_charts:
            st.altair_chart(top_charts[0], width="stretch")

        altitude_chart = None
        if records["altitude_m"].notna().any():
            min_altitude = records["altitude_m"].min()
            max_altitude = records["altitude_m"].max()
            padding = max((max_altitude - min_altitude) * 0.1, 1)
            altitude_chart = _synced_series_chart(
                chart_data,
                hover,
                "altitude_m",
                "Altitude (m)",
                "Elevation profile",
                "#c2410c",
                area=True,
                y_scale=alt.Scale(domain=[min_altitude, max_altitude + padding], nice=False),
            ).properties(width="container")

        scatter = None
        if records[["speed_kmh", "heart_rate"]].notna().all(axis=1).any():
            speed_q1, speed_q3 = records["speed_kmh"].quantile([0.25, 0.75])
            speed_iqr = speed_q3 - speed_q1
            speed_low = speed_q1 - 1.5 * speed_iqr
            speed_high = speed_q3 + 1.5 * speed_iqr
            scatter_data = chart_data[chart_data["speed_kmh"].between(speed_low, speed_high)]
            x_min, x_max = scatter_data["speed_kmh"].min(), scatter_data["speed_kmh"].max()
            y_min, y_max = scatter_data["heart_rate"].min(), scatter_data["heart_rate"].max()
            x_pad = max((x_max - x_min) * 0.05, 0.1)
            y_pad = max((y_max - y_min) * 0.05, 1)
            slope_abs_max = max(scatter_data["slope_pct"].abs().max(skipna=True) or 0, 1)
            scatter = (
                alt.Chart(scatter_data)
                .mark_circle(opacity=0.7, size=40)
                .encode(
                    x=alt.X(
                        "speed_kmh:Q",
                        title="Speed (km/h)",
                        scale=alt.Scale(domain=[x_min - x_pad, x_max + x_pad], nice=False),
                    ),
                    y=alt.Y(
                        "heart_rate:Q",
                        title="HR (bpm)",
                        scale=alt.Scale(domain=[y_min - y_pad, y_max + y_pad], nice=False),
                    ),
                    color=alt.Color(
                        "slope_pct:Q",
                        title="Slope (%)",
                        scale=alt.Scale(domain=[-slope_abs_max, slope_abs_max], range=["red", "green"]),
                    ),
                    tooltip=[
                        alt.Tooltip("speed_kmh:Q", title="Speed (km/h)"),
                        alt.Tooltip("heart_rate:Q", title="HR (bpm)"),
                        alt.Tooltip("slope_pct:Q", title="Slope (%)", format=".1f"),
                    ],
                )
                .properties(title=alt.TitleParams("Speed vs HR", anchor="start"), width="container")
            )

        mid_charts = [c for c in (altitude_chart, scatter) if c is not None]
        if len(mid_charts) == 2:
            mid_col1, mid_col2 = st.columns(2)
            mid_col1.altair_chart(mid_charts[0], width="stretch")
            mid_col2.altair_chart(mid_charts[1], width="stretch")
        elif mid_charts:
            st.altair_chart(mid_charts[0], width="stretch")

        speed_histogram = None
        if records["speed_kmh"].notna().any():
            speed_histogram = (
                alt.Chart(chart_data)
                .mark_bar(color="#60a5fa")
                .encode(
                    x=alt.X("speed_kmh:Q", bin=alt.Bin(maxbins=30), title="Speed (km/h)"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=[alt.Tooltip("count():Q", title="Count")],
                )
                .properties(title=alt.TitleParams("Speed distribution", anchor="start"), width="container")
            )

        hr_histogram = None
        if records["heart_rate"].notna().any():
            hr_histogram = (
                alt.Chart(chart_data)
                .mark_bar(color="#60a5fa")
                .encode(
                    x=alt.X("heart_rate:Q", bin=alt.Bin(maxbins=30), title="HR (bpm)"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=[alt.Tooltip("count():Q", title="Count")],
                )
                .properties(title=alt.TitleParams("HR distribution", anchor="start"), width="container")
            )

        hist_charts = [c for c in (speed_histogram, hr_histogram) if c is not None]
        if len(hist_charts) == 2:
            hist_col1, hist_col2 = st.columns(2)
            hist_col1.altair_chart(hist_charts[0], width="stretch")
            hist_col2.altair_chart(hist_charts[1], width="stretch")
        elif hist_charts:
            st.altair_chart(hist_charts[0], width="stretch")

        if records[["lat", "lon"]].notna().all(axis=1).any():
            st.markdown("**Route**")
            st.map(records[["lat", "lon"]].dropna(), latitude="lat", longitude="lon", size=3)
