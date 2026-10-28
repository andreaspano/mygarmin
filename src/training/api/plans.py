"""I piani di allenamento scritti a mano in `plan/`.

Un piano e' un file Markdown: davanti un front matter YAML con i numeri che
la pagina mostra come riquadri (la gara, il bersaglio, il ritmo, le settimane
del blocco), dietro il testo, che e' quello che si legge. La stessa idea del
todo 14 per i piani settimanali di `summary/05.plan/`, ma allargata a un
blocco intero: qui le chiavi dicono la gara, non le sedute di sette giorni.

**Il front matter non e' obbligatorio.** Un file che non ce l'ha non si salta:
si mostra col solo testo, e i riquadri restano vuoti. I piani li scrive una
persona a mano, e un piano che non si vede perche' gli manca una chiave
sarebbe peggio di un piano senza numeri in cima.

Il titolo non sta nel front matter: e' il primo titolo di primo livello del
testo (`# ...`), togliendolo dal corpo perche' la pagina lo mette nella sua
intestazione. Senza titolo resta il nome del file."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

# Il front matter: fra due righe di soli tre trattini, in cima al file.
_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)
# Il titolo del piano: il primo `# ...`, da solo sulla sua riga.
_TITLE = re.compile(r"\A\s*#[ \t]+(.+?)[ \t]*(?:\n|\Z)")


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Il front matter e il testo che lo segue. Un file senza front matter, o
    con un front matter che YAML non legge, rende `{}` e il testo intero: il
    piano si vede comunque."""
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text[match.end() :]
    return (meta if isinstance(meta, dict) else {}), text[match.end() :]


def _title(body: str) -> tuple[str | None, str]:
    """Il titolo e il corpo senza di lui."""
    match = _TITLE.match(body)
    if not match:
        return None, body.strip()
    return match.group(1), body[match.end() :].strip()


def _as_date(value: Any) -> date | None:
    """Una data del front matter. YAML legge `2027-02-28` come `date` da se';
    scritta fra apici arriva come stringa."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    # Un bersaglio scritto senza apici (`target_time: 2:20:00`) YAML lo legge
    # come un numero di minuti, non come un'ora: meglio il numero crudo di un
    # riquadro vuoto.
    return str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _plan(path: Path) -> dict[str, Any]:
    """Un piano, dal suo file."""
    meta, body = _front_matter(path.read_text(encoding="utf-8"))
    title, text = _title(body)
    return {
        "slug": path.stem,
        "file": path.name,
        "title": title or path.stem,
        "race": _as_date(meta.get("race")),
        "race_name": _as_text(meta.get("race_name")),
        "distance_km": _as_number(meta.get("distance_km")),
        "target_time": _as_text(meta.get("target_time")),
        "target_pace": _as_text(meta.get("target_pace_min_km")),
        "target_speed_kmh": _as_number(meta.get("target_speed_kmh")),
        "block_start": _as_date(meta.get("block_start")),
        "weeks": int(weeks) if (weeks := _as_number(meta.get("block_weeks"))) else None,
        "peak_weekly_km": _as_number(meta.get("peak_weekly_km")),
        "written_at": datetime.fromtimestamp(path.stat().st_mtime),
        "body": text,
    }


def load_plans(folder: Path) -> list[dict[str, Any]]:
    """I piani di `folder`, la gara piu' vicina per prima.

    Dentro la stessa gara vince il bersaglio piu' veloce, cosi' i tre piani
    di una mezza si leggono dal piu' ambizioso al piu' prudente; i piani
    senza data di gara stanno in fondo, in ordine di nome. Una cartella che
    non c'e' non e' un errore: sono zero piani."""
    if not folder.is_dir():
        return []
    plans = [_plan(path) for path in sorted(folder.glob("*.md")) if path.is_file()]
    return sorted(
        plans,
        key=lambda p: (
            p["race"] is None,
            p["race"] or date.max,
            p["target_time"] or "",
            p["slug"],
        ),
    )


# I piani settimanali di `summary/05.plan/` (todo 14 e 60): un file per
# settimana, col nome del suo lunedi'. Stanno in `summary/` e non in `plan/`
# perche' non li scrive una persona — si generano da un blocco di `plan/` — e
# il nome della cartella e' qui, che e' il modulo che sa come sono fatti i
# file di un piano: lo leggono sia l'orchestratore, per il prompt di Next, sia
# la vista Plan della Week.
WEEK_PLAN_FOLDER = "05.plan"


def week_plan_path(summary_dir: Path, day: date) -> Path | None:
    """Il file del piano della settimana in cui cade `day`, se c'e'.

    Un giorno qualunque va bene e viene riportato al suo lunedi', che e' il
    nome del file: chi chiama ha in mano una data, non sempre un lunedi'.
    Niente file non e' un errore — le settimane prima dell'inizio del blocco
    non ne hanno, e il piano di una settimana non deve diventare un'istruzione
    da inventare."""
    monday = day - timedelta(days=day.weekday())
    path = summary_dir / WEEK_PLAN_FOLDER / f"{monday.isoformat()}.md"
    return path if path.is_file() else None


# I mesi come li scrivono i file del piano, nella prima cella della tabella
# (`**Wed 28 Oct**`). Scritti qui e non con `strftime("%b")`, che segue la
# lingua del processo: `make api` con LANG italiano direbbe "ott" e la riga
# non si troverebbe piu'.
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _distance_label(value: Any) -> str | None:
    """La distanza di una seduta come la legge una persona: `"7 km"`, o
    `"10-11 km"` quando il piano da' un intervallo.

    L'etichetta la fa l'API e non la pagina, come fanno gia' `Sport.label` e
    `section_icon`: i conti e la forma dei numeri stanno da questa parte
    (todo 52)."""
    def one(number: Any) -> str | None:
        km = _as_number(number)
        if km is None:
            return None
        return f"{km:g}"

    if isinstance(value, (list, tuple)):
        ends = [text for number in value if (text := one(number)) is not None]
        if len(ends) == 2:
            return f"{ends[0]}-{ends[1]} km"
        return f"{ends[0]} km" if ends else None
    single = one(value)
    return f"{single} km" if single is not None else None


def _day_row(body: str, day: date) -> str | None:
    """La riga di `day` nella tabella `Day | Session` del piano.

    Si guarda **solo la prima cella**, che la seconda e' la prosa e puo'
    nominare altre date; e si cerca la data nella forma dei file (`28 Oct`),
    con i delimitatori di parola, se no `1 Nov` si troverebbe dentro
    `21 Nov`. Nessuna riga trovata non e' un errore: il testo e' un extra, i
    campi della seduta vengono dal front matter."""
    needle = re.compile(rf"\b{day.day} {_MONTHS[day.month - 1]}\b")
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not needle.search(cells[0]):
            continue
        return cells[1].strip() or None
    return None


def _session(entry: dict, day: date, text: str) -> dict[str, Any]:
    """Una voce di `sessions` nei campi che l'API manda, piu' la riga che quel
    giorno ha nella tabella del testo.

    La usano in due (todo 71): `load_day_plan`, per il giorno che la Day sta
    mostrando, e `load_week_plan`, che le manda tutte e sette. Prima era
    scritta una volta e mezza — i campi dentro `load_day_plan`, e i soli
    totali altrove."""
    return {
        "day": day,
        "sport": _as_text(entry.get("sport")),
        "kind": _as_text(entry.get("kind")),
        "distance_label": _distance_label(entry.get("distance_km")),
        "optional": _as_text(entry.get("optional")),
        "text": _day_row(text, day),
    }


def _planned_sessions(meta: dict, text: str) -> list[dict[str, Any]] | None:
    """Le sette sedute di una settimana, in ordine di data.

    `None` quando `sessions` non c'e': il file di settembre 2026 ha la
    tabella e non i campi, e ricavare le sedute dalla prosa e' la strada
    fragile che il todo 14 aveva scartato.

    **In ordine di data e non di file.** Il front matter le scrive da lunedi'
    a domenica, ma quel file di settembre dimostra che non e' garantito — la
    sua tabella parte dalla domenica — e una card che le mette in fila le
    vuole in fila. Le voci senza una data si saltano: senza di quella una
    seduta non si sa di che giorno e'."""
    sessions = meta.get("sessions")
    if not isinstance(sessions, list):
        return None
    dated = [
        (day, entry)
        for entry in sessions
        if isinstance(entry, dict) and (day := _as_date(entry.get("date"))) is not None
    ]
    if not dated:
        return None
    return [_session(entry, day, text) for day, entry in sorted(dated, key=lambda p: p[0])]


def load_day_plan(summary_dir: Path, day: date) -> dict[str, Any] | None:
    """La seduta prevista per `day`, dal piano della sua settimana, o `None`
    se per quel giorno un piano non c'e'.

    `None` copre tutti i modi in cui non c'e' — file assente, front matter
    assente o illeggibile, `sessions` assente, nessuna voce con quella data —
    perche' per chi guarda sono la stessa cosa: quel giorno non e' previsto
    niente. Il file di settembre 2026, scritto prima che il formato avesse il
    front matter, cade qui: la sua tabella c'e' ma le sedute a macchina no, e
    inventarle dal testo e' la strada fragile che il todo 14 aveva scartato.

    La voce si cerca **per data e non per posizione**: quel file dimostra che
    ne' l'ordine ne' il numero delle righe sono garantiti (la sua tabella
    parte dalla domenica e ha otto righe).

    Il testo di quella riga arriva comunque, accanto ai campi, perche' e'
    dov'e' scritto il perche'. I campi sono gli stessi che `load_week_plan`
    manda per tutti e sette i giorni (`_session`), con attorno da che file
    vengono."""
    path = week_plan_path(summary_dir, day)
    if path is None:
        return None
    meta, body = _front_matter(path.read_text(encoding="utf-8"))
    sessions = meta.get("sessions")
    if not isinstance(sessions, list):
        return None
    entry = next(
        (s for s in sessions if isinstance(s, dict) and _as_date(s.get("date")) == day),
        None,
    )
    if entry is None:
        return None
    _, text = _title(body)
    return {
        **_session(entry, day, text),
        "week": _as_date(meta.get("week")) or day - timedelta(days=day.weekday()),
        "file": path.name,
        "written_at": datetime.fromtimestamp(path.stat().st_mtime),
    }


def load_week_plan(summary_dir: Path, day: date) -> dict[str, Any] | None:
    """Il piano della settimana di `day`, o `None` se quella settimana non ne
    ha uno.

    Stesso trattamento dei piani di `plan/`: il front matter da' i numeri, il
    primo `# ...` il titolo, e il resto e' il testo che si legge. Le chiavi
    sono quelle delle sette sedute invece di quelle di una gara, e
    `summary/05.plan/README.md` le elenca.

    **Le sette sedute si mandano, una per giorno** (todo 71): e' il piano
    della settimana giorno per giorno, che e' la domanda che si fa guardando
    una settimana. Il todo 60 non le mandava perche' nessuno le guardava, e
    il todo 70 ne aveva mandato i soli totali, che rispondevano a un'altra
    domanda. Il testo resta com'e': la sua tabella dice le stesse sedute con
    dentro anche il perche', e quello e' il documento."""
    path = week_plan_path(summary_dir, day)
    if path is None:
        return None
    meta, body = _front_matter(path.read_text(encoding="utf-8"))
    title, text = _title(body)
    return {
        "week": _as_date(meta.get("week")) or day - timedelta(days=day.weekday()),
        "file": path.name,
        "title": title or path.stem,
        "plan": _as_text(meta.get("plan")),
        "block_week": int(n) if (n := _as_number(meta.get("block_week"))) else None,
        "block_weeks": int(n) if (n := _as_number(meta.get("block_weeks"))) else None,
        "phase": _as_text(meta.get("phase")),
        "race": _as_date(meta.get("race")),
        "target_time": _as_text(meta.get("target_time")),
        "sessions": _planned_sessions(meta, text),
        "written_at": datetime.fromtimestamp(path.stat().st_mtime),
        "body": text,
    }
