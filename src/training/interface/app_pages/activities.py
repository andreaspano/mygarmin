"""Activities page: browse FIT activities downloaded into data/."""

import datetime as dt

from pathlib import Path

import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import (
    activity_table,
    rest_icon,
    sport_label,
    with_empty_days,
    with_icons,
)
from training.interface.data import load_activities
from training.interface.filters import date_range
from training.interface.report_view import show_report

# Il report giornaliero (agente `fitness-status`, todo 31): uno per giorno,
# con il nome esatto del giorno. Altri file nella cartella (es.
# `2026-10-01_since-2026-08-01.md`) non si mostrano.
DAILY_REPORT_DIR = Path("summary/01.daily")
# Tabella e report accanto hanno la stessa altezza fissa: dieci righe da 35px
# piu' l'intestazione, come la tabella dei periodi nella Week. Oltre, la
# tabella e il report scorrono dentro il loro riquadro.
TABLE_HEIGHT_PX = 35 * 11 + 3
# Lo spazio fra la tabella e la scheda sotto, nella stessa colonna.
_COLUMN_GAP_PX = 16


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
rows = with_icons(with_empty_days(latest, start_date, end_date))
# Le righe vuote prendono l'icona del riposo, ma non sempre: non oggi, che la
# giornata non e' finita e ci si puo' ancora allenare; e non con un filtro per
# sport, dove una riga vuota vuol dire "niente ciclismo quel giorno", non "un
# giorno di riposo".
if not sports:
    rest_days = rows["activity_id"].isna() & (rows["day"] != dt.date.today())
    rows.loc[rest_days, "icon"] = rest_icon()

# Larga quanto il riquadro della scheda sotto (`activity_detail`, prima di
# due colonne 3:2): con sei colonne, a tutta pagina meta' tabella era vuota.
# Nella colonna di destra il report giornaliero del giorno scelto (todo 31),
# come il report settimanale accanto alla tabella della Week.
st.caption("Click a row to see the details.")
table_col, report_col = st.columns([3, 2])

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
        height=TABLE_HEIGHT_PX,
    )

selected_rows = event.selection.rows
selected = rows.iloc[selected_rows[0]] if selected_rows else None

# Sotto la tabella, nella stessa colonna, la scheda dell'attivita' scelta (o
# un messaggio); grafico e mappa vengono dopo, a tutta larghezza.
card_height = 0
if selected is None:
    # Senza nessuna attivita' nell'intervallo non c'e' niente da scegliere: lo
    # si dice, invece di chiedere di selezionare una riga.
    table_col.info(
        "Select an activity from the table to see its details."
        if rows["activity_id"].notna().any()
        else "No activity in the selected period."
    )
elif pd.isna(selected["activity_id"]):
    table_col.info("No activity on this day.")
else:
    # La riga dell'attivita' da `latest` e non da `rows`: li' le colonne con le
    # righe vuote hanno perso i loro tipi (gli id diventano float).
    activity = latest[latest["activity_id"] == selected["activity_id"]].iloc[0]
    card_height = show_activity_detail(activity, card_container=table_col)

# Il report del giorno a destra, alto quanto tabella e scheda insieme (con lo
# spazio fra le due), cosi' le due colonne finiscono alla stessa altezza.
# C'e' anche per un giorno senza attivita': il riposo e' proprio il giorno in
# cui serve.
if selected is not None:
    with report_col:
        show_report(
            DAILY_REPORT_DIR / f"{selected['day']:%Y-%m-%d}.md",
            TABLE_HEIGHT_PX + (_COLUMN_GAP_PX + card_height if card_height else 0),
            "day_report",
            missing_text="No daily report for this day.",
        )
