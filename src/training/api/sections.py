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


@dataclass(frozen=True)
class Section:
    key: str
    # Il titolo nel report (`## Health`): lo mette chi compone, non l'agente.
    title: str
    # Il nome dell'agente in `.claude/agents/`.
    agent: str
    # Vera per chi legge i frammenti degli altri invece dei numeri.
    reads_fragments: bool


# Nell'ordine in cui si leggono nella pagina.
SECTIONS: tuple[Section, ...] = (
    Section("summary", "Summary", "07_summary", True),
    Section("training", "Training", "05_training", False),
    Section("recovery", "Recovery", "03_recovery", False),
    Section("health", "Health", "01_health", False),
    Section("load", "Load", "02_load", False),
    Section("fitness", "Fitness", "04_fitness", False),
    Section("next", "Next", "06_next", True),
)

BY_KEY = {section.key: section for section in SECTIONS}

# Nell'ordine in cui si lanciano, che e' quello dei numeri degli agenti e non
# quello di lettura: prima le cinque che guardano i numeri del giorno, poi le
# due che leggono i frammenti delle altre.
_RUN_KEYS = ("health", "load", "recovery", "fitness", "training", "next", "summary")
RUN_ORDER: tuple[Section, ...] = tuple(BY_KEY[key] for key in _RUN_KEYS)
assert {s.key for s in RUN_ORDER} == {s.key for s in SECTIONS}
assert all(not s.reads_fragments for s in RUN_ORDER[:5]), "i numeri prima dei verdetti"
assert all(s.reads_fragments for s in RUN_ORDER[5:]), "i verdetti per ultimi"
