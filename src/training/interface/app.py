"""Streamlit multipage entrypoint.

Run: `uv run streamlit run src/training/interface/app.py`
(or `make interface`).
"""

import streamlit as st

# Il titolo vale per tutta l'app, non per la pagina aperta: "Activities" nella
# scheda del browser era sbagliato due volte su tre. Resta lo stesso su tutte
# le pagine (verificato nel browser: `st.navigation` non ci aggiunge il nome
# della pagina corrente).
#
# La barra laterale porta poche voci di navigazione: parte a 200px, il
# minimo che Streamlit accetta, invece dei 300 di default. Quei 100px vanno
# alle pagine, che ne hanno piu' bisogno (la tabella delle attivita' e' piu'
# larga del suo contenitore). Un intero vuol dire "larghezza iniziale, e per
# il resto comportamento automatico": resta richiudibile e trascinabile.
SIDEBAR_WIDTH = 200

st.set_page_config(page_title="Training", layout="wide", initial_sidebar_state=SIDEBAR_WIDTH)

pg = st.navigation(
    [
        st.Page("app_pages/profile.py", title="Profile", icon=":material/person:"),
        st.Page("app_pages/activities.py", title="Day", icon=":material/directions_run:"),
        st.Page("app_pages/week.py", title="Week", icon=":material/calendar_view_week:"),
        st.Page("app_pages/month.py", title="Month", icon=":material/calendar_view_month:"),
    ]
)
pg.run()
