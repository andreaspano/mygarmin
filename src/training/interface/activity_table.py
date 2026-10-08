"""Tabella delle singole attivita', condivisa fra le pagine.

La pagina Activities e quella Week mostrano lo stesso elenco (stesse colonne,
stessi formati, stesse icone): tenerlo qui evita che le due copie divergano."""

import base64
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

# Etichette e file delle icone stanno in `sports.py`, senza Streamlit, perche'
# li usa anche l'API (todo 33). `sport_label` si importa ancora da qui nelle
# pagine.
from training.interface.sports import REST_ICON_FILE, SPORT_ICON_FILES, sport_label

ICONS_DIR = Path("icons")
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
#
# Data e ora stanno in due colonne (todo 30): la Day ha una riga anche per i
# giorni senza attivita', e li' "7 Oct 2026, 00:00" sembrerebbe un'uscita a
# mezzanotte. Entrambe si ricavano da `start_time` in `activity_table()`.
ACTIVITY_COLUMNS = [
    "icon",
    "day",
    "time",
    "activity_name",
    "total_distance_km",
    "total_time_min",
    "total_ascent_m",
]
ACTIVITY_COLUMN_CONFIG = {
    "icon": st.column_config.ImageColumn("", width=50),
    "day": st.column_config.DateColumn("Date", format="ddd D MMM YYYY", width=120),
    "time": st.column_config.TextColumn("Time", width=60),
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


# L'icona dei giorni di riposo nella tabella della Day (righe vuote, todo 30).
@st.cache_data
def rest_icon() -> str | None:
    """L'icona del riposo come data URI, come quelle degli sport, o None se il
    file manca."""
    path = ICONS_DIR / REST_ICON_FILE
    if not path.exists():
        return None
    mime = _ICON_MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


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
    activities = activities.copy()
    # Le righe dei giorni vuoti portano gia' il loro `day` (vedi
    # `with_empty_days`); le altre lo prendono dall'inizio dell'attivita'.
    if "day" not in activities.columns:
        activities["day"] = activities["start_time"].dt.date
    activities["time"] = activities["start_time"].dt.strftime("%H:%M")
    # Un giorno vuoto non ha icona: None, non NaN, che la colonna immagine
    # proverebbe a mostrare.
    activities["icon"] = activities["icon"].where(activities["icon"].notna(), None)
    return st.dataframe(
        activities[ACTIVITY_COLUMNS],
        column_config=ACTIVITY_COLUMN_CONFIG,
        hide_index=True,
        **kwargs,
    )


def with_empty_days(activities: pd.DataFrame, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Le attivita' piu' una riga vuota per ogni giorno fra `start` e `end`
    (compresi) che non ne ha nessuna, dalla piu' recente (todo 30).

    Le righe vuote hanno solo `day`: niente icona, nome, numeri. Un giorno con
    due attivita' resta su due righe. Le righe vuote esistono solo qui, per la
    tabella della Day: i dati non cambiano."""
    rows = activities.assign(day=activities["start_time"].dt.date)
    taken = set(rows["day"])
    empty = pd.DataFrame({"day": [day for day in pd.date_range(start, end, freq="D").date if day not in taken]})
    combined = pd.concat([rows, empty], ignore_index=True) if not empty.empty else rows
    return combined.sort_values(["day", "start_time"], ascending=False, na_position="last").reset_index(
        drop=True
    )
