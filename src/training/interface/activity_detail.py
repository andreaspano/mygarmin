"""Scheda di dettaglio di una singola attivita': metriche, grafico e
traccia.

Sta qui e non nella pagina Activities perche' la stessa scheda si apre anche
dalla pagina Week, cliccando una riga della tabella delle attivita'."""

import altair as alt
import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_table import sport_icon_path, sport_label
from training.interface.db import load_activity_records
from training.interface.run_chart import EFFECTS, effects, has_effects, run_analysis_chart, zone_settings

alt.data_transformers.disable_max_rows()



def _hm(minutes: float) -> str:
    """Minuti in "hh:mm", come le durate della pagina Week (114 -> "01:54")."""
    if pd.isna(minutes):
        return "-"
    minutes = round(minutes)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _records(activity_id: int) -> pd.DataFrame:
    return load_activity_records(activity_id, DATA_DIR)


def _effect_rows(activity, records: pd.DataFrame) -> list[list[tuple[str, str, str]]]:
    """Le righe della scheda con gli effetti: i minuti per effetto, stimati
    sui battiti, e i due Training Effect di Garmin, come (etichetta, valore,
    aiuto). Quello che manca non si mostra, e una riga vuota sparisce."""
    bounds, threshold = zone_settings(activity)
    estimated, garmin = [], []
    if has_effects(bounds, threshold) and records["heart_rate"].notna().any():
        seconds = effects(records, bounds, threshold)
        # Le soglie nell'aiuto sono quelle di questa attivita', lette dal FIT:
        # cambiano nel tempo, e il numero dice piu' del nome della zona.
        z3_top = bounds[2]
        ranges = (
            f"heart rate at or below the top of Z3 ({z3_top} bpm)",
            f"heart rate between the top of Z3 and the anaerobic threshold "
            f"({z3_top + 1}-{threshold} bpm)",
            f"heart rate above the anaerobic threshold ({threshold} bpm)",
        )
        estimated = [
            (
                f"{name} (est.)",
                _hm(seconds[name] / 60),
                f"Time (hh:mm) with {hr_range}. Estimated from heart rate: Garmin computes "
                "its own Training Effect, and the file only keeps the session totals.",
            )
            for name, hr_range in zip(EFFECTS, ranges)
        ]
    te_help = {
        "Aerobic TE": "Garmin's aerobic Training Effect for the session, from 0 to 5: how much "
        "the activity improved your aerobic fitness.",
        "Anaerobic TE": "Garmin's anaerobic Training Effect for the session, from 0 to 5: how "
        "much the activity improved your capacity for high-intensity efforts.",
    }
    for label, value in (("Aerobic TE", activity.aerobic_te), ("Anaerobic TE", activity.anaerobic_te)):
        if pd.notna(value):
            garmin.append((label, f"{value:.1f}", te_help[label]))
    return [row for row in (estimated, garmin) if row]


def _show_analysis(activity, records: pd.DataFrame) -> None:
    """Il grafico a tre fasce (todo 28), che ha preso il posto dei sei
    grafici di prima (FC, velocita', quota, velocita' contro FC e i due
    istogrammi). Il riepilogo degli effetti sta nella scheda, sopra."""
    bounds, threshold = zone_settings(activity)

    # Il tema decide i colori: la velocita' e' nel colore del testo, e il viola
    # delle zone si schiarisce sul fondo scuro.
    theme = st.context.theme.type or "light"
    chart = run_analysis_chart(records, bounds, threshold, theme)
    if chart is None:
        st.info("No heart rate or speed to plot for this activity.")
    else:
        st.altair_chart(chart, width="stretch")


# L'altezza della scheda, in pixel, per chi deve affiancarle qualcosa di alto
# uguale (il report giornaliero nella Day). Streamlit non dice quanto e' alto
# un contenitore: sono stime, sulle misure di Streamlit 1.63 come quelle della
# tabella in `period_page`. Bordo e margini interni del riquadro, la riga con
# icona e titolo, e una riga di metriche (etichetta e valore) con lo spazio
# sotto.
_CARD_FRAME_PX = 34
_CARD_HEAD_PX = 56
_CARD_METRIC_ROW_PX = 100


def show_activity_detail(activity, card_container=None) -> int:
    """Disegna il dettaglio di `activity` (una riga di `list_activities`) e
    rende l'altezza stimata della scheda, in pixel.

    Con `card_container` la scheda va li' (la Day la mette nella colonna della
    tabella, con il report accanto); senza, nella prima di due colonne 3:2,
    come prima. Grafico e mappa stanno comunque sotto, a tutta larghezza."""
    records = _records(activity.activity_id)
    effect_rows = _effect_rows(activity, records)

    # La scheda ha lo stesso impianto di quelle per sport della pagina Week:
    # riquadro con bordo, icona e titolo sulla stessa riga, metriche su due
    # righe da tre. Il commento del report, che stava accanto, e' stato tolto
    # per scelta di Andrea: la seconda colonna resta vuota, cosi' il riquadro
    # resta largo quanto la tabella sopra (pagina Day).
    #
    # Tre quinti della pagina e non un terzo come le schede della Week: a un
    # terzo i valori grandi delle metriche ("+164 / -163 m", "135 bpm") non ci
    # stanno e Streamlit li taglia con i puntini, e a meta' succedeva ancora a
    # 1280px. Misurato nel browser a 1440 e a 1280.
    card_col = card_container if card_container is not None else st.columns([3, 2])[0]
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
        distance_col.metric(
            "Distance",
            f"{activity.total_distance_km:.1f} km",
            help="Total distance recorded by the watch, in km.",
        )
        time_col.metric(
            "Duration",
            _hm(activity.total_time_min),
            help="Elapsed time from start to finish, in hh:mm, pauses and stops included.",
        )
        ascent_col.metric(
            "Elevation",
            f"+{activity.total_ascent_m:.0f} / -{activity.total_descent_m:.0f} m"
            if pd.notna(activity.total_ascent_m)
            else "-",
            help="Total ascent and descent recorded by the watch, in metres. "
            "Empty when the watch stored no altitude.",
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
            help="Average heart rate over the activity, in beats per minute. Empty when "
            "no heart rate was recorded.",
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

        # Sotto, nello stesso riquadro e sulla stessa griglia da tre, gli
        # effetti dell'allenamento: prima la stima sui battiti, poi i valori
        # di Garmin.
        for row in effect_rows:
            for column, (label, value, help_text) in zip(st.columns(3), row):
                column.metric(label, value, help=help_text)

    card_height = _CARD_FRAME_PX + _CARD_HEAD_PX + _CARD_METRIC_ROW_PX * (2 + len(effect_rows))

    if records.empty:
        st.warning("No sampled data (records) in this file.")
        return card_height

    _show_analysis(activity, records)

    if records[["lat", "lon"]].notna().all(axis=1).any():
        st.markdown("**Route**")
        st.map(records[["lat", "lon"]].dropna(), latitude="lat", longitude="lon", size=3)
    return card_height
