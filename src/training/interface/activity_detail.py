"""Scheda di dettaglio di una singola attivita': metriche, commento, grafici
e traccia.

Sta qui e non nella pagina Activities perche' la stessa scheda si apre anche
dalla pagina Week, cliccando una riga della tabella delle attivita'."""

import json

import altair as alt
import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_report import load_activity_comments
from training.interface.activity_table import sport_icon_path, sport_label
from training.interface.db import load_activity_records
from training.interface.run_chart import EFFECTS, effects, has_effects, run_analysis_chart

alt.data_transformers.disable_max_rows()



def _hm(minutes: float) -> str:
    """Minuti in "hh:mm", come le durate della pagina Week (114 -> "01:54")."""
    if pd.isna(minutes):
        return "-"
    minutes = round(minutes)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _records(activity_id: int) -> pd.DataFrame:
    return load_activity_records(activity_id, DATA_DIR)


def _zone_settings(activity) -> tuple[list[int] | None, int | None]:
    """I tetti di Z1-Z4 e la soglia anaerobica salvati dal FIT, o None (file
    vecchi senza il messaggio delle zone)."""
    bounds = json.loads(activity.hr_zone_bounds) if isinstance(activity.hr_zone_bounds, str) else None
    threshold = int(activity.threshold_hr) if pd.notna(activity.threshold_hr) else None
    return bounds, threshold


def _show_analysis(activity, records: pd.DataFrame) -> None:
    """Il riepilogo degli effetti e il grafico a tre fasce (todo 28), che ha
    preso il posto dei sei grafici di prima (FC, velocita', quota, velocita'
    contro FC e i due istogrammi)."""
    bounds, threshold = _zone_settings(activity)
    has_hr = records["heart_rate"].notna().any()

    # Cinque riquadri: i minuti per effetto, stimati sui battiti, e i due
    # Training Effect di Garmin. Quello che manca non si mostra; senza niente
    # il riepilogo sparisce.
    tiles = []
    if has_effects(bounds, threshold) and has_hr:
        seconds = effects(records, bounds, threshold)
        tiles += [(f"{name} (est.)", _hm(seconds[name] / 60)) for name in EFFECTS]
    if pd.notna(activity.aerobic_te):
        tiles.append(("Aerobic TE", f"{activity.aerobic_te:.1f}"))
    if pd.notna(activity.anaerobic_te):
        tiles.append(("Anaerobic TE", f"{activity.anaerobic_te:.1f}"))
    if tiles:
        for column, (label, value) in zip(st.columns(len(tiles)), tiles):
            column.metric(
                label,
                value,
                border=True,
                help="Estimated from heart rate against your zones: Garmin computes its own "
                "Training Effect, and the file only keeps the session totals."
                if label.endswith("(est.)")
                else "Garmin's Training Effect for the session, 0-5.",
            )

    # Il tema decide i colori: la velocita' e' nel colore del testo, e il viola
    # delle zone si schiarisce sul fondo scuro.
    theme = st.context.theme.type or "light"
    chart = run_analysis_chart(records, bounds, threshold, theme)
    if chart is None:
        st.info("No heart rate or speed to plot for this activity.")
    else:
        st.altair_chart(chart, width="stretch")


def show_activity_detail(activity) -> None:
    """Disegna il dettaglio di `activity` (una riga di `list_activities`)."""
    records = _records(activity.activity_id)

    # La scheda ha lo stesso impianto di quelle per sport della pagina Week:
    # riquadro con bordo, icona e titolo sulla stessa riga, metriche su due
    # righe da tre e due. Il commento sta accanto invece di finire sotto.
    #
    # Tre quinti della pagina e non un terzo come le schede della Week: a un
    # terzo i valori grandi delle metriche ("+164 / -163 m", "135 bpm") non ci
    # stanno e Streamlit li taglia con i puntini, e a meta' succedeva ancora a
    # 1280px. Misurato nel browser a 1440 e a 1280.
    card_col, comment_col = st.columns([3, 2])
    with card_col.container(border=True):
        head = st.container(horizontal=True, vertical_alignment="center")
        icon_path = sport_icon_path(activity.sport)
        if icon_path:
            head.image(icon_path, width=40)
        head.markdown(
            f"**{sport_label(activity.sport)}** — {activity.start_time:%d %b %Y, %H:%M}"
        )

        # Prima riga le tre grandezze che sono anche colonne di tabella, nello
        # stesso ordine, cosi' l'occhio le ritrova; sotto le tre che dalla
        # tabella sono state tolte e che vivono solo qui.
        distance_col, time_col, ascent_col = st.columns(3)
        distance_col.metric("Distance", f"{activity.total_distance_km:.1f} km")
        time_col.metric("Duration", _hm(activity.total_time_min))
        ascent_col.metric(
            "Elevation",
            f"+{activity.total_ascent_m:.0f} / -{activity.total_descent_m:.0f} m"
            if pd.notna(activity.total_ascent_m)
            else "-",
        )

        speed_col, hr_col, vo2_col = st.columns(3)
        # Sul tempo in movimento, non sulla durata qui sopra (che e' quella
        # totale, soste comprese): km/h per durata non da' i chilometri.
        speed_col.metric(
            "Avg speed",
            f"{activity.avg_speed_kmh:.1f} km/h" if pd.notna(activity.avg_speed_kmh) else "-",
            help="Average speed, over moving time (the duration above is elapsed time, "
            "stops included).",
        )
        hr_col.metric(
            "Avg HR",
            f"{activity.avg_heart_rate:.0f} bpm" if pd.notna(activity.avg_heart_rate) else "-",
        )
        # La stima dell'orologio a fine attivita' (vedi `fit._vo2max`): manca
        # per le attivita' che l'orologio non considera, come le escursioni.
        vo2_col.metric(
            "VO2Max",
            f"{activity.vo2max:.1f}" if pd.notna(activity.vo2max) else "-",
            help="The watch's VO2max estimate at the end of the activity, in ml/kg/min. "
            "Runs update it; other activities carry the last value. Empty when the "
            "watch stored none.",
        )

    with comment_col:
        st.markdown("**Comment**")
        saved_comments = load_activity_comments(activity.activity_id)
        if saved_comments is None:
            st.info("Report not generated yet for this activity. Run `make activity_reports`.")
        else:
            for comment in saved_comments:
                st.markdown(f"- {comment}")

    if records.empty:
        st.warning("No sampled data (records) in this file.")
        return

    _show_analysis(activity, records)

    if records[["lat", "lon"]].notna().all(axis=1).any():
        st.markdown("**Route**")
        st.map(records[["lat", "lon"]].dropna(), latitude="lat", longitude="lon", size=3)
