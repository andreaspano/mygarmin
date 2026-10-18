"""Il tasto Refresh della Day (todo 41): aggiorna i dati e riscrive il report
di un giorno, in background.

Il lavoro lo fa l'agente `fitness-status` (`.claude/agents/`), lanciato con
`claude -p`: il suo primo passo e' `make update_activity`, l'ultimo salva
`summary/01.daily/<giorno>.md`. Qui c'e' solo chi lo lancia e ne tiene lo
stato.

Un lavoro alla volta, con lo stato in memoria: se il server si riavvia torna
`idle`. Lo stdin e' chiuso, cosi' un login Garmin scaduto non si ferma ad
aspettare una password: `update_activity` fallisce e l'agente va avanti con
i dati locali, come scritto nelle sue istruzioni."""

import shutil
import subprocess
import threading
from datetime import date, datetime
from pathlib import Path

from training.api.cache import invalidate

# L'agente impiega qualche minuto; oltre questo tempo il lavoro e' perso.
TIMEOUT_SECONDS = 15 * 60
# Le righe finali dell'output tenute quando il lavoro fallisce.
MESSAGE_LINES = 5

# Solo cio' che serve all'agente: l'aggiornamento, i fatti del giorno e il
# file del report. Le letture nel repo sono gia' permesse.
ALLOWED_TOOLS = [
    "Bash(make update_activity)",
    "Bash(make -s daily_data:*)",
    "Read",
    "Edit(summary/01.daily/**)",
]

_lock = threading.Lock()
_state: dict = {"status": "idle", "day": None, "started": None, "finished": None, "message": None}


def status() -> dict:
    """Lo stato del lavoro, una copia."""
    with _lock:
        return dict(_state)


def start(day: date, repo_root: Path, summary_dir: Path, data_dir: Path) -> dict:
    """Lancia il lavoro per `day`, se non ce n'e' gia' uno in corso. Rende lo
    stato: quello nuovo, o quello del lavoro che sta gia' girando."""
    with _lock:
        if _state["status"] == "running":
            return dict(_state)
        _state.update(status="running", day=day, started=datetime.now(), finished=None, message=None)
        started = _state["started"]
    thread = threading.Thread(
        target=_run, args=(day, started, repo_root, summary_dir, data_dir), daemon=True
    )
    thread.start()
    return status()


def _run(day: date, started: datetime, repo_root: Path, summary_dir: Path, data_dir: Path) -> None:
    ok, message = _call_agent(day, repo_root)
    report = summary_dir / "01.daily" / f"{day.isoformat()}.md"
    # L'uscita 0 non basta: il report deve essere stato riscritto adesso.
    if ok and not (report.exists() and report.stat().st_mtime >= started.timestamp()):
        ok, message = False, "The agent finished without writing the report."
    invalidate(data_dir)
    with _lock:
        _state.update(status="done" if ok else "failed", finished=datetime.now(), message=message)


def _call_agent(day: date, repo_root: Path) -> tuple[bool, str | None]:
    claude = shutil.which("claude")
    if claude is None:
        return False, "The claude command is not on the PATH of the API."
    command = [
        claude, "-p", "--agent", "fitness-status",
        "--allowedTools", *ALLOWED_TOOLS,
        "--", f"Write the daily report for {day.isoformat()}.",
    ]
    try:
        result = subprocess.run(
            command, cwd=repo_root, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, f"The agent did not finish in {TIMEOUT_SECONDS // 60} minutes."
    if result.returncode != 0:
        lines = (result.stderr.strip() or result.stdout.strip()).splitlines()
        return False, "\n".join(lines[-MESSAGE_LINES:]) or f"claude exited with {result.returncode}."
    return True, None
