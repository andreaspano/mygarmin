"""Le sezioni del report giornaliero, una per card (todo 44).

Ogni sezione ha il suo agente, che ne scrive il corpo in un file dentro
`summary/01.daily/<giorno>/`. Qui sta l'elenco, in un posto solo: lo legge
l'API per comporre il report e l'orchestratore per sapere chi lanciare e in
che ordine.

Le prime cinque guardano i numeri del giorno, ognuna la sua fetta del JSON.
Le ultime due (`next`, `summary`) leggono quello che hanno scritto le altre,
quindi girano dopo: l'ordine di `RUN_ORDER` non e' quello in cui le sezioni
si leggono nella pagina."""

from dataclasses import dataclass
from datetime import datetime


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

BY_KEY = {section.key: section for section in SECTIONS}

# Nell'ordine in cui si lanciano, che e' quello dei numeri degli agenti e non
# quello di lettura: prima quelle che guardano i numeri del giorno, poi quelle
# che leggono i frammenti delle altre. Il sole prima della luna, perche'
# quando girano insieme (il tasto della pagina) la luna lo deve trovare
# scritto.
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
RUN_ORDER: tuple[Section, ...] = tuple(BY_KEY[key] for key in _RUN_KEYS)
assert {s.key for s in RUN_ORDER} == {s.key for s in SECTIONS}
# I verdetti stanno in fondo, tutti insieme: chi legge i frammenti degli
# altri non puo' girare prima di loro.
_first_verdict = next(i for i, s in enumerate(RUN_ORDER) if s.reads_fragments)
assert all(s.reads_fragments for s in RUN_ORDER[_first_verdict:]), "i verdetti per ultimi"


# I due giri dei timer (todo 47). Non sono due giri uguali: la mattina
# Health e Recovery hanno qualcosa da dire, perche' sono le misure della
# notte appena finita; la sera racconterebbero di nuovo la stessa notte.
# Training il contrario: alle 10 non c'e' ancora niente da commentare.
MOMENT_SECTIONS: dict[str, tuple[str, ...]] = {
    "morning": ("health", "recovery", "load", "fitness", "next", "summary_morning"),
    "evening": ("load", "fitness", "training", "next", "summary_evening"),
}

MOMENTS = tuple(MOMENT_SECTIONS)
assert all(set(keys) <= set(BY_KEY) for keys in MOMENT_SECTIONS.values())

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
