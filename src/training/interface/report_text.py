"""La lettura di un report scritto (`summary/...`), senza Streamlit.

E' la parte di `report_view.show_report` che legge il file: la usa la
pagina per disegnare il riquadro e l'API (`training.api`) per rendere le
sezioni come dati."""

from pathlib import Path

# Un'icona per sezione del report, dalla cartella delle icone degli sport
# (`icons/`). La sezione si riconosce dal nome nel titolo ("1. Training" ->
# training.png), non dal numero: un report con le sezioni in un altro ordine le trova lo
# stesso, e una sezione senza icona resta col solo titolo.
#
# Il report giornaliero ha le stesse sezioni con titolo del settimanale:
# "Training" e "Recovery" usano le stesse icone, "Load" prende quella del
# trend (e' l'andamento del carico), "Health" (una croce) e "Next" (una
# freccia) hanno la loro, disegnate nello stesso stile: cerchio pieno e tratto
# bianco arrotondato.
REPORT_SECTION_ICONS = {
    "training": "training.png",
    "recovery": "recovery.png",
    "trend": "trend.png",
    "load": "trend.png",
    "health": "health.png",
    "next": "next.png",
}

# Le righe del file che ripetono quello che la pagina dice gia': il titolo
# ("# ...") e le righe di intestazione del settimanale ("Week: ...") e del
# giornaliero ("Window: ..." nei report vecchi, "Data: ..." nei nuovi). Il
# periodo e' la riga spuntata nella tabella accanto.
_HEADER_PREFIXES = ("# ", "Week: ", "Window: ", "Data: ")


def section_icon(title: str) -> str | None:
    """Il file dell'icona della sezione dal suo titolo, o None. Il file puo'
    mancare nella cartella: lo controlla chi lo mostra."""
    words = title.lower()
    for name, filename in REPORT_SECTION_ICONS.items():
        if name in words:
            return filename
    return None


def parse_report(path: Path) -> list[tuple[str | None, str]]:
    """Le sezioni del report in `path`, come (titolo, testo).

    Le sezioni sono le righe "## ..." ("## 1. Training", ...). Il testo prima
    della prima sezione, se c'e', ha titolo `None`: e' tutto il testo dei
    report giornalieri vecchi, che avevano paragrafi in grassetto. Una
    sezione senza titolo e senza testo non si rende."""
    lines = [
        line
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if not line.startswith(_HEADER_PREFIXES)
    ]

    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in lines:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)
    return [
        (title, body)
        for title, body in ((title, "\n".join(text).strip()) for title, text in sections)
        if title or body
    ]
