"""Chi scrive i report: il tasto Refresh della Day (todo 41, riscritto dal 44
e dal 47), i due giri di cron e, dal todo 53, anche il report della
settimana.

Dal todo 44 il report non lo scrive piu' un agente solo: ogni sezione ha il
suo (`api/sections.py`) e scrive il proprio frammento nella cartella del
periodo — `summary/01.daily/<giorno>/`, `summary/02.weekly/<lunedi>/`. Qui
c'e' chi li lancia e chi ne tiene lo stato.

**Un ciclo solo per il giorno e per la settimana** (todo 53): cambiano le
sezioni, la cartella, i fatti e la voce, e sono tutte cose che stanno in
`sections.Report`. Due cicli quasi uguali che divergono nel tempo sono il
modo sicuro di avere due difetti diversi.

Gli agenti girano **in fila**, non insieme: a parita' di lavoro i gettoni
sono gli stessi, ma un giro che va storto si ferma invece di bruciare le
sessioni rimaste, e non si rischiano i limiti di frequenza. Un giro completo
sono otto agenti da circa un minuto l'uno.

Dal todo 47 a lanciare non e' piu' solo il tasto: le righe di cron
(`deploy/crontab`) fanno il giro del mattino e quello della sera, che non
sono uguali, e il lunedi e la domenica ci si attacca la settimana. Da li'
vengono tre cose che il tasto da solo non chiedeva:

- il **momento**, che e' la voce con cui Next e Summary parlano;
- il lock **su file**, perche' il guardiano in memoria vale dentro un solo
  processo e il giro di cron e' un processo diverso dall'API;
- l'esito dello **scaricamento** nello stato, perche' senza nessuno a
  guardare un login scaduto scriverebbe report su dati vecchi in silenzio.

I fatti si preparano **una volta sola** (in un file temporaneo) e gli agenti
leggono quello: otto letture vorrebbero dire otto sincronizzazioni del
database e della salute.

Lo stato resta in memoria: se il server si riavvia torna `idle`. Lo stdin e'
chiuso, cosi' un login Garmin scaduto non si ferma ad aspettare una
password."""

import argparse
import contextlib
import fcntl
import json
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

from training.api.cache import invalidate
from training.api.sections import (
    DAILY,
    WEEKLY,
    Report,
    Section,
    moment_at,
    week_moment_at,
)

# Quanto si da' a un agente prima di considerarlo perso. Uno solo, non il
# giro intero: in fila otto agenti lenti farebbero piu' di un'ora.
TIMEOUT_SECONDS = 10 * 60
# Il tempo per scaricare i dati nuovi da Garmin, prima degli agenti.
UPDATE_TIMEOUT_SECONDS = 15 * 60
# Le righe finali dell'output tenute quando qualcosa fallisce.
MESSAGE_LINES = 5

# Le regole che valgono per tutte le sezioni (voce, numeri, fasce) stanno in
# un file solo invece che copiate in otto prompt: `--append-system-prompt-file`
# le attacca al prompt dell'agente. Provato il 2026-10-20 su un agente finto:
# con il flag risponde la parola del file, senza no.
STYLE_FILE = ".claude/agents/_style.md"

_lock = threading.Lock()

# Il guardiano "un lavoro alla volta" di `_state` vale dentro **un processo
# solo**: l'API e il comando da terminale (quello che lanciano i timer del
# todo 47) sono processi diversi, e senza questo file partirebbero due
# `make update_activity` e due serie di agenti sugli stessi frammenti. Il
# lock sta nella cartella dei dati, accanto ad `activities.db`, e non si
# aspetta mai: chi lo trova occupato se ne va. Vale anche fra giorno e
# settimana: il giro del lunedi li fa uno dopo l'altro, non insieme.
LOCK_FILENAME = ".refresh.lock"


def _allowed_tools(kind: Report) -> list[str]:
    """Agli agenti serve leggere (i fatti e i frammenti degli altri) e
    scrivere il proprio frammento, **solo dentro la cartella del suo
    report**. I permessi sui file si controllano solo con regole
    `Edit(...)`: una regola `Write(...)` Claude Code la accetta e non la
    guarda mai. Niente Bash: i dati e i fatti li prepara questo modulo, una
    volta per tutti."""
    return ["Read", f"Edit(summary/{kind.folder}/**)"]


@contextlib.contextmanager
def _claim(data_dir: Path) -> Iterator[bool]:
    """Prende il lock dei lavori, se e' libero. Rende vero a chi l'ha preso e
    falso a chi l'ha trovato occupato; il file resta, e' il lock a sparire."""
    path = Path(data_dir) / LOCK_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        yield True
    finally:
        handle.close()


def _blank_section() -> dict:
    return {"status": "idle", "started": None, "finished": None, "message": None}


def _blank_state() -> dict:
    return {
        "status": "idle",
        "kind": DAILY.name,
        "day": None,
        "moment": None,
        "started": None,
        "finished": None,
        "message": None,
        "download": None,
        "sections": {section.key: _blank_section() for section in DAILY.run_order},
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
    subject: date,
    repo_root: Path,
    summary_dir: Path,
    data_dir: Path,
    keys: tuple[str, ...] | None = None,
    kind: Report = DAILY,
) -> dict:
    """Lancia il lavoro per `subject` — un giorno, o il lunedi di una
    settimana — se non ce n'e' gia' uno in corso. Rende lo stato: quello
    nuovo, o quello del lavoro che sta gia' girando.

    `keys` sono le sezioni da rifare, nell'ordine di `kind.run_order`; senza,
    si rifanno tutte: il tasto della pagina vuol dire "rifai tutto" a
    qualunque ora, e i sottoinsiemi dei giri li scelgono i timer."""
    sections = [s for s in kind.run_order if keys is None or s.key in keys]
    with _lock:
        if _state["status"] == "running":
            copy = dict(_state)
            copy["sections"] = {k: dict(v) for k, v in _state["sections"].items()}
            return copy
        now = datetime.now()
        # Prima di sovrascriverlo: serve a sapere se le sezioni che ci sono
        # gia' parlano dello stesso tipo di report.
        was = _state["kind"]
        _state.update(
            status="running",
            kind=kind.name,
            day=subject,
            moment=_moment_of(kind, subject, now),
            started=now,
            finished=None,
            message=None,
            download=None,
        )
        # Le sezioni sono quelle del report che si sta scrivendo: dopo un
        # giro settimanale lo stato non deve raccontare le chiavi del
        # giorno. Quelle che non si rifanno restano com'erano: lo stato dice
        # quello che e' successo l'ultima volta, non una bugia.
        known = _state["sections"] if was == kind.name else {}
        _state["sections"] = {
            s.key: _blank_section() if s in sections else known.get(s.key, _blank_section())
            for s in kind.run_order
        }
        started = _state["started"]
    thread = threading.Thread(
        target=_run,
        args=(kind, subject, started, repo_root, summary_dir, data_dir, tuple(sections)),
        daemon=True,
    )
    thread.start()
    return status()


def _moment_of(kind: Report, subject: date, when: datetime) -> str:
    """Il momento di default: per il giorno lo da' l'orologio, per la
    settimana il fatto che sia finita o no."""
    if kind is WEEKLY:
        return week_moment_at(subject, when.date())
    return moment_at(when)


def _set(key: str, **fields) -> None:
    with _lock:
        _state["sections"][key].update(**fields)


def _run(
    kind: Report,
    subject: date,
    started: datetime,
    repo_root: Path,
    summary_dir: Path,
    data_dir: Path,
    sections: tuple[Section, ...],
    update: bool = True,
    moment: str | None = None,
) -> bool:
    """Il lavoro vero: i dati, i fatti del periodo, gli agenti in fila.

    Rende falso senza fare niente se un altro lavoro sta gia' girando, qui o
    in un altro processo.

    Il momento e' la voce con cui Next e Summary parlano, non chi gira: di
    suo lo decide `_moment_of`, e lo si puo' imporre per riscrivere una
    sezione con la voce dell'altro giro.

    **La settimana non scarica mai** (todo 53): gira in coda al giro del
    giorno, che ha appena chiamato Garmin, e un secondo scaricamento sarebbe
    solo un'altra occasione di fallire."""
    moment = moment or _moment_of(kind, subject, started)
    update = update and kind is not WEEKLY
    # Lo stato deve avere le voci di **questo** report: `start()` le ha gia'
    # messe, ma il comando da terminale chiama `_run` direttamente e senza
    # questo troverebbe le chiavi dell'altro tipo (il primo giro settimanale
    # e' morto cosi', su `KeyError: 'summary_end'`).
    with _lock:
        if _state["kind"] != kind.name:
            _state["kind"] = kind.name
            _state["sections"] = {s.key: _blank_section() for s in kind.run_order}
        else:
            for section in kind.run_order:
                _state["sections"].setdefault(section.key, _blank_section())
    failed: list[str] = []
    message = None
    with _claim(data_dir) as mine:
        if not mine:
            with _lock:
                _state.update(
                    status="failed",
                    finished=datetime.now(),
                    message="Another refresh is already running.",
                )
            return False
        with tempfile.TemporaryDirectory() as tmp:
            facts = Path(tmp) / f"{kind.name}-{subject.isoformat()}.json"
            ok, problem, download = _prepare(kind, subject, repo_root, data_dir, facts, update)
            with _lock:
                _state["download"] = download
            if not ok:
                message = problem
            else:
                folder = Path(summary_dir) / kind.folder / subject.isoformat()
                folder.mkdir(parents=True, exist_ok=True)
                for section in sections:
                    began = datetime.now()
                    _set(section.key, status="running", started=began, finished=None, message=None)
                    good, problem = _write_section(
                        kind, section, subject, moment, repo_root, facts, folder, began
                    )
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
    return True


def _facts(kind: Report, subject: date, data_dir: Path) -> dict:
    """I fatti del periodo, gli stessi che riceve la pagina."""
    if kind is WEEKLY:
        from training.api.weekly import weekly_payload

        return weekly_payload(subject, data_dir)
    from training.api.daily import daily_payload

    return daily_payload(subject, data_dir)


def _prepare(
    kind: Report,
    subject: date,
    repo_root: Path,
    data_dir: Path,
    facts: Path,
    update: bool = True,
) -> tuple[bool, str | None, dict | None]:
    """Scarica i dati nuovi e scrive i fatti del periodo in `facts`. Rende se
    si puo' andare avanti, l'eventuale motivo per cui no, e com'e' andato lo
    scaricamento.

    `update_activity` chiama Garmin: se fallisce (niente rete, login scaduto)
    non ci si ferma, si va avanti con i dati locali. **Ma lo si dice**: da
    quando a lanciare sono i timer (todo 47) non c'e' nessuno a guardare, e
    un login scaduto farebbe scrivere report su dati di tre giorni fa senza
    che niente lo segnali. L'esito finisce in `download`, e da li' nello
    stato che la pagina mostra. Con `update` falso non si chiama affatto: si
    riscrive il testo sui dati che ci sono gia'.

    I fatti sono quelli di `api/daily.daily_payload` e
    `api/weekly.weekly_payload`, cioe' **gli stessi che riceve la pagina**,
    non quelli di `make daily_data`: quel JSON non ha il blocco `fitness`, e
    l'agente di Fitness scriveva che i punteggi non c'erano mentre la card
    accanto li mostrava."""
    download = None
    if update:
        try:
            done = subprocess.run(
                ["make", "update_activity"],
                cwd=repo_root, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=UPDATE_TIMEOUT_SECONDS, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            download = {"ok": False, "message": f"The download could not run: {exc}"}
        else:
            download = {"ok": done.returncode == 0, "message": None}
            if done.returncode != 0:
                download["message"] = (
                    _tail(done) or f"make update_activity exited with {done.returncode}."
                )
        # I file sono cambiati sotto la cache: senza questo i fatti sarebbero
        # quelli di prima dello scaricamento.
        invalidate(data_dir)
    try:
        payload = _facts(kind, subject, data_dir)
    except Exception as exc:  # noqa: BLE001 - qualunque cosa, il lavoro si ferma qui
        return False, f"The facts could not be built: {exc}", download
    facts.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    return True, None, download


def _prompt(
    kind: Report, section: Section, subject: date, moment: str, facts: Path, folder: Path
) -> str:
    where = f"Write the body of the section (no `## ` heading) to {folder / f'{section.key}.md'}."
    when = kind.moment_lines[moment]
    period = kind.period(subject)
    if section.key == "summary_start":
        # Chi apre la settimana non ha frammenti suoi da leggere: la sua
        # cartella e' vuota, e quello che gli serve — com'e' andata e cosa
        # era previsto — sta nel report della settimana prima, scritto la
        # sera precedente.
        before = folder.parent / (subject - timedelta(days=7)).isoformat()
        return (
            f"Write the {section.title} part of the {kind.what} for {period}. "
            f"{when} "
            f"The report of the week before is written in {before}: read it, it is your input. "
            f"The facts of this week, which has barely begun, are in {facts}. {where}"
        )
    if section.reads_fragments:
        return (
            f"Write the {section.title} part of the {kind.what} for {period}. "
            f"{when} "
            f"The other sections are already written in {folder}: read them, they are your "
            f"input. The facts, if you need them, are in {facts}. {where}"
        )
    return (
        f"Write the {section.title} section of the {kind.what} for {period}. "
        f"{when} "
        f"The facts are in {facts}: read that file, do not run anything. {where}"
    )


def _write_section(
    kind: Report,
    section: Section,
    subject: date,
    moment: str,
    repo_root: Path,
    facts: Path,
    folder: Path,
    began: datetime,
) -> tuple[bool, str | None]:
    claude = shutil.which("claude")
    if claude is None:
        return False, "The claude command is not on the PATH of the API."
    command = [
        claude, "-p", "--agent", section.agent,
        "--append-system-prompt-file", str(repo_root / STYLE_FILE),
        "--allowedTools", *_allowed_tools(kind),
        "--", _prompt(kind, section, subject, moment, facts, folder),
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


def section_keys(
    name: str | None, moment: str | None = None, kind: Report = DAILY
) -> tuple[str, ...] | None:
    """Le chiavi da rifare: una sola col nome di una sezione, quelle del giro
    con un momento, tutte senza niente. Alza `KeyError` su un nome che non
    esiste.

    Il nome di una sezione vince sul momento: chiedere una sezione sola e'
    piu' preciso di chiedere un giro."""
    if name is not None:
        return (kind.by_key[name].key,)
    if moment is not None:
        return kind.moments[moment]
    return None


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data non valida: {text!r} (serve YYYY-MM-DD)")


def _cli(kind: Report) -> None:
    """Rifa' un report da terminale, senza passare dall'API.

    Lo stesso lavoro del tasto Refresh, ma in primo piano e senza server:
    serve per rifare un report a mano, per provare l'impianto, ed e' quello
    che lanciano i timer (`--moment`, todo 47 e 53). Stampa come e' andata
    sezione per sezione, ed esce 1 se qualcuna e' fallita.

    Se un altro lavoro sta gia' girando — il tasto della pagina, o il giro
    di cron dell'altro momento — non si mette in coda: lo dice ed esce 0,
    cosi' nel registro un accavallamento non si legge come un guasto."""
    from training.api.context import REPO_ROOT, SUMMARY_DIR
    from training.garmin.config import DATA_DIR

    weekly = kind is WEEKLY
    parser = argparse.ArgumentParser(
        description=f"Rifa' il report {'settimanale' if weekly else 'giornaliero'}, "
        "una sezione o tutte."
    )
    parser.add_argument(
        "--week" if weekly else "--day",
        type=_day,
        help="il lunedi della settimana (YYYY-MM-DD); di default quella di oggi"
        if weekly
        else "il giorno (YYYY-MM-DD); di default oggi",
    )
    parser.add_argument("--section", help="una sola sezione: " + ", ".join(kind.by_key))
    parser.add_argument(
        "--moment",
        choices=tuple(kind.moments),
        help="il giro di un timer invece di tutte le sezioni ("
        + "; ".join(f"{name} = {', '.join(keys)}" for name, keys in kind.moments.items())
        + "). Da' anche la voce a Next e Summary, che senza la prendono "
        "dal periodo: con --section riscrive quella sezione sola con la "
        "voce del giro scelto.",
    )
    if not weekly:
        parser.add_argument(
            "--no-update",
            action="store_true",
            help="non richiamare Garmin: riscrive il testo sui dati che ci sono gia'",
        )
    args = parser.parse_args()
    today = date.today()
    if weekly:
        # Di default la settimana di oggi: il giro del lunedi apre quella
        # che comincia, quello della domenica chiude quella che finisce in
        # giornata, e sono la stessa. Per una settimana vecchia, `--week`.
        subject = args.week or (today - timedelta(days=today.weekday()))
        if subject.weekday() != 0:
            parser.error(f"il {subject} non e' un lunedi'")
        if subject > today:
            parser.error(f"la settimana del {subject} non e' ancora cominciata")
    else:
        subject = args.day or today
        if subject > today:
            parser.error(f"il {subject} non e' ancora arrivato")
    try:
        keys = section_keys(args.section, args.moment, kind)
    except KeyError:
        parser.error(
            f"sezione sconosciuta: {args.section!r} (ce ne sono {', '.join(kind.by_key)})"
        )
    sections = tuple(s for s in kind.run_order if keys is None or s.key in keys)

    what = f"della settimana del {subject}" if weekly else f"del {subject}"
    print(f"Report {what}: {len(sections)} sezioni, una alla volta.")
    if not _run(
        kind,
        subject,
        datetime.now(),
        REPO_ROOT,
        SUMMARY_DIR,
        DATA_DIR,
        sections,
        not getattr(args, "no_update", False),
        args.moment,
    ):
        print("Ce n'e' gia' uno in corso: non faccio niente.")
        raise SystemExit(0)
    state = status()
    if state["download"] and not state["download"]["ok"]:
        print(f"  dati     non scaricati  {state['download']['message']}")
    for section in sections:
        row = state["sections"][section.key]
        note = f"  {row['message']}" if row["message"] else ""
        print(f"  {section.key:15} {row['status']}{note}")
    print(state["message"] or "Fatto.")
    raise SystemExit(1 if state["status"] == "failed" else 0)


def main() -> None:
    """Il report del giorno da terminale (`training-daily-report`)."""
    _cli(DAILY)


def week_main() -> None:
    """Il report della settimana da terminale (`training-weekly-report`)."""
    _cli(WEEKLY)
