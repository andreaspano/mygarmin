"""Cache SQLite delle metriche giornaliere di salute (`health_daily`).

La tabella sta in `activities.db`, accanto ad `activities`, ma si costruisce
dai JSON di `DATA_DIR/health/` come `activities` si costruisce dai `.fit`: i
JSON restano la fonte, e la tabella si puo' sempre buttare e rifare. Il
parsing e' in `health.py`; qui c'e' solo la cache, separata da `db.py` perche'
le due restino indipendenti: un cambio al parsing della salute svuota
`health_daily` e basta, senza rileggere i FIT.

Un `rebuild()` dei FIT cancella invece il file intero, tabella compresa: va
bene, il primo `sync_health()` dopo la riempie di nuovo dai JSON.

NULL vuol dire "non lo sappiamo", mai zero: lo stesso contratto di
`health._dig()`.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from training.garmin.config import DATA_DIR
from training.interface.db import _connect as _connect_db
from training.interface.health import (
    COLUMNS,
    TEXT_COLUMNS,
    _day_paths,
    _day_row,
    available_days,
)

# Da cambiare quando cambia il parsing della salute in `health.py`:
# `sync_health()` lo confronta con quello in `schema_meta` (chiave
# `health_logic_version`, separata da `logic_version` dei FIT) e, se sono
# diversi, svuota `health_daily` e la riempie di nuovo.
HEALTH_LOGIC_VERSION = "1"

_VERSION_KEY = "health_logic_version"


def _column_type(name: str) -> str:
    return "TEXT" if name in TEXT_COLUMNS else "REAL"


_HEALTH_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS health_daily (\n"
    "    day TEXT PRIMARY KEY,\n"
    + "".join(f"    {name} {_column_type(name)},\n" for name in COLUMNS)
    + "    source_mtime REAL NOT NULL,\n"
    "    parsed_at TEXT NOT NULL\n"
    ") WITHOUT ROWID;\n"
)

_UPSERT = (
    f"INSERT INTO health_daily (day, {', '.join(COLUMNS)}, source_mtime, parsed_at) "
    f"VALUES (:day, {', '.join(':' + name for name in COLUMNS)}, :source_mtime, :parsed_at) "
    "ON CONFLICT(day) DO UPDATE SET "
    + ", ".join(f"{name}=excluded.{name}" for name in [*COLUMNS, "source_mtime", "parsed_at"])
)


def _connect(data_dir: Path) -> sqlite3.Connection:
    """La connessione di `db.py`, con in piu' la tabella della salute."""
    conn = _connect_db(data_dir)
    conn.executescript(_HEALTH_SCHEMA)
    return conn


def _source_mtime(health_dir: Path, day: str) -> float | None:
    """L'mtime piu' recente fra i file del giorno, o None se non ce n'e'."""
    mtimes = []
    for path in _day_paths(health_dir, day).values():
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else None


def sync_health(data_dir: Path = DATA_DIR) -> int:
    """Porta `health_daily` in pari con i JSON; torna quanti giorni ha riletto.

    Un giorno si rilegge solo se manca dalla tabella o se uno dei suoi file e'
    piu' nuovo della riga: `export_daily_health(..., force_dates={today})`
    riscrive i file di oggi a ogni giro, e una riga messa in cache una volta
    per giorno resterebbe vecchia. Se `HEALTH_LOGIC_VERSION` non coincide con
    quella salvata, prima si svuota la tabella."""
    data_dir = Path(data_dir)
    health_dir = data_dir / "health"
    conn = _connect(data_dir)
    try:
        row = conn.execute("SELECT value FROM schema_meta WHERE key=?", (_VERSION_KEY,)).fetchone()
        if row is None or row[0] != HEALTH_LOGIC_VERSION:
            conn.execute("DELETE FROM health_daily")
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_VERSION_KEY, HEALTH_LOGIC_VERSION),
            )

        cached = dict(conn.execute("SELECT day, source_mtime FROM health_daily"))
        days = [day.isoformat() for day in available_days(data_dir)]

        parsed_at = datetime.now().isoformat(sep=" ")
        rows = []
        for day in days:
            mtime = _source_mtime(health_dir, day)
            if mtime is None:
                continue
            if day in cached and mtime <= cached[day]:
                continue
            rows.append(
                {"day": day, **_day_row(health_dir, day), "source_mtime": mtime, "parsed_at": parsed_at}
            )
        conn.executemany(_UPSERT, rows)

        # Un giorno i cui file non ci sono piu' non deve restare in cache.
        gone = set(cached) - set(days)
        conn.executemany("DELETE FROM health_daily WHERE day=?", [(day,) for day in gone])

        conn.commit()
        return len(rows)
    finally:
        conn.close()


def load_health_db(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Le metriche di salute da `health_daily`, dopo un `sync_health()`.

    Stessa forma che `health.load_health()` ha sempre restituito: indice
    `DatetimeIndex` di nome `day`, continuo dal primo all'ultimo giorno (i
    buchi a `NaN`), colonne `COLUMNS`. DataFrame vuoto con le colonne giuste
    se non c'e' niente."""
    data_dir = Path(data_dir)
    sync_health(data_dir)
    conn = _connect(data_dir)
    try:
        cursor = conn.execute(f"SELECT day, {', '.join(COLUMNS)} FROM health_daily ORDER BY day")
        records = cursor.fetchall()
    finally:
        conn.close()

    if not records:
        return pd.DataFrame(columns=COLUMNS, index=pd.DatetimeIndex([], name="day"))

    days = [datetime.fromisoformat(r[0]).date() for r in records]
    rows = [dict(zip(COLUMNS, r[1:])) for r in records]
    frame = pd.DataFrame(rows, columns=COLUMNS, index=pd.DatetimeIndex(days, name="day"))
    # Le colonne numeriche sempre `float`, anche quando sono tutte NULL (la
    # saturazione, se l'orologio non la misura): NaN e non None.
    numeric = [name for name in COLUMNS if name not in TEXT_COLUMNS]
    frame[numeric] = frame[numeric].astype(float)
    # Il calendario completo fra il primo e l'ultimo giorno: `reindex` mette
    # NaN dove il giorno non c'era.
    full_range = pd.date_range(days[0], days[-1], freq="D", name="day")
    return frame.reindex(full_range)
