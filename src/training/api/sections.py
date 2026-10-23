"""Le sezioni dei report, una per card (todo 44 per il giorno, 53 per la
settimana).

Ogni sezione ha il suo agente, che ne scrive il corpo in un file dentro la
cartella del report (`summary/01.daily/<giorno>/`,
`summary/02.weekly/<lunedi>/`). Qui sta l'elenco, in un posto solo: lo legge
l'API per comporre il report e l'orchestratore per sapere chi lanciare e in
che ordine.

Le sezioni che guardano i numeri girano per prime, quelle che leggono i
frammenti delle altre dopo: l'ordine di `run_order` non e' quello in cui le
sezioni si leggono nella pagina.

Giorno e settimana hanno la stessa forma e due registri diversi, tenuti
insieme da `Report`: cambiano le sezioni, la cartella, i due giri e gli
agenti, non il meccanismo."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Section:
    key: str
    # Il titolo nel report (`## Health`): lo mette chi compone, non l'agente.
    title: str
    # Il nome dell'agente in `.claude/agents/`.
    agent: str
    # Vera per chi legge i frammenti degli altri invece dei numeri.
    reads_fragments: bool


# Nell'ordine in cui si leggono nella pagina. Il verdetto del giorno e' in
# due pezzi (todo 49), stesso agente e due momenti: il sole lo scrive il giro
# del mattino, la luna quello della sera. Con un file solo il giro delle 22
# cancellava il verdetto delle 10, che e' proprio quello con cui vale la pena
# confrontarlo.
SECTIONS: tuple[Section, ...] = (
    Section("summary_morning", "Morning summary", "07_summary", True),
    Section("summary_evening", "Evening summary", "07_summary", True),
    Section("training", "Training", "05_training", False),
    Section("recovery", "Recovery", "03_recovery", False),
    Section("health", "Health", "01_health", False),
    Section("load", "Load", "02_load", False),
    Section("fitness", "Fitness", "04_fitness", False),
    Section("next", "Next", "06_next", True),
)

# La settimana (todo 53): le stesse cinque card piu' Next e il Summary in due
# parti, che qui sono l'apertura del lunedi e la chiusura della domenica.
WEEK_SECTIONS: tuple[Section, ...] = (
    Section("summary_start", "Week start", "w7_summary", True),
    Section("summary_end", "Week end", "w7_summary", True),
    Section("training", "Training", "w5_training", False),
    Section("recovery", "Recovery", "w3_recovery", False),
    Section("health", "Health", "w1_health", False),
    Section("load", "Load", "w2_load", False),
    Section("fitness", "Fitness", "w4_fitness", False),
    Section("next", "Next", "w6_next", True),
)

BY_KEY = {section.key: section for section in SECTIONS}

# Nell'ordine in cui si lanciano, che e' quello dei numeri degli agenti e non
# quello di lettura: prima quelle che guardano i numeri, poi quelle che
# leggono i frammenti delle altre. Il primo verdetto prima del secondo,
# perche' quando girano insieme (il tasto della pagina) il secondo deve
# trovare il primo scritto.
_RUN_KEYS = (
    "health",
    "load",
    "recovery",
    "fitness",
    "training",
    "next",
    "summary_morning",
    "summary_evening",
)
_WEEK_RUN_KEYS = (
    "health",
    "load",
    "recovery",
    "fitness",
    "training",
    "next",
    "summary_start",
    "summary_end",
)


def _ordered(sections: tuple[Section, ...], keys: tuple[str, ...]) -> tuple[Section, ...]:
    by_key = {section.key: section for section in sections}
    order = tuple(by_key[key] for key in keys)
    assert {s.key for s in order} == {s.key for s in sections}
    # I verdetti stanno in fondo, tutti insieme: chi legge i frammenti degli
    # altri non puo' girare prima di loro.
    first = next(i for i, s in enumerate(order) if s.reads_fragments)
    assert all(s.reads_fragments for s in order[first:]), "i verdetti per ultimi"
    return order


RUN_ORDER: tuple[Section, ...] = _ordered(SECTIONS, _RUN_KEYS)
WEEK_RUN_ORDER: tuple[Section, ...] = _ordered(WEEK_SECTIONS, _WEEK_RUN_KEYS)


# I due giri dei timer (todo 47). Non sono due giri uguali: la mattina
# Health e Recovery hanno qualcosa da dire, perche' sono le misure della
# notte appena finita; la sera racconterebbero di nuovo la stessa notte.
# Training il contrario: alle 10 non c'e' ancora niente da commentare.
MOMENT_SECTIONS: dict[str, tuple[str, ...]] = {
    "morning": ("health", "recovery", "load", "fitness", "next", "summary_morning"),
    "evening": ("load", "fitness", "training", "next", "summary_evening"),
}

# I due giri della settimana (todo 53): il lunedi alle 10 apre la settimana
# che comincia, la domenica alle 22 la chiude.
#
# **Il lunedi scrive una sezione sola.** Il todo ne prevedeva sei, ma una
# settimana al suo primo giorno non ha numeri da commentare: le medie
# starebbero su un giorno e le sedute su nessuna. Chi apre non guarda i
# numeri di questa settimana — guarda come ci arrivi, e questo lo sa dal
# report della settimana prima e dalla notte appena finita. Tutto il resto
# si scrive la domenica, quando i sette giorni ci sono tutti.
#
# Next sta nella chiusura, perche' la strategia e' per la settimana che
# comincia il giorno dopo: come il Next della sera parla di domani.
WEEK_MOMENT_SECTIONS: dict[str, tuple[str, ...]] = {
    "start": ("summary_start",),
    "end": ("health", "recovery", "load", "fitness", "training", "next", "summary_end"),
}

MOMENTS = tuple(MOMENT_SECTIONS)
WEEK_MOMENTS = tuple(WEEK_MOMENT_SECTIONS)
assert all(set(keys) <= set(BY_KEY) for keys in MOMENT_SECTIONS.values())
assert all(
    set(keys) <= {s.key for s in WEEK_SECTIONS} for keys in WEEK_MOMENT_SECTIONS.values()
)

# Come si dice all'agente a che punto siamo. Non e' un fatto del periodo ma
# del giro (todo 47): lo usano Next, che deve sapere per quando e' il
# consiglio, e Summary, che apre o chiude.
_DAY_MOMENT_LINES = {
    "morning": "This is the morning run: the day is ahead of him.",
    "evening": "This is the evening run: the day is behind him.",
}
_WEEK_MOMENT_LINES = {
    "start": "This is the Monday run: the week you are writing about starts today, and has "
    "no numbers of its own yet.",
    "end": "This is the Sunday evening run: the week is finished, and the next one starts "
    "tomorrow.",
}


@dataclass(frozen=True)
class Report:
    """Un tipo di report: quello del giorno o quello della settimana.

    Tiene insieme le cose che l'orchestratore deve sapere per scriverlo —
    dove vanno i frammenti, chi gira, in che ordine e con che voce — cosi'
    il ciclo e' uno solo per tutti e due (todo 53)."""

    name: str
    # Come si chiama nel prompt dell'agente.
    what: str
    # La cartella sotto `summary/`.
    folder: str
    # Nell'ordine in cui si leggono nella pagina.
    sections: tuple[Section, ...]
    # Nell'ordine in cui si lanciano.
    run_order: tuple[Section, ...]
    # I giri: quali sezioni scrive ognuno.
    moments: dict[str, tuple[str, ...]]
    # La riga che dice all'agente a che punto del periodo siamo.
    moment_lines: dict[str, str]

    @property
    def by_key(self) -> dict[str, Section]:
        return {section.key: section for section in self.sections}

    def period(self, subject: date) -> str:
        """Il periodo come lo legge l'agente: un giorno, o una settimana con
        i suoi due estremi."""
        if self.name == "weekly":
            return f"the week from Monday {subject} to Sunday {subject + timedelta(days=6)}"
        return subject.isoformat()


DAILY = Report(
    name="daily",
    what="daily report",
    folder="01.daily",
    sections=SECTIONS,
    run_order=RUN_ORDER,
    moments=MOMENT_SECTIONS,
    moment_lines=_DAY_MOMENT_LINES,
)
WEEKLY = Report(
    name="weekly",
    what="weekly report",
    folder="02.weekly",
    sections=WEEK_SECTIONS,
    run_order=WEEK_RUN_ORDER,
    moments=WEEK_MOMENT_SECTIONS,
    moment_lines=_WEEK_MOMENT_LINES,
)
KINDS = {report.name: report for report in (DAILY, WEEKLY)}


# L'ora da cui una giornata si considera alle spalle. Serve alla **voce** del
# testo, non a chi gira: prima di questa Next propone la seduta per oggi e
# Summary giudica la giornata che comincia, dopo Next guarda a domani e
# Summary dice com'e' andata.
EVENING_FROM_HOUR = 15


def moment_at(when: datetime) -> str:
    """Il momento della giornata di `when`, per la voce del testo.

    Si ricava sempre dall'orologio, anche quando a lanciare e' il tasto
    della pagina: cosi' un refresh a mano parla come il giro del timer che
    gli e' piu' vicino. Quale sezione gira e' un'altra cosa, e la decidono
    solo i timer (`MOMENT_SECTIONS`)."""
    return "evening" if when.hour >= EVENING_FROM_HOUR else "morning"


def week_moment_at(monday: date, today: date) -> str:
    """Il momento di una settimana, per la voce del testo: una settimana
    finita si racconta da domenica sera, una ancora aperta dal lunedi.

    Non guarda l'orologio come `moment_at`: una settimana dura sette giorni,
    e quello che cambia la voce e' se e' finita o no. L'ultimo giorno conta
    come finita: il giro delle 22 della domenica chiude la settimana che sta
    finendo in quel momento."""
    return "start" if monday + timedelta(days=6) > today else "end"
