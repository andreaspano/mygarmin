"""Activities page: browse FIT activities downloaded into data/."""

import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import activity_table, sport_label
from training.interface.data import load_activities
from training.interface.filters import date_range


st.title("My activities")

activities = load_activities(DATA_DIR)

if activities.empty:
    st.info(f"No *_ACTIVITY.fit file found in {DATA_DIR.resolve()}.")
    st.stop()

filter_row = st.container(horizontal=True)
# I valori restano le chiavi (e' su quelle che si filtra), ma si leggono con
# le stesse etichette delle tabelle.
sports = filter_row.multiselect(
    "Sport",
    sorted(activities["sport"].dropna().unique()),
    format_func=sport_label,
    placeholder="All",
    width=200,
)
start_date, end_date = date_range(
    activities,
    filter_row,
    "'From' is later than 'To': swap the two dates to see the activities.",
)

latest = activities
if sports:
    latest = latest[latest["sport"].isin(sports)]
latest = latest[
    (latest["start_time"].dt.date >= start_date) & (latest["start_time"].dt.date <= end_date)
]
latest = latest.copy()

if latest.empty:
    st.info("No activity matches the selected filters.")
    st.stop()

# Larga quanto il riquadro della scheda sotto (`activity_detail`, prima di
# due colonne 3:2): con sei colonne, a tutta pagina meta' tabella era vuota.
table_col, _ = st.columns([3, 2])
table_col.caption("Click a row to see the details.")

# La tabella e' ordinata dalla piu' recente: alla prima apertura (e a ogni
# cambio di filtro, che cambia le righe e quindi la key) la prima riga e' gia'
# selezionata, cosi' la pagina si apre sul dettaglio invece che a meta'.
table_key = f"activities_{'-'.join(sports)}_{start_date}_{end_date}"
if table_key not in st.session_state:
    st.session_state[table_key] = {"selection": {"rows": [0], "columns": []}}

with table_col:
    event = activity_table(
        latest,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )

selected_rows = event.selection.rows
if not selected_rows:
    st.info("Select an activity from the table to see its details.")
    st.stop()

show_activity_detail(latest.iloc[selected_rows[0]])
