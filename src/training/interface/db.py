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
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from training.interface.fit import (
    LOCAL_TZ,
    activity_id_from_path,
    list_activity_files,
    load_activity_names,
    load_activity_summary,
)
from training.interface.fit import load_activity_records as _parse_fit_records

DB_FILENAME = "activities.db"

# Bump when parsing/derivation logic changes (e.g. the UTC->local timezone
# fix): sync() compares this against the value stored in schema_meta and
# transparently triggers a full rebuild() when they differ, instead of
# silently serving rows computed under old logic.
LOGIC_VERSION = "1"

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
            total_calories, total_ascent_m, total_descent_m, activity_name, parsed_at
        ) VALUES (
            :activity_id, :path, :sport, :sub_sport, :start_time, :total_distance_km,
            :total_time_min, :avg_heart_rate, :max_heart_rate, :avg_speed_kmh,
            :total_calories, :total_ascent_m, :total_descent_m, :activity_name, :parsed_at
        )
        ON CONFLICT(activity_id) DO UPDATE SET
            path=excluded.path, sport=excluded.sport, sub_sport=excluded.sub_sport,
            start_time=excluded.start_time, total_distance_km=excluded.total_distance_km,
            total_time_min=excluded.total_time_min, avg_heart_rate=excluded.avg_heart_rate,
            max_heart_rate=excluded.max_heart_rate, avg_speed_kmh=excluded.avg_speed_kmh,
            total_calories=excluded.total_calories, total_ascent_m=excluded.total_ascent_m,
            total_descent_m=excluded.total_descent_m, activity_name=excluded.activity_name,
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


def _parse_and_store(conn: sqlite3.Connection, path: Path, names: dict, parsed_at: str) -> bool:
    summary = load_activity_summary(path)
    if summary["activity_id"] is None or summary["start_time"] is None:
        return False
    records = _parse_fit_records(path)
    _insert_activity(conn, summary, names.get(str(summary["activity_id"])), parsed_at)
    _insert_records(conn, summary["activity_id"], records)
    return True


def rebuild(data_dir: Path = Path("data")) -> int:
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
        parsed_at = datetime.now().isoformat(sep=" ")
        count = sum(_parse_and_store(conn, p, names, parsed_at) for p in list_activity_files(data_dir))
        conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('logic_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (LOGIC_VERSION,),
        )
        conn.commit()
    finally:
        conn.close()
    return count


def sync(data_dir: Path = Path("data")) -> int:
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
        parsed_at = datetime.now().isoformat(sep=" ")
        added = sum(_parse_and_store(conn, p, names, parsed_at) for p in new_paths)

        conn.executemany(
            "UPDATE activities SET activity_name=? WHERE activity_id=?",
            [(name, int(activity_id)) for activity_id, name in names.items()],
        )
        conn.commit()
        return added
    finally:
        conn.close()


def list_activities(data_dir: Path = Path("data")) -> pd.DataFrame:
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


def load_activity_records(activity_id: int, data_dir: Path = Path("data")) -> pd.DataFrame:
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
