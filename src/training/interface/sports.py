"""Gli sport come si leggono a schermo: etichette e file delle icone.

Le usa l'API (`training.api`, todo 33), e da li' la pagina in React. Le
icone stanno nella cartella `icons/` della radice del repo."""

# Le chiavi sono quelle di `activities.sport` (vedi `db.GARMIN_TYPE_TO_SPORT`).
SPORT_ICON_FILES = {
    "walking": "walking.png",
    "running": "running.png",
    "cycling": "cycling.png",
    "hiking": "trekking.png",
    "cross_country_skiing": "backcountry_ski.png",
    "rock_climbing": "climbing.png",
}

# L'icona dei giorni di riposo: la striscia della settimana la mette nei
# giorni senza attivita', e la scheda Training nei "Rest day". Grigia, per
# restare indietro rispetto ai colori degli sport.
REST_ICON_FILE = "rest.png"


def sport_label(value: str | None) -> str:
    """Il nome di uno sport (o di un sotto-tipo) come si legge a schermo.

    Nei dati gli sport sono chiavi: `cross_country_skiing`. A schermo diventano
    "Cross country skiing": iniziale maiuscola e basta. Passa di qui ogni
    etichetta, cosi' lo stesso sport si legge uguale nella striscia della
    settimana, nelle linguette e nella scheda Training."""
    if not value:
        return "?"
    return value.replace("_", " ").capitalize()
