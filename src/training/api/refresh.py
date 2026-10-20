"""Il tasto Refresh della Day (todo 41, riscritto dal todo 44): aggiorna i
dati e rifa' il report di un giorno, in background.

Dal todo 44 il report non lo scrive piu' un agente solo: ogni sezione ha il
suo (`api/sections.py`) e scrive il proprio frammento in
`summary/01.daily/<giorno>/`. Qui c'e' chi li lancia e chi ne tiene lo stato.

Gli agenti girano **in fila**, non insieme: a parita' di lavoro i gettoni
sono gli stessi, ma un giro che va storto si ferma invece di bruciare le
sessioni rimaste, e non si rischiano i limiti di frequenza. Un giro completo
sono sette agenti da circa un minuto l'uno.

I fatti del giorno si preparano **una volta sola** (`make daily_data` in un
file temporaneo) e gli agenti leggono quello: sette `make daily_data`
vorrebbero dire sette sincronizzazioni del database e della salute.

Un lavoro alla volta, con lo stato in memoria: se il server si riavvia torna
`idle`. Lo stdin e' chiuso, cosi' un login Garmin scaduto non si ferma ad
aspettare una password: `update_activity` fallisce e si va avanti con i dati
locali."""

import argparse
import json
import shutil
import subprocess
import tempfile
import threading
from datetime import date, datetime
from pathlib import Path

from training.api.cache import invalidate
from training.api.daily import daily_payload
from training.api.sections import BY_KEY, RUN_ORDER, Section

# Quanto si da' a un agente prima di considerarlo perso. Uno solo, non il
# giro intero: in fila sette agenti lenti farebbero piu' di un'ora.
TIMEOUT_SECONDS = 10 * 60
# Il tempo per scaricare i dati nuovi da Garmin, prima degli agenti.
UPDATE_TIMEOUT_SECONDS = 15 * 60
# Le righe finali dell'output tenute quando qualcosa fallisce.
MESSAGE_LINES = 5

# Agli agenti serve leggere (i fatti del giorno e i frammenti degli altri) e
# scrivere il proprio frammento. I permessi sui file si controllano solo con
# regole `Edit(...)`: una regola `Write(...)` Claude Code la accetta e non la
# guarda mai. Niente Bash: l'aggiornamento dei dati e i fatti del giorno li
# prepara questo modulo, una volta per tutti.
ALLOWED_TOOLS = ["Read", "Edit(summary/01.daily/**)"]

# Le regole che valgono per tutte le sezioni (voce, numeri, fasce) stanno in
# un file solo invece che copiate in sette prompt: `--append-system-prompt-file`
# le attacca al prompt dell'agente. Provato il 2026-10-20 su un agente finto:
# con il flag risponde la parola del file, senza no.
STYLE_FILE = ".claude/agents/_style.md"

_lock = threading.Lock()


def _blank_section() -> dict:
    return {"status": "idle", "started": None, "finished": None, "message": None}


def _blank_state() -> dict:
    return {
        "status": "idle",
        "day": None,
        "started": None,
        "finished": None,
        "message": None,
        "sections": {section.key: _blank_section() for section in RUN_ORDER},
    }


_state: dict = _blank_state()


def status() -> dict:
    """Lo stato del lavoro, una copia: quello d'insieme e quello di ogni
    sezione."""
    with _lock:
        copy = dict(_state)
        copy["sections"] = {key: dict(value) for key, value in _state["sections"].items()}
        return copy


def start(
    day: date,
    repo_root: Path,
    summary_dir: Path,
    data_dir: Path,
    keys: tuple[str, ...] | None = None,
) -> dict:
    """Lancia il lavoro per `day`, se non ce n'e' gia' uno in corso. Rende lo
    stato: quello nuovo, o quello del lavoro che sta gia' girando.

    `keys` sono le sezioni da rifare, nell'ordine di `RUN_ORDER`; senza, si
    rifanno tutte."""
    sections = [s for s in RUN_ORDER if keys is None or s.key in keys]
    with _lock:
        if _state["status"] == "running":
            copy = dict(_state)
            copy["sections"] = {k: dict(v) for k, v in _state["sections"].items()}
            return copy
        now = datetime.now()
        _state.update(status="running", day=day, started=now, finished=None, message=None)
        # Le sezioni che non si rifanno restano com'erano: lo stato dice
        # quello che e' successo l'ultima volta, non una bugia.
        for section in sections:
            _state["sections"][section.key] = {
                "status": "idle", "started": None, "finished": None, "message": None
            }
        started = _state["started"]
    thread = threading.Thread(
        target=_run,
        args=(day, started, repo_root, summary_dir, data_dir, tuple(sections)),
        daemon=True,
    )
    thread.start()
    return status()


def _set(key: str, **fields) -> None:
    with _lock:
        _state["sections"][key].update(**fields)


def _run(
    day: date,
    started: datetime,
    repo_root: Path,
    summary_dir: Path,
    data_dir: Path,
    sections: tuple[Section, ...],
    update: bool = True,
) -> None:
    failed: list[str] = []
    message = None
    with tempfile.TemporaryDirectory() as tmp:
        facts = Path(tmp) / f"{day.isoformat()}.json"
        ok, problem = _prepare(day, repo_root, data_dir, facts, update)
        if not ok:
            message = problem
        else:
            folder = Path(summary_dir) / "01.daily" / day.isoformat()
            folder.mkdir(parents=True, exist_ok=True)
            for section in sections:
                began = datetime.now()
                _set(section.key, status="running", started=began, finished=None, message=None)
                good, problem = _write_section(section, day, repo_root, facts, folder, began)
                _set(
                    section.key,
                    status="done" if good else "failed",
                    finished=datetime.now(),
                    message=problem,
                )
                if not good:
                    failed.append(section.key)
    if failed and not message:
        message = "These sections kept their previous text: " + ", ".join(failed)
    with _lock:
        _state.update(
            status="failed" if (failed or message) else "done",
            finished=datetime.now(),
            message=message,
        )


def _prepare(
    day: date, repo_root: Path, data_dir: Path, facts: Path, update: bool = True
) -> tuple[bool, str | None]:
    """Scarica i dati nuovi e scrive i fatti del giorno in `facts`.

    `update_activity` chiama Garmin: se fallisce (niente rete, login scaduto)
    non ci si ferma, si va avanti con i dati locali. Con `update` falso non si
    chiama affatto: si riscrive il testo sui dati che ci sono gia'.

    I fatti sono quelli di `api/daily.daily_payload`, cioe' **gli stessi che
    riceve la pagina**, non quelli di `make daily_data`: quel JSON non ha il
    blocco `fitness`, e l'agente di Fitness scriveva che i punteggi non
    c'erano mentre la card accanto li mostrava."""
    if update:
        subprocess.run(
            ["make", "update_activity"],
            cwd=repo_root, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=UPDATE_TIMEOUT_SECONDS, check=False,
        )
        # I file sono cambiati sotto la cache: senza questo i fatti sarebbero
        # quelli di prima dello scaricamento.
        invalidate(data_dir)
    try:
        payload = daily_payload(day, data_dir)
    except Exception as exc:  # noqa: BLE001 - qualunque cosa, il lavoro si ferma qui
        return False, f"The facts of the day could not be built: {exc}"
    facts.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    return True, None


def _prompt(section: Section, day: date, facts: Path, folder: Path) -> str:
    where = f"Write the body of the section (no `## ` heading) to {folder / f'{section.key}.md'}."
    if section.reads_fragments:
        return (
            f"Write the {section.title} part of the daily report for {day.isoformat()}. "
            f"The other sections are already written in {folder}: read them, they are your "
            f"input. The facts of the day, if you need them, are in {facts}. {where}"
        )
    return (
        f"Write the {section.title} section of the daily report for {day.isoformat()}. "
        f"The facts of the day are in {facts}: read that file, do not run anything. {where}"
    )


def _write_section(
    section: Section, day: date, repo_root: Path, facts: Path, folder: Path, began: datetime
) -> tuple[bool, str | None]:
    claude = shutil.which("claude")
    if claude is None:
        return False, "The claude command is not on the PATH of the API."
    command = [
        claude, "-p", "--agent", section.agent,
        "--append-system-prompt-file", str(repo_root / STYLE_FILE),
        "--allowedTools", *ALLOWED_TOOLS,
        "--", _prompt(section, day, facts, folder),
    ]
    try:
        result = subprocess.run(
            command, cwd=repo_root, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, f"{section.agent} did not finish in {TIMEOUT_SECONDS // 60} minutes."
    if result.returncode != 0:
        return False, _tail(result) or f"{section.agent} exited with {result.returncode}."
    # L'uscita 0 non basta: il frammento deve essere stato scritto adesso.
    fragment = folder / f"{section.key}.md"
    if not (fragment.exists() and fragment.stat().st_mtime >= began.timestamp()):
        return False, f"{section.agent} finished without writing {fragment.name}."
    return True, None


def _tail(result: subprocess.CompletedProcess) -> str:
    lines = (result.stderr.strip() or result.stdout.strip()).splitlines()
    return "\n".join(lines[-MESSAGE_LINES:])


def section_keys(name: str | None) -> tuple[str, ...] | None:
    """Le chiavi da rifare: tutte con `None`, una sola col suo nome. Alza
    `KeyError` su un nome che non esiste."""
    if name is None:
        return None
    return (BY_KEY[name].key,)


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data non valida: {text!r} (serve YYYY-MM-DD)")


def main() -> None:
    """Rifa' il report di un giorno da terminale, senza passare dall'API.

    Lo stesso lavoro del tasto Refresh, ma in primo piano e senza server:
    serve per rifare un report a mano e per provare l'impianto. Stampa come
    e' andata sezione per sezione, ed esce 1 se qualcuna e' fallita."""
    from training.api.context import REPO_ROOT, SUMMARY_DIR
    from training.garmin.config import DATA_DIR

    parser = argparse.ArgumentParser(description="Rifa' il report giornaliero, una sezione o tutte.")
    parser.add_argument("--day", type=_day, help="il giorno (YYYY-MM-DD); di default oggi")
    parser.add_argument("--section", help="una sola sezione: " + ", ".join(BY_KEY))
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="non richiamare Garmin: riscrive il testo sui dati che ci sono gia'",
    )
    args = parser.parse_args()
    day = args.day or date.today()
    if day > date.today():
        parser.error(f"il {day} non e' ancora arrivato")
    try:
        keys = section_keys(args.section)
    except KeyError:
        parser.error(f"sezione sconosciuta: {args.section!r} (ce ne sono {', '.join(BY_KEY)})")
    sections = tuple(s for s in RUN_ORDER if keys is None or s.key in keys)

    print(f"Report del {day}: {len(sections)} sezioni, una alla volta.")
    _run(day, datetime.now(), REPO_ROOT, SUMMARY_DIR, DATA_DIR, sections, not args.no_update)
    state = status()
    for section in sections:
        row = state["sections"][section.key]
        note = f"  {row['message']}" if row["message"] else ""
        print(f"  {section.key:9} {row['status']}{note}")
    print(state["message"] or "Fatto.")
    raise SystemExit(1 if state["status"] == "failed" else 0)
