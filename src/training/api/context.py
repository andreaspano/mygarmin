"""L'utente di una richiesta: da quale cartella dati e da quale cartella dei
report leggere.

Ogni endpoint lo riceve da `get_user_context()`, una dipendenza FastAPI.
Oggi l'utente e' uno solo e la dipendenza rende sempre le stesse cartelle;
con il login cambiera' solo lei, non gli endpoint."""

from dataclasses import dataclass
from pathlib import Path

from training.garmin.config import DATA_DIR

# La radice del repo e non la cartella corrente, come `config.CONFIG_PATH`:
# l'API non deve dipendere dalla cartella da cui si lancia. Le pagine
# Streamlit usano invece `Path("summary/...")` relativo.
REPO_ROOT = Path(__file__).resolve().parents[3]
SUMMARY_DIR = REPO_ROOT / "summary"
# Le icone sono del repo, non dell'utente: uguali per tutti.
ICONS_DIR = REPO_ROOT / "icons"


@dataclass(frozen=True)
class UserContext:
    data_dir: Path
    summary_dir: Path


def get_user_context() -> UserContext:
    return UserContext(data_dir=DATA_DIR, summary_dir=SUMMARY_DIR)
