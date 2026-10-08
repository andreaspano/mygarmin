"""Gli sport come si leggono a schermo: etichette e file delle icone.

Senza Streamlit: le usano le pagine (`activity_table.py`) e l'API
(`training.api`, todo 33), che cosi' hanno una fonte sola. Le icone stanno
nella cartella `icons/` della radice del repo."""

# Le chiavi sono quelle di `activities.sport` (vedi `db.GARMIN_TYPE_TO_SPORT`).
SPORT_ICON_FILES = {
    "walking": "walking.png",
    "running": "running.png",
    "cycling": "cycling.png",
    "hiking": "trekking.png",
    "cross_country_skiing": "backcountry_ski.png",
    "rock_climbing": "climbing.png",
}

# L'icona dei giorni di riposo nella tabella della Day (righe vuote, todo 30):
# grigia, per restare indietro rispetto ai colori degli sport.
REST_ICON_FILE = "rest.png"


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
