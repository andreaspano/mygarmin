"""Streamlit multipage entrypoint.

Run: `uv run streamlit run src/training/interface/app.py`
(or `make interface`).
"""

import streamlit as st

# Il titolo vale per tutta l'app, non per la pagina aperta: "Activities" nella
# scheda del browser era sbagliato due volte su tre. `st.navigation` ci
# aggiunge da se' il nome della pagina corrente.
st.set_page_config(page_title="Training", layout="wide")

pg = st.navigation(
    [
        st.Page("app_pages/profile.py", title="Profile", icon=":material/person:"),
        st.Page("app_pages/activities.py", title="Activities", icon=":material/directions_run:"),
        st.Page("app_pages/week.py", title="Week", icon=":material/calendar_view_week:"),
    ]
)
pg.run()
