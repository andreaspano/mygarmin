"""Il terreno delle attivita' a piedi (todo 35): pista, strada, sterrato,
sentiero, montagna.

Il terreno si stima dai dati che ci sono gia' (tipo Garmin, `sub_sport`,
salita per km) e Andrea lo puo' correggere dalla Day in React. La stima si
calcola in lettura e non sta in `activities.db`; le correzioni stanno in
`activity_terrain.json` nella cartella dati, accanto a `activity_names.json`,
perche' `db.rebuild()` cancella il database e le perderebbe."""

import json
import os
import tempfile
import threading
from pathlib import Path

from training.interface.fit import _load_json_map
from training.interface.grade import EQUIV_SPEED_SPORTS

TERRAINS = ("track", "road", "gravel", "trail", "mountain")

# Le soglie sulla salita per km, guardate sulle attivita' fino al
# 2026-10-11. Le escursioni hanno la mediana a 68 m/km (un quarto sotto i
# 51, un quarto sopra gli 87): a 60 si dividono circa a meta' fra sentiero e
# montagna. Le corse hanno il 90% sotto i 24 m/km: a 25 restano "trail" solo
# la ventina di corse piu' collinari (Piombino 44, i giri del 09/2026 sopra
# i 30), nessuna arriva a 60.
MOUNTAIN_M_PER_KM = 60
TRAIL_M_PER_KM = 25

_TERRAIN_FILENAME = "activity_terrain.json"
_write_lock = threading.Lock()


def has_terrain(sport: str | None, sub_sport: str | None, garmin_type: str | None) -> bool:
    """Solo gli sport a piedi hanno un terreno, e il tapis roulant no."""
    if sport not in EQUIV_SPEED_SPORTS:
        return False
    return sub_sport != "treadmill" and garmin_type != "treadmill_running"


def guess_terrain(
    sport: str | None,
    sub_sport: str | None,
    garmin_type: str | None,
    distance_km: float | None,
    ascent_m: float | None,
) -> str | None:
    """Il terreno stimato, o `None` per gli sport senza terreno. Lo sterrato
    non si stima mai: dove i dati non decidono, e' strada."""
    if not has_terrain(sport, sub_sport, garmin_type):
        return None
    if garmin_type == "track_running" or sub_sport == "track":
        return "track"
    if garmin_type == "mountaineering":
        return "mountain"
    climb = _climb_per_km(distance_km, ascent_m)
    if climb is not None and climb >= MOUNTAIN_M_PER_KM:
        return "mountain"
    if garmin_type == "trail_running" or sub_sport == "trail" or sport == "hiking":
        return "trail"
    if climb is not None and climb >= TRAIL_M_PER_KM:
        return "trail"
    return "road"


def _climb_per_km(distance_km: float | None, ascent_m: float | None) -> float | None:
    # I NaN di pandas arrivano qui come float: `x == x` e' falso solo per NaN.
    if distance_km is None or ascent_m is None or distance_km != distance_km or ascent_m != ascent_m:
        return None
    if distance_km <= 0:
        return None
    return ascent_m / distance_km


def _terrain_path(data_dir: Path) -> Path:
    return Path(data_dir) / _TERRAIN_FILENAME


def load_terrain_overrides(data_dir: Path) -> dict[str, str]:
    """Le correzioni di Andrea, `{"<activity_id>": "<terrain>"}`."""
    return _load_json_map(_terrain_path(data_dir))


def save_terrain_override(data_dir: Path, activity_id: int, terrain: str | None) -> None:
    """Salva la correzione di un'attivita'; con `None` la toglie (si torna
    alla stima). Scrive un file temporaneo e lo sostituisce, sotto un lock:
    due richieste insieme non lasciano il JSON a meta'."""
    if terrain is not None and terrain not in TERRAINS:
        raise ValueError(f"Unknown terrain: {terrain}")
    path = _terrain_path(data_dir)
    with _write_lock:
        overrides = load_terrain_overrides(data_dir)
        if terrain is None:
            overrides.pop(str(activity_id), None)
        else:
            overrides[str(activity_id)] = terrain
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".activity_terrain.", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(overrides, f, indent=2, sort_keys=True)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
