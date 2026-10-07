"""Activities page: browse FIT activities downloaded into data/."""

import datetime as dt

import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import activity_table, sport_label, with_empty_days
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
# Fino a oggi e non fino all'ultima attivita': la tabella ha una riga per ogni
# giorno (todo 30), e i giorni di riposo piu' recenti devono vedersi.
start_date, end_date = date_range(
    activities,
    filter_row,
    "'From' is later than 'To': swap the two dates to see the activities.",
    latest=dt.date.today(),
)

latest = activities
if sports:
    latest = latest[latest["sport"].isin(sports)]
latest = latest[
    (latest["start_time"].dt.date >= start_date) & (latest["start_time"].dt.date <= end_date)
]
latest = latest.copy()

# Un giorno senza attivita' (dello sport scelto, se c'e' il filtro) ha una riga
# vuota con la sola data: dalla tabella si vede anche quando non ci si e'
# allenati. Per questo un intervallo senza attivita' non ferma la pagina.
rows = with_empty_days(latest, start_date, end_date)

# Larga quanto il riquadro della scheda sotto (`activity_detail`, prima di
# due colonne 3:2): con sei colonne, a tutta pagina meta' tabella era vuota.
table_col, _ = st.columns([3, 2])
table_col.caption("Click a row to see the details.")

# La tabella e' ordinata dalla piu' recente: alla prima apertura (e a ogni
# cambio di filtro, che cambia le righe e quindi la key) e' gia' selezionata
# l'attivita' piu' recente, cosi' la pagina si apre sul dettaglio invece che a
# meta'. Non la prima riga: spesso e' un giorno vuoto, come oggi prima di
# allenarsi.
table_key = f"activities_{'-'.join(sports)}_{start_date}_{end_date}"
if table_key not in st.session_state:
    with_activity = rows.index[rows["activity_id"].notna()]
    first = [int(with_activity[0])] if len(with_activity) else []
    st.session_state[table_key] = {"selection": {"rows": first, "columns": []}}

with table_col:
    event = activity_table(
        rows,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )

selected_rows = event.selection.rows
if not selected_rows:
    # Senza nessuna attivita' nell'intervallo non c'e' niente da scegliere: lo
    # si dice, invece di chiedere di selezionare una riga.
    st.info(
        "Select an activity from the table to see its details."
        if rows["activity_id"].notna().any()
        else "No activity in the selected period."
    )
    st.stop()

selected = rows.iloc[selected_rows[0]]
if pd.isna(selected["activity_id"]):
    st.info("No activity on this day.")
    st.stop()

# La riga dell'attivita' da `latest` e non da `rows`: li' le colonne con le
# righe vuote hanno perso i loro tipi (gli id diventano float).
show_activity_detail(latest[latest["activity_id"] == selected["activity_id"]].iloc[0])
