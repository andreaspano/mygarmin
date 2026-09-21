"""Filtri condivisi fra le pagine."""

import datetime as dt

import pandas as pd
import streamlit as st


# Scorciatoie di periodo: quante settimane indietro dall'ultima attivita'.
# `None` significa "non conta le settimane": ci pensa `_preset_range`.
_PRESETS: dict[str, int | None] = {
    "4 weeks": 4,
    "8 weeks": 8,
    "12 weeks": 12,
    "This year": None,
    "All": None,
}
_DEFAULT_PRESET = "12 weeks"


def _preset_range(
    preset: str, min_date: dt.date, max_date: dt.date
) -> tuple[dt.date, dt.date]:
    """L'intervallo di una scorciatoia, sempre dentro i dati disponibili.

    Si conta indietro dall'ultima attivita' e non da oggi: aprendo la pagina
    dopo due settimane di pausa "ultime 4 settimane" deve mostrare le ultime
    quattro settimane di allenamento, non due settimane vuote."""
    if preset == "All":
        return min_date, max_date
    if preset == "This year":
        return max(min_date, dt.date(max_date.year, 1, 1)), max_date
    weeks = _PRESETS[preset]
    return max(min_date, max_date - dt.timedelta(weeks=weeks)), max_date


def date_range(
    activities: pd.DataFrame,
    container=None,
    invalid_message: str | None = None,
    presets: bool = False,
    key: str = "date_range",
) -> tuple[dt.date, dt.date]:
    """Le due caselle a calendario "From" / "To", con l'intervallo scelto.

    Gli estremi sono la prima e l'ultima attivita'. Se le date sono invertite
    la pagina si ferma con un avviso invece di mostrare una lista vuota.

    `container` e' dove metterle (es. una riga orizzontale condivisa con
    altri filtri); senza, vanno sulla pagina.

    Con `presets` si mette sopra una fila di scorciatoie (ultime 4/8/12
    settimane, anno corrente, tutto), con le due caselle affiancate nella riga
    sotto: le scorciatoie sono la scelta di tutti i giorni, le date a mano
    sono la rifinitura, e una sotto l'altra si leggono in quell'ordine. Per
    questo con `presets` il `container` deve essere verticale (o mancare): in
    una riga orizzontale finirebbe tutto affiancato.

    Si parte da `_DEFAULT_PRESET` invece che dallo storico intero: le due
    caselle restano modificabili a mano, e toccarle non cancella la
    scorciatoia, la sorpassa e basta. Senza
    `presets` la funzione si comporta esattamente come prima, caselle senza
    stato incluse, perche' la pagina Activities non deve cambiare."""
    where = container if container is not None else st

    min_date = activities["start_time"].min().date()
    max_date = activities["start_time"].max().date()

    if not presets:
        start_date = where.date_input(
            "From", value=min_date, min_value=min_date, max_value=max_date, width=160
        )
        end_date = where.date_input(
            "To", value=max_date, min_value=min_date, max_value=max_date, width=160
        )
        return _checked(start_date, end_date, invalid_message)

    from_key, to_key, preset_key = f"{key}_from", f"{key}_to", f"{key}_preset"

    # Prima apertura: si parte dalla scorciatoia di default, non da tutto.
    if from_key not in st.session_state:
        st.session_state[from_key], st.session_state[to_key] = _preset_range(
            _DEFAULT_PRESET, min_date, max_date
        )

    preset = where.segmented_control(
        "Period",
        list(_PRESETS),
        default=_DEFAULT_PRESET,
        key=preset_key,
        label_visibility="collapsed",
    )

    # Le caselle seguono la scorciatoia solo quando questa cambia davvero:
    # cosi' una data corretta a mano non viene riscritta al rerun successivo.
    # Lo stato dei widget si puo' toccare finche' non sono stati creati.
    if preset is not None and preset != st.session_state.get(f"{preset_key}_prev"):
        st.session_state[from_key], st.session_state[to_key] = _preset_range(
            preset, min_date, max_date
        )
    st.session_state[f"{preset_key}_prev"] = preset

    dates_row = where.container(horizontal=True)
    start_date = dates_row.date_input(
        "From", min_value=min_date, max_value=max_date, width=160, key=from_key
    )
    end_date = dates_row.date_input(
        "To", min_value=min_date, max_value=max_date, width=160, key=to_key
    )
    return _checked(start_date, end_date, invalid_message)


def _checked(
    start_date: dt.date, end_date: dt.date, invalid_message: str | None
) -> tuple[dt.date, dt.date]:
    if start_date > end_date:
        st.warning(invalid_message or "'From' is later than 'To': swap the two dates.")
        st.stop()
    return start_date, end_date
