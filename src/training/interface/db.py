"""SQLite cache of parsed FIT activity data (data/activities.db).

Parsing FIT files with fitparse is slow (pure-Python, non-lazy: even the
small "session" summary message forces a full parse of the file, ~1s for
a ~450KB/~2800-sample activity). This module caches that parsed data in
SQLite so normal reads are indexed lookups instead of a FIT re-parse. The
.fit files remain the source of truth; the DB is always rebuildable from
them via rebuild().

Two entry points matter to callers: list_activities() and
load_activity_records() — both call sync() first, so new .fit files are
picked up automatically without a manual cache-clear or restart.

The Streamlit pages do not call list_activities() directly: passano da
data.load_activities(), che ci mette davanti una cache con un ttl breve per
non rifare la scansione a ogni rerun.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from training.garmin.config import DATA_DIR
from training.interface.fit import (
    LOCAL_TZ,
    activity_id_from_path,
    list_activity_files,
    load_activity_names,
    load_activity_summary,
    load_activity_types,
)
from training.interface.fit import load_activity_records as _parse_fit_records

DB_FILENAME = "activities.db"

# Il FIT di un'attivita' registrata seguendo un percorso preimpostato ha
# sport "generic" (sotto-tipo "navigate"): in quel caso lo sport vero lo
# sa solo Garmin Connect, che lo chiama con queste chiavi.
_GENERIC_SPORTS = {None, "", "generic"}
GARMIN_TYPE_TO_SPORT = {
    "running": "running",
    "trail_running": "running",
    "treadmill_running": "running",
    "track_running": "running",
    "street_running": "running",
    "cycling": "cycling",
    "road_biking": "cycling",
    "mountain_biking": "cycling",
    "gravel_cycling": "cycling",
    "cyclocross": "cycling",
    "indoor_cycling": "cycling",
    "virtual_ride": "cycling",
    "e_bike_fitness": "cycling",
    "hiking": "hiking",
    "mountaineering": "hiking",
    "walking": "walking",
    "casual_walking": "walking",
    "speed_walking": "walking",
    "cross_country_skiing": "cross_country_skiing",
    "cross_country_skiing_ws": "cross_country_skiing",
    "skate_skiing": "cross_country_skiing",
    "backcountry_skiing": "cross_country_skiing",
}


def sport_from_garmin_type(sport: str | None, type_key: str | None) -> str | None:
    """Lo sport da mostrare. Vince il tipo di Garmin Connect, quando lo
    conosciamo: e' quello che l'utente puo' correggere dopo (una corsa
    registrata col profilo "Escursione" resta "hiking" nel FIT per sempre,
    anche se su Connect diventa "street_running"). Il FIT resta la risposta
    quando Connect non dice niente o usa una chiave che non mappiamo; se il
    FIT e' "generic" si mostra la chiave di Connect cosi' com'e'."""
    if type_key in GARMIN_TYPE_TO_SPORT:
        return GARMIN_TYPE_TO_SPORT[type_key]
    if sport not in _GENERIC_SPORTS or not type_key:
        return sport
    return type_key

# Bump when parsing/derivation logic changes (e.g. the UTC->local timezone
# fix): sync() compares this against the value stored in schema_meta and
# transparently triggers a full rebuild() when they differ, instead of
# silently serving rows computed under old logic.
#
# "3": colonna `vo2max`, letta dal messaggio 140 dei file FIT. I file gia' in
# cache non la avevano, e sync() rilegge solo i file nuovi: il salto di versione
# e' quello che li fa rileggere tutti, una volta.
#
# "4": `avg_speed_kmh` leggeva solo il campo `avg_speed`, che l'orologio nuovo
# non scrive piu' (vedi `fit._avg_speed_kmh`): 45 attivita' erano in cache con
# 0 km/h al posto della velocita'.
LOGIC_VERSION = "4"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    activity_id       INTEGER PRIMARY KEY,
    path              TEXT NOT NULL,
    sport             TEXT,
    sub_sport         TEXT,
    start_time        TEXT NOT NULL,
    total_distance_km REAL,
    total_time_min    REAL,
    avg_heart_rate    INTEGER,
    max_heart_rate    INTEGER,
    avg_speed_kmh     REAL,
    total_calories    INTEGER,
    total_ascent_m    REAL,
    total_descent_m   REAL,
    vo2max            REAL,
    activity_name     TEXT,
    parsed_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activities_start_time ON activities(start_time);
CREATE INDEX IF NOT EXISTS idx_activities_sport ON activities(sport);

CREATE TABLE IF NOT EXISTS records (
    activity_id INTEGER NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    ts_epoch    INTEGER NOT NULL,
    heart_rate  INTEGER,
    speed_kmh   REAL,
    altitude_m  REAL,
    cadence     INTEGER,
    power       INTEGER,
    lat         REAL,
    lon         REAL,
    distance_km REAL,
    PRIMARY KEY (activity_id, ts_epoch)
) WITHOUT ROWID;
"""

_RECORD_COLUMNS = ("heart_rate", "speed_kmh", "altitude_m", "cadence", "power", "lat", "lon", "distance_km")


def _db_path(data_dir: Path) -> Path:
    return Path(data_dir) / DB_FILENAME


def _connect(data_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(data_dir))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    return conn


def _local_to_epoch(ts) -> int:
    localized = pd.Timestamp(ts).tz_localize(LOCAL_TZ, ambiguous=False, nonexistent="shift_forward")
    return int(localized.timestamp())


def _epoch_to_local(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=LOCAL_TZ).replace(tzinfo=None)


def _clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _insert_activity(conn: sqlite3.Connection, summary: dict, name: str | None, parsed_at: str) -> None:
    payload = dict(summary)
    payload["start_time"] = payload["start_time"].isoformat(sep=" ")
    payload["activity_name"] = name
    payload["parsed_at"] = parsed_at
    conn.execute(
        """
        INSERT INTO activities (
            activity_id, path, sport, sub_sport, start_time, total_distance_km,
            total_time_min, avg_heart_rate, max_heart_rate, avg_speed_kmh,
            total_calories, total_ascent_m, total_descent_m, vo2max, activity_name, parsed_at
        ) VALUES (
            :activity_id, :path, :sport, :sub_sport, :start_time, :total_distance_km,
            :total_time_min, :avg_heart_rate, :max_heart_rate, :avg_speed_kmh,
            :total_calories, :total_ascent_m, :total_descent_m, :vo2max, :activity_name, :parsed_at
        )
        ON CONFLICT(activity_id) DO UPDATE SET
            path=excluded.path, sport=excluded.sport, sub_sport=excluded.sub_sport,
            start_time=excluded.start_time, total_distance_km=excluded.total_distance_km,
            total_time_min=excluded.total_time_min, avg_heart_rate=excluded.avg_heart_rate,
            max_heart_rate=excluded.max_heart_rate, avg_speed_kmh=excluded.avg_speed_kmh,
            total_calories=excluded.total_calories, total_ascent_m=excluded.total_ascent_m,
            total_descent_m=excluded.total_descent_m, vo2max=excluded.vo2max,
            activity_name=excluded.activity_name,
            parsed_at=excluded.parsed_at
        """,
        payload,
    )


def _insert_records(conn: sqlite3.Connection, activity_id: int, records: pd.DataFrame) -> None:
    if records.empty:
        return
    rows = [
        (activity_id, _local_to_epoch(ts), *(_clean(getattr(r, col)) for col in _RECORD_COLUMNS))
        for ts, r in records.iterrows()
    ]
    conn.executemany(
        f"INSERT OR IGNORE INTO records (activity_id, ts_epoch, {', '.join(_RECORD_COLUMNS)}) "
        f"VALUES ({', '.join(['?'] * (2 + len(_RECORD_COLUMNS)))})",
        rows,
    )


def _parse_and_store(
    conn: sqlite3.Connection, path: Path, names: dict, types: dict, parsed_at: str
) -> bool:
    summary = load_activity_summary(path)
    if summary["activity_id"] is None or summary["start_time"] is None:
        return False
    records = _parse_fit_records(path)
    activity_id = str(summary["activity_id"])
    summary["sport"] = sport_from_garmin_type(summary.get("sport"), types.get(activity_id))
    _insert_activity(conn, summary, names.get(activity_id), parsed_at)
    _insert_records(conn, summary["activity_id"], records)
    return True


def rebuild(data_dir: Path = DATA_DIR) -> int:
    """Drop and repopulate the cache from every .fit file in data_dir.
    Used after a parsing-logic change (LOGIC_VERSION bump) or on first run."""
    data_dir = Path(data_dir)
    db_path = _db_path(data_dir)
    db_path.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)

    conn = _connect(data_dir)
    try:
        names = load_activity_names(data_dir)
        types = load_activity_types(data_dir)
        parsed_at = datetime.now().isoformat(sep=" ")
        count = sum(
            _parse_and_store(conn, p, names, types, parsed_at) for p in list_activity_files(data_dir)
        )
        conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('logic_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (LOGIC_VERSION,),
        )
        conn.commit()
    finally:
        conn.close()
    return count


def sync(data_dir: Path = DATA_DIR) -> int:
    """Parse and cache only .fit files not yet in the DB (by activity_id,
    read cheaply from the filename, no FIT parse needed). Also refreshes
    activity_name for already-cached rows from activity_names.json. Falls
    back to a full rebuild() if the cache predates the current
    LOGIC_VERSION."""
    data_dir = Path(data_dir)
    conn = _connect(data_dir)
    try:
        row = conn.execute("SELECT value FROM schema_meta WHERE key='logic_version'").fetchone()
        if row is None or row[0] != LOGIC_VERSION:
            conn.close()
            return rebuild(data_dir)

        existing_ids = {r[0] for r in conn.execute("SELECT activity_id FROM activities")}
        new_paths = [p for p in list_activity_files(data_dir) if activity_id_from_path(p) not in existing_ids]

        names = load_activity_names(data_dir)
        types = load_activity_types(data_dir)
        parsed_at = datetime.now().isoformat(sep=" ")
        added = sum(_parse_and_store(conn, p, names, types, parsed_at) for p in new_paths)

        conn.executemany(
            "UPDATE activities SET activity_name=? WHERE activity_id=?",
            [(name, int(activity_id)) for activity_id, name in names.items()],
        )
        # Anche il tipo puo' cambiare dopo il download (attivita' riclassificata
        # su Garmin Connect), quindi si aggiorna a ogni sync come il nome: un
        # tipo che mappiamo vale su qualunque riga, uno sconosciuto solo dove
        # il FIT non sapeva lo sport.
        conn.executemany(
            "UPDATE activities SET sport=? WHERE activity_id=?",
            [
                (GARMIN_TYPE_TO_SPORT[type_key], int(activity_id))
                for activity_id, type_key in types.items()
                if type_key in GARMIN_TYPE_TO_SPORT
            ],
        )
        conn.executemany(
            "UPDATE activities SET sport=? WHERE activity_id=? AND sport IN ('generic', '')",
            [
                (type_key, int(activity_id))
                for activity_id, type_key in types.items()
                if type_key and type_key not in GARMIN_TYPE_TO_SPORT
            ],
        )
        conn.commit()
        return added
    finally:
        conn.close()


def list_activities(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    data_dir = Path(data_dir)
    sync(data_dir)
    conn = _connect(data_dir)
    try:
        df = pd.read_sql_query("SELECT * FROM activities ORDER BY start_time DESC", conn)
    finally:
        conn.close()
    if not df.empty:
        df["start_time"] = pd.to_datetime(df["start_time"])
    return df


def load_activity_records(activity_id: int, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    data_dir = Path(data_dir)
    conn = _connect(data_dir)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM records WHERE activity_id=? ORDER BY ts_epoch",
            conn,
            params=(int(activity_id),),
        )
    finally:
        conn.close()
    df["timestamp"] = df["ts_epoch"].map(_epoch_to_local)
    return df.drop(columns=["activity_id", "ts_epoch"]).set_index("timestamp")
