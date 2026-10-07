"""Il riquadro con un report scritto (`summary/...`), condiviso fra le pagine.

La Week e la Month ci mostrano il report del periodo scelto, la Day quello del
giorno (todo 31): stesso aspetto e stesso modo di leggere il file, invece di
una copia per pagina."""

from pathlib import Path

import streamlit as st

from training.interface.activity_table import ICONS_DIR

# Un'icona per sezione del report, dalla cartella delle icone degli sport. La
# sezione si riconosce dal nome nel titolo ("1. Training" -> training.png),
# non dal numero: un report con le sezioni in un altro ordine le trova lo
# stesso, e una sezione senza icona resta col solo titolo.
REPORT_SECTION_ICONS = {
    "training": "training.png",
    "recovery": "recovery.png",
    "trend": "trend.png",
}
# Piu' piccole delle icone delle schede (40px): qui accompagnano un titolo
# dentro un testo, non aprono una scheda.
REPORT_ICON_PX = 28

# Le righe del file che ripetono quello che la pagina dice gia': il titolo
# ("# ...") e le righe di intestazione del settimanale ("Week: ...") e del
# giornaliero ("Window: ..." nei report vecchi, "Data: ..." nei nuovi). Il
# periodo e' la riga spuntata nella tabella accanto.
_HEADER_PREFIXES = ("# ", "Week: ", "Window: ", "Data: ")


def _report_icon_path(title: str) -> Path | None:
    words = title.lower()
    for name, filename in REPORT_SECTION_ICONS.items():
        path = ICONS_DIR / filename
        if name in words and path.exists():
            return path
    return None


def show_report(path: Path, height: int, key: str, missing_text: str | None = None) -> None:
    """Il report in `path` in un riquadro grigio alto `height`, con il testo
    che scorre dentro. Senza file: `missing_text` in una riga, o niente.

    `key` da' il nome alla classe CSS del riquadro: una per pagina."""
    if not path.exists():
        if missing_text:
            st.caption(missing_text)
        return

    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.startswith(_HEADER_PREFIXES)
    ]

    # Le sezioni ("## 1. Training", ...) una per una: ognuna ha la sua riga di
    # titolo con l'icona accanto, come le schede per sport. Il testo prima della
    # prima sezione, se c'e', sta in una sezione senza titolo: e' tutto il
    # report giornaliero, che ha paragrafi in grassetto e non sezioni.
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in lines:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)

    # Uno sfondo grigio chiaro, senza bordo, per staccare il testo dalla tabella
    # accanto. E' l'unica eccezione voluta (da Andrea) alla regola "niente CSS"
    # dell'app: Streamlit non ha un colore di sfondo per i contenitori, e i
    # riquadri nativi (`st.info` e simili) sono azzurri, verdi o gialli, colori
    # che dicono uno stato. La regola tocca solo questo contenitore, tramite la
    # classe che Streamlit da' a chi ha una `key` (`st-key-<key>`). Il grigio e'
    # semitrasparente: chiaro sul tema chiaro, tenue su quello scuro.
    st.html(
        f"<style>.st-key-{key} {{"
        " background-color: rgba(128, 128, 128, 0.08);"
        " border-radius: 0.5rem; padding: 1rem 1.25rem; }</style>"
    )
    with st.container(height=height, border=False, key=key):
        for title, text in sections:
            if title:
                head = st.container(horizontal=True, vertical_alignment="center")
                icon_path = _report_icon_path(title)
                if icon_path:
                    head.image(icon_path, width=REPORT_ICON_PX)
                # In grassetto e non "####": un titolo markdown porta con se' un
                # margine sopra che, accanto all'icona, la lascerebbe piu' in basso
                # del testo.
                head.markdown(f"**{title}**")
            body = "\n".join(text).strip()
            if body:
                st.markdown(body)
