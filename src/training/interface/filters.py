"""Filtri condivisi fra le pagine."""

import datetime as dt

import pandas as pd
import streamlit as st


def date_range(
    activities: pd.DataFrame, container=None, invalid_message: str | None = None
) -> tuple[dt.date, dt.date]:
    """Le due caselle a calendario "From" / "To", con l'intervallo scelto.

    Gli estremi sono la prima e l'ultima attivita', e di default sono anche i
    valori iniziali: si parte vedendo tutto. Se le date sono invertite la
    pagina si ferma con un avviso invece di mostrare una lista vuota.

    `container` e' dove metterle (es. una riga orizzontale condivisa con
    altri filtri); senza, vanno sulla pagina."""
    where = container if container is not None else st

    min_date = activities["start_time"].min().date()
    max_date = activities["start_time"].max().date()

    start_date = where.date_input(
        "From", value=min_date, min_value=min_date, max_value=max_date, width=160
    )
    end_date = where.date_input(
        "To", value=max_date, min_value=min_date, max_value=max_date, width=160
    )

    if start_date > end_date:
        st.warning(invalid_message or "'From' is later than 'To': swap the two dates.")
        st.stop()

    return start_date, end_date
