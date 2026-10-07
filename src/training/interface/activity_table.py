"""Tabella delle singole attivita', condivisa fra le pagine.

La pagina Activities e quella Week mostrano lo stesso elenco (stesse colonne,
stessi formati, stesse icone): tenerlo qui evita che le due copie divergano."""

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

ICONS_DIR = Path("icons")
SPORT_ICON_FILES = {
    "walking": "walking.png",
    "running": "running.png",
    "cycling": "cycling.png",
    "hiking": "trekking.png",
    "cross_country_skiing": "backcountry_ski.png",
}
_ICON_MIME_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

# Le tre grandezze che dicono "che uscita e' stata" (quanto lunga, quanto e'
# durata, quanto saliva), dopo icona, data e nome. Velocita' media, battito e
# VO2max stanno nella scheda di dettaglio sotto la tabella (`activity_detail`),
# che si apre sulla riga selezionata: erano sei numeri per riga da leggere di
# sfuggita. Il sotto-tipo (`sub_sport`: "Road", "Generic", ...) non ha una
# colonna: diceva poco. Tolte anche (todo 29, scelta di Andrea) l'ID, che a
# chi legge non dice niente, lo sport, che lo dice gia' l'icona, e la
# velocita' equivalente, che ora si legge nel grafico della scheda (todo 28).
# Restano tutte nei dati, come le metriche spostate.
ACTIVITY_COLUMNS = [
    "icon",
    "start_time",
    "activity_name",
    "total_distance_km",
    "total_time_min",
    "total_ascent_m",
]
ACTIVITY_COLUMN_CONFIG = {
    "icon": st.column_config.ImageColumn("", width=50),
    "start_time": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm", width=160),
    "activity_name": st.column_config.TextColumn("Name", width=185),
    # Intestazioni corte, la sola unita': e' una tabella che si scorre con gli
    # occhi riga per riga, e "km", "Min", "Bpm" si leggono al volo. Il nome
    # della grandezza sta nel `help`, per chi passa sopra l'intestazione.
    "total_distance_km": st.column_config.NumberColumn(
        "km", format="%.1f", width=80, alignment="center", help="Distance."
    ),
    "total_time_min": st.column_config.NumberColumn(
        "Min", format="%.0f", width=70, alignment="center", help="Duration, in minutes."
    ),
    "total_ascent_m": st.column_config.NumberColumn(
        "D+", format="%.0f", width=60, alignment="center", help="Elevation gain, in metres."
    ),
}


@st.cache_data
def sport_icons() -> dict:
    icons = {}
    for sport, filename in SPORT_ICON_FILES.items():
        path = ICONS_DIR / filename
        if path.exists():
            mime = _ICON_MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            icons[sport] = f"data:{mime};base64,{encoded}"
    return icons


def sport_label(value: str | None) -> str:
    """Il nome di uno sport (o di un sotto-tipo) come si legge a schermo.

    Nei dati gli sport sono chiavi: `cross_country_skiing`. A schermo diventano
    "Cross country skiing", con la stessa regola che `profile.py` applica ai
    suoi valori (`CAPITALIZE_KEYS`): iniziale maiuscola e basta. Passa di qui
    ogni etichetta, cosi' lo stesso sport si legge uguale nelle tabelle, nelle
    schede, nei grafici e nei filtri."""
    if not value:
        return "?"
    return value.replace("_", " ").capitalize()


def sport_icon_path(sport: str | None) -> Path | None:
    """Il file dell'icona, per chi vuole mostrarla con `st.image` invece che
    dentro una colonna della tabella."""
    filename = SPORT_ICON_FILES.get(sport)
    if not filename:
        return None
    path = ICONS_DIR / filename
    return path if path.exists() else None


def with_icons(activities: pd.DataFrame) -> pd.DataFrame:
    activities = activities.copy()
    activities["icon"] = activities["sport"].map(sport_icons())
    return activities


def activity_table(activities: pd.DataFrame, **kwargs):
    """Mostra `activities` con le colonne/formati standard.

    Gli argomenti extra (`on_select`, `selection_mode`, `key`, `height`, ...)
    passano dritti a `st.dataframe`, cosi' ogni pagina decide se la tabella
    e' selezionabile o solo da leggere."""
    if "icon" not in activities.columns:
        activities = with_icons(activities)
    return st.dataframe(
        activities[ACTIVITY_COLUMNS],
        column_config=ACTIVITY_COLUMN_CONFIG,
        hide_index=True,
        **kwargs,
    )
