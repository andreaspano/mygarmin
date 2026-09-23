"""La macchina delle pagine per periodo: Week e Month.

Le due pagine mostrano la stessa cosa con un'unita' di tempo diversa: tabella
dei totali, schede per sport, elenco attivita' e, in fondo, i grafici. Quel che
cambia e' solo il periodo, e sta nel file della pagina; qui c'e' tutto il resto.

Non era un file a parte finche' la pagina era una sola. Lo e' diventato quando
ne e' arrivata una seconda: delle 1.020 righe di `week.py` meno di cento
parlavano davvero di settimane, e copiarle avrebbe duplicato anche i commenti
qui sotto, che sono la parte piu' difficile da riscrivere."""


import warnings
from collections.abc import Callable
from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import activity_table, sport_icon_path, sport_label
from training.interface.data import load_activities
from training.interface.filters import date_range


@dataclass(frozen=True)
class PeriodSpec:
    """Tutto cio' che cambia fra Week e Month. Il resto del modulo non sa che
    unita' di tempo sta guardando, ed e' voluto: se qui dentro servisse un
    `if spec.name == "week"`, vorrebbe dire che a questa spec manca un campo.

    Le funzioni (`bucket`, `bucket_end`, `label`, `point_label`) arrivano dal
    file della pagina: e' li' che sta scritto cosa vuol dire un periodo."""

    # Identita' della pagina.
    name: str  # "week" | "month": il prefisso di ogni chiave di sessione
    title: str  # "Week" | "Month": titolo della pagina e del tooltip
    unit: str  # "week" | "month": il nome dentro le frasi in inglese
    adjective: str  # "Weekly" | "Monthly": "Weekly totals", "Monthly totals"

    # Come si raggruppano le attivita'.
    bucket: Callable[[pd.Series], pd.Series]  # start_time -> inizio del periodo
    bucket_end: Callable[[pd.DatetimeIndex], pd.DatetimeIndex]  # inizio -> ultimo giorno
    freq: str  # il passo di pd.date_range sui periodi: "W-MON" | "MS"
    label: Callable[[pd.Timestamp], str]  # come si legge un periodo, per esteso

    # Asse dei tempi e tooltip.
    axis_format: str  # "w%V" | "%b"
    axis_interval: str  # "week" | "month": una tacca per periodo
    point_label: Callable[[pd.Series], pd.Series]  # "w38" | "Sep 2026", nel tooltip
    tooltip_start_format: str | None  # None toglie la riga "Starting"

    # Annotazioni: i confini del livello sopra (i mesi su un asse a settimane,
    # gli anni su uno a mesi).
    boundary_freq: str  # "MS" | "YS"
    boundary_format: str  # "%b" | "%Y"
    boundary_min_share: float  # vedi _boundary_layers()

    # Tabella dei totali: solo la prima colonna cambia, le altre si scrivono
    # da se' a partire da `unit`.
    column_header: str  # "Week" | "Month"
    column_format: str  # "D MMM YYYY" | "MMMM YYYY"
    column_width: int
    column_help: str

    # Il gruppo di scorciatoie del filtro a calendario (vedi filters.py).
    presets: str

    def key(self, *parts: str) -> str:
        """Ogni chiave di sessione della pagina passa di qui.

        Senza il nome della pagina davanti, Week e Month si scriverebbero
        addosso: il suffisso che le distingueva era l'intervallo di date, e con
        "All" su tutte e due e' lo stesso. Quella della tabella non si
        limiterebbe a sporcare lo stato, farebbe cadere la pagina: la riga
        selezionata si rilegge prima che la tabella esista, e la riga 40 di 55
        settimane letta su 21 mesi e' un IndexError."""
        return "_".join((self.name, *parts))


# Configurazione della tabella dei totali di periodo. Segue le convenzioni
# della tabella delle attivita' (activity_table.py): numeri a destra, unita' di
# misura nell'intestazione, larghezze fisse. Le due tabelle stanno nella stessa
# pagina e devono leggersi come una cosa sola.
#
# L'unita' compare una volta sola per numero, e dove compare dipende da dove si
# legge il numero:
#   - tabelle: nell'intestazione ("Distance (km)"), mai nella cella;
#   - schede:  nel valore ("77.5 km"), l'etichetta resta nuda ("Distance");
#   - grafici: nel titolo dell'asse ("km"), perche' il titolo del grafico dice
#              gia' di che grandezza si tratta.
# L'eccezione sono le durate: "08:28" porta con se' il proprio formato, e
# ripetere l'unita' accanto non aggiungerebbe niente.
# Le stesse tre grandezze della tabella delle attivita', con le stesse
# intestazioni corte: una tabella si scorre con gli occhi, e "km" si legge piu'
# in fretta di "Distance (km)". La FC media non c'e' piu', come nell'altra
# tabella: sta nelle schede qui sotto, dove c'e' spazio per un'etichetta intera.
TABLE_COLUMNS = ["period_start", "n", "distance", "time", "d+"]


def _column_config(spec: PeriodSpec) -> dict:
    """La configurazione della tabella dei totali.

    Solo la prima colonna cambia davvero fra le due pagine (intestazione,
    formato della data, `help`): le altre quattro si scrivono da se' a partire
    da `spec.unit`, cosi' "of the week" e "of the month" non sono due elenchi
    da tenere allineati a mano."""
    return {
        "period_start": st.column_config.DatetimeColumn(
            spec.column_header,
            format=spec.column_format,
            width=spec.column_width,
            help=spec.column_help,
        ),
        "n": st.column_config.NumberColumn(
            "Activities",
            format="%d",
            width=95,
            alignment="right",
            help=f"Number of activities in the {spec.unit}.",
        ),
        "distance": st.column_config.NumberColumn(
            "km",
            format="%.1f",
            width=80,
            alignment="right",
            help=f"Total distance of the {spec.unit}.",
        ),
        # In ore e minuti e non in minuti come nella tabella delle attivita':
        # un totale di periodo sono ore ("07:18"), e in minuti sarebbe un 438
        # da convertire a mente. Sulla Month le ore arrivano a tre cifre
        # ("67:37") e la colonna le regge senza allargarsi.
        "time": st.column_config.TextColumn(
            "h:mm",
            width=80,
            alignment="right",
            help=f"Total duration of the {spec.unit}, hours:minutes.",
        ),
        "d+": st.column_config.NumberColumn(
            "D+",
            format="%.0f",
            width=70,
            alignment="right",
            help=f"Total elevation gain of the {spec.unit}, in metres.",
        ),
    }


def _hm(hours: float) -> str:
    """Ore decimali in "hh:mm" (1.8 -> "01:48").

    st.dataframe non ha un formato per le durate, quindi la cella e' testo.
    Le ore stanno sempre su due cifre: cosi' la colonna resta incolonnata e
    l'ordinamento alfabetico coincide con quello cronologico. Si arrotondano i
    minuti, non le ore, per non far comparire un "01:60"."""
    if pd.isna(hours):
        return ""
    minutes = round(hours * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _totals(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Totali (n, distanza, tempo, dislivello, FC, velocita', VO2max)
    raggruppati per `key`.

    La FC media e' pesata sulla durata (una sgambata di 20' non puo' pesare
    come un'uscita di 5h) e considera solo le attivita' che hanno davvero un
    dato di FC: le altre non entrano ne' al numeratore ne' al denominatore.

    Distanza, tempo e dislivello si sommano; le altre tre no, e ognuna ha la
    sua regola. La velocita' e' distanza totale su tempo in movimento totale
    (vedi le colonne `_speed_*`). Il VO2max e' l'ultimo del gruppo, non una
    media: e' il valore corrente dell'orologio, quindi il piu' recente e'
    l'unico che valga qualcosa (`last` di pandas salta gia' i vuoti)."""
    ordered = df.sort_values("start_time")
    grouped = ordered.groupby(key).agg(
        n=("activity_id", "count"),
        distance=("total_distance_km", "sum"),
        time_min=("total_time_min", "sum"),
        ascent=("total_ascent_m", "sum"),
        hr_weighted=("_hr_weighted", "sum"),
        hr_time=("_hr_time", "sum"),
        speed_distance=("_speed_distance", "sum"),
        speed_time=("_speed_time", "sum"),
        vo2max=("vo2max", "last"),
    )
    return pd.DataFrame(
        {
            "n": grouped["n"],
            "distance": grouped["distance"],
            "time": grouped["time_min"] / 60,
            "d+": grouped["ascent"],
            # Gruppi senza nessuna attivita' con FC: cella vuota, non uno zero.
            "hr": (grouped["hr_weighted"] / grouped["hr_time"]).where(grouped["hr_time"] > 0),
            # Stessa regola per chi non ha nessuna attivita' con velocita'
            # (una settimana di sola palestra).
            "speed": (grouped["speed_distance"] / grouped["speed_time"]).where(
                grouped["speed_time"] > 0
            ),
            "vo2max": grouped["vo2max"],
        }
    )


def _by_period(
    df: pd.DataFrame,
    value: str,
    periods: pd.DatetimeIndex,
    scale: float = 1.0,
    with_total: bool = True,
) -> pd.DataFrame:
    """`value` sommato per settimana, una colonna per sport e, se richiesto,
    il totale degli sport selezionati.

    I periodi senza attivita' non esistono nel pivot: reindicizzando su
    tutti i lunedi' del periodo restano a zero, cosi' le pause di allenamento
    si vedono invece di sparire con una linea che salta il buco."""
    by_period_sport = df.pivot_table(
        index="period_start", columns="sport", values=value, aggfunc="sum"
    )
    by_period_sport = by_period_sport.reindex(periods).fillna(0) * scale
    # Con un solo sport il totale ricalcherebbe esattamente la sua linea.
    if with_total and by_period_sport.shape[1] > 1:
        by_period_sport[TOTAL_SERIES] = by_period_sport.sum(axis=1)
    return by_period_sport


# La larghezza in pixel non e' una pigrizia, e' l'unica strada: due pannelli
# affiancati con il crosshair in comune si pagano cosi'.
#
# Perche' la verticale si muova insieme sul grafico settimanale e sul suo
# cumulato, i due devono stare in una vista Vega sola (fra viste distinte i
# segnali non passano), cioe' in un `hconcat`. E un `hconcat` non sa adattarsi
# al contenitore: provato, `autosize: fit-x` lo fa collassare a larghezza
# zero, e con `fit` o `pad` la larghezza resta quella scritta qui. Il frontend
# di Streamlit passa la larghezza misurata ai figli di un `vconcat`, ma non
# scende dentro gli `hconcat`. Nemmeno calcolarla si puo': `st.context` non
# espone la larghezza della finestra.
#
# Tarata per stare in una finestra da 1440 con la sidebar aperta: li' la
# sezione richiudibile che ospita la riga lascia al grafico 946px (la pagina
# ne ha 980, il bordo della sezione se ne prende 34). Attenzione, si misura sul
# contenitore del grafico, non sull'area principale della pagina, che a 1440
# e' 1.140: la differenza sono i margini, e sbagliare misura vuol dire
# scoprire lo sbordamento dopo.
#
# La barra di scorrimento non compare fino a 1440 con la sidebar aperta, e mai
# con la sidebar chiusa. Sotto, torna a sforare: basta chiudere la sidebar,
# oppure abbassare questo numero.
CHARTS_TOTAL_WIDTH = 914
_AXIS_WIDTH = 55  # l'asse y di ogni pannello, fuori dall'area di disegno
_VEGA_PADDING = 94  # margini interni e titoli degli assi y, misurati nel browser

# `width` in Vega e' la sola area di disegno: assi e margini si aggiungono, e
# qui si tolgono in anticipo perche' CHARTS_TOTAL_WIDTH sia davvero la
# larghezza che il blocco occupa sullo schermo.
CHART_WIDTH = (CHARTS_TOTAL_WIDTH - _VEGA_PADDING) // 2 - _AXIS_WIDTH
CHART_HEIGHT = 240

# L'area del totale ha un colore suo, arancione, invece di pescare dalla
# tavolozza categorica (dove finiva su un marrone smorto). Le linee dei sport
# usano la tavolozza di default meno l'arancione, per non confondersi con lei.
# Il totale non e' uno sport: e' una serie in piu', e questo e' il suo nome
# ovunque, dalla colonna del pivot alla voce di legenda.
TOTAL_SERIES = "Total"

TOTAL_COLOR = "#f97316"
_SPORT_COLORS = [
    "#4c78a8",
    "#e45756",
    "#72b7b2",
    "#54a24b",
    "#b279a2",
    "#ff9da6",
    "#9d755d",
    "#bab0ac",
    "#eeca3b",
]


def _sport_colors(sports: list[str]) -> dict[str, str]:
    """Un colore per sport, assegnato una volta sola su tutti gli sport
    presenti nei dati: cosi' resta lo stesso cambiando periodo o togliendo
    caselle, invece di scalare sugli sport rimasti."""
    return {sport: _SPORT_COLORS[i % len(_SPORT_COLORS)] for i, sport in enumerate(sports)}


def _series_label(name: str) -> str:
    """Il nome di una serie come si legge nei grafici.

    Le serie sono gli sport piu' "Total": gli sport passano da `sport_label()`
    come ovunque altrove, il totale non e' uno sport e resta com'e'."""
    return name if name == TOTAL_SERIES else sport_label(name)


# Il grigio delle voci spente: lo stesso della verticale del crosshair.
_OFF_COLOR = "#9ca3af"

# Le verticali dei cambi di mese: un grigio neutro (la griglia orizzontale
# del tema tira all'azzurro, e accanto a lei un grigio-azzurro si confondeva)
# e un tratto sotto il pixel, che l'antialiasing rende piu' tenue: devono
# esserci per chi le cerca, non farsi notare da chi guarda le serie.
BOUNDARY_LINE_COLOR = "#d4d4d4"
BOUNDARY_LINE_WIDTH = 0.6
# I nomi dei confini sopra i pannelli: lo stesso grigio delle etichette degli
# assi.
BOUNDARY_LABEL_COLOR = "#808495"
# Quanta parte del periodo deve occupare un tratto per avere il suo nome sta
# in `spec.boundary_min_share`, perche' dipende da quanto e' lunga la scritta.
# L'aritmetica, su un pannello da CHART_WIDTH (355px) e a fontSize 11: "Sep"
# occupa ~20px, cioe' il 4% (la soglia della Week); "2026" ne occupa ~25, cioe'
# il 7% (quella della Month).


def _series_symbol(name: str, colors: dict[str, str], on: bool) -> str:
    """L'etichetta di una voce della riga di legenda: simbolo colorato e nome.

    Il simbolo e' un'icona Material dentro la direttiva `:color[...]{...}` del
    Markdown di Streamlit, che accetta un esadecimale qualunque: l'icona non
    ha un colore suo e prende quello. Accesa e' l'anello con il pallino in
    mezzo, del colore della serie; spenta e' l'anello vuoto, grigio.

    La stringa non deve cominciare con l'icona nuda: Streamlit la staccherebbe
    dall'etichetta per disegnarla a parte, fuori dal Markdown, e il colore
    andrebbe perso. Cominciando con `:color[` resta tutta nel Markdown."""
    icon = "radio_button_checked" if on else "radio_button_unchecked"
    color = (TOTAL_COLOR if name == TOTAL_SERIES else colors[name]) if on else _OFF_COLOR
    return f':color[:material/{icon}:]{{foreground="{color}"}} {_series_label(name)}'


def _color_scale(series_names: list[str], colors: dict[str, str]) -> alt.Scale:
    """La stessa scala per tutti i pannelli e per la riga di legenda.

    Prende i nomi grezzi e restituisce la scala gia' con le etichette: dominio
    e colori si costruiscono insieme, cosi' non possono sfasarsi.

    Dominio esplicito: dentro un grafico ogni layer vede solo una parte delle
    serie, e senza fissare la scala il totale si prenderebbe il colore del
    primo sport. Fra un grafico e l'altro e' quello che garantisce che lo
    stesso sport resti dello stesso colore, ora che non c'e' piu' una vista
    unica a condividere la scala."""
    return alt.Scale(
        domain=[_series_label(name) for name in series_names],
        range=[TOTAL_COLOR if name == TOTAL_SERIES else colors[name] for name in series_names],
    )


def _boundary_layers(
    index: pd.DatetimeIndex, x: alt.X, spec: PeriodSpec
) -> list[alt.Chart]:
    """Gli strati che segnano i confini del livello sopra il periodo: i mesi
    su un asse a settimane, gli anni su uno a mesi.

    Fra le due pagine cambiano tre cose sole: ogni quanto cade un confine
    (`boundary_freq`), come si scrive (`boundary_format`) e quanto dev'essere
    largo un tratto perche' ci stia il nome (`boundary_min_share`)."""
    # Una verticale leggera dove cambia il mese: l'asse conta in settimane
    # ISO, e senza un riferimento "w31" non dice a nessuno che e' fine luglio.
    # Sta sul primo del mese, che sull'asse a settimane cade fra due lunedi';
    # su quello a mesi il primo di gennaio cade invece esattamente su un punto,
    # e la linea gli finisce sotto, che va bene. E' il primo strato, cosi'
    # resta dietro a tutto. Solo i confini *dentro* il periodo: uno sul bordo
    # allargherebbe l'asse, e uno strato senza dati farebbe brontolare Vega
    # ("Infinite extent"). Da cui una conseguenza da sapere: un periodo che
    # comincia a gennaio non ha la linea di quell'anno (con "All" le linee
    # sono una sola, al 2026-01-01), ma le etichette restano due, perche'
    # `edges` include sempre i due estremi.
    # La colonna si chiama `period_start` come quella dei dati, anche se qui
    # porta un inizio di mese o di anno: con lo stesso campo e la stessa
    # codifica `x` gli strati condividono asse e titolo senza che Vega li
    # fonda in "period_start, boundary_start".
    first_period, last_period = index.min(), index.max()
    boundaries = pd.date_range(first_period, last_period, freq=spec.boundary_freq)
    boundaries = boundaries[(boundaries > first_period) & (boundaries < last_period)]

    layers = []
    if len(boundaries):
        layers.append(
            alt.Chart(pd.DataFrame({"period_start": boundaries}))
            .mark_rule(color=BOUNDARY_LINE_COLOR, strokeWidth=BOUNDARY_LINE_WIDTH)
            .encode(x=x)
        )

    # Il nome sopra il pannello, al centro del suo tratto: fra due verticali,
    # oppure fra una verticale e il bordo per il primo e l'ultimo, che di
    # solito entrano nel periodo solo in parte. E' un testo appoggiato al bordo
    # superiore (`y` a zero pixel, spinto su da `dy`) e non un secondo asse: un
    # asse in alto vorrebbe assi indipendenti fra gli strati, e allora ogni
    # strato ridisegnerebbe anche quello in basso.
    #
    # Un tratto troppo corto per reggere la scritta resta senza nome: con
    # "This year" la w01 comincia il 29 dicembre, e quei tre giorni mettevano
    # un "Dec" addosso a "Jan". Sulla Month lo stesso vale per un mese di coda
    # ritagliato a mano, che scriverebbe il suo anno addosso al successivo.
    edges = [first_period, *boundaries, last_period]
    span = last_period - first_period
    segments = [
        (a, b)
        for a, b in zip(edges, edges[1:])
        if not span or (b - a) / span >= spec.boundary_min_share
    ]
    if segments:
        # `strftime` e non una f-string: il formato arriva da fuori, e una
        # f-string non prende il proprio formato da una variabile.
        middles = [a + (b - a) / 2 for a, b in segments]
        labels = pd.DataFrame(
            {
                "period_start": middles,
                "boundary": [m.strftime(spec.boundary_format) for m in middles],
            }
        )
        layers.append(
            alt.Chart(labels)
            .mark_text(baseline="bottom", dy=-4, fontSize=11, color=BOUNDARY_LABEL_COLOR)
            .encode(x=x, y=alt.value(0), text="boundary:N")
        )
    return layers


def _chart(
    spec: PeriodSpec,
    by_period_sport: pd.DataFrame,
    y_label: str,
    title: str,
    picked: alt.Parameter,
    hover: alt.Parameter,
    colors: dict[str, str],
    show_x_title: bool = True,
    integer: bool = False,
) -> alt.LayerChart:
    """Costruisce (senza disegnarlo) un pannello: l'area del totale, le linee
    per sport, il crosshair e i punti che raccolgono il click.

    `picked` e `hover` arrivano da fuori e sono lo stesso oggetto per tutti i
    pannelli. Il segnale e' condiviso fra i due pannelli della stessa riga,
    che stanno in una vista Vega sola (`_row_spec()`): la verticale
    tratteggiata si muove insieme sul pannello di periodo e sul cumulato. Fra
    una riga
    e l'altra no, perche' ogni riga e' una vista a se'; li' lo stesso oggetto
    serve solo a tenere fermo il nome con cui si rilegge la selezione.

    Le etichette dei periodi (w26, w27, ... oppure Jan, Feb, ...) stanno sotto
    ogni pannello:
    con quattro righe, chi guarda un pannello in alto non deve scendere fino
    in fondo alla griglia per sapere a che periodo corrisponde un picco.
    `show_x_title` riguarda solo il titolo dell'asse, che basta una
    volta, sull'ultima riga.

    `integer` e' per le grandezze che si contano invece di misurarsi (il
    numero di attivita'): l'asse non scende sotto il passo di uno, che con
    poche attivita' darebbe tacche a 0,5, e il tooltip non mostra decimali.

    La selezione viaggia su `period_key` (stringa) e non sulla data: cosi'
    torna indietro da Vega tale e quale, senza passare da epoch/millisecondi.

    Il titolo sta dentro il grafico e allineato a sinistra, come nella pagina
    Activities."""
    long = (
        by_period_sport.rename_axis("period_start")
        .reset_index()
        .melt(id_vars="period_start", var_name="series", value_name="value")
    )
    # Da qui in poi `series` e' l'etichetta, non la chiave: e' quello che
    # finisce in legenda e nel tooltip. `TOTAL_SERIES` attraversa la mappatura
    # immutato, quindi i confronti qui sotto continuano a valere.
    long["series"] = long["series"].map(_series_label)
    long["period_key"] = long["period_start"].dt.strftime("%Y-%m-%d")
    # Il nome del punto (il numero di settimana ISO, o il mese e l'anno):
    # calcolato qui e non nel grafico perche' serve al tooltip, ed e' anche il
    # riscontro di quello che l'asse deve mostrare.
    long["point_label"] = spec.point_label(long["period_start"])

    # L'asse resta temporale (e' quello che tiene le distanze giuste fra i
    # periodi, comprese le pause), ma i tick cadono su ogni periodo invece che
    # sui confini del livello sopra: cosi' ogni etichetta corrisponde davvero a
    # un punto della serie. Vega nasconde da se' quelle che si
    # sovrapporrebbero.
    x = alt.X(
        "period_start:T",
        title=spec.unit if show_x_title else None,
        axis=alt.Axis(
            format=spec.axis_format,
            tickCount={"interval": spec.axis_interval, "step": 1},
        ),
    )
    # `minExtent`: lo stesso spazio per l'asse y in tutti i pannelli, qualunque
    # sia la larghezza delle sue etichette ("5" o "12,000"). Le righe sono
    # viste separate e Vega non le allinea piu' fra loro: senza, ogni riga
    # cominciava qualche pixel piu' in la' della precedente, e la piu' larga
    # decideva da sola se il blocco stava nel contenitore.
    y = alt.Y(
        "value:Q",
        title=y_label,
        axis=alt.Axis(minExtent=_AXIS_WIDTH, tickMinStep=1 if integer else alt.Undefined),
    )
    # Legenda spenta: la legenda e' la riga di pills sopra i grafici, che porta
    # gli stessi colori e in piu' si clicca. Due elenchi delle stesse voci, uno
    # sopra l'altro, erano il problema da togliere.
    series_names = [str(c) for c in by_period_sport.columns]
    color = alt.Color(
        "series:N",
        title=None,
        scale=_color_scale(series_names, colors),
        legend=None,
    )

    layers = _boundary_layers(by_period_sport.index, x, spec)

    # Il totale e' solo un'area riempita sullo sfondo, senza bordo: fa da ombra
    # sotto ai singoli sport, che ci passano sopra leggibili.
    total = long[long["series"] == TOTAL_SERIES]
    if not total.empty:
        layers.append(
            alt.Chart(total).mark_area(fillOpacity=0.25).encode(x=x, y=y, color=color)
        )

    by_sport = long[long["series"] != TOTAL_SERIES]
    if not by_sport.empty:
        layers.append(alt.Chart(by_sport).mark_line().encode(x=x, y=y, color=color))

    # La riga "Starting" serve dove il nome del punto non dice l'anno ("w38");
    # dove lo dice gia' ("Sep 2026") non aggiungerebbe niente, e la spec la
    # toglie mettendo `tooltip_start_format` a None.
    tooltip = [alt.Tooltip("point_label:N", title=spec.title)]
    if spec.tooltip_start_format:
        tooltip.append(
            alt.Tooltip("period_start:T", title="Starting", format=spec.tooltip_start_format)
        )
    tooltip += [
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("value:Q", title=y_label, format=".0f" if integer else ".1f"),
    ]

    # Punti trasparenti: non si vedono (restano solo le linee) ma sono loro a
    # raccogliere il click sul periodo e a guidare il crosshair, percio' si
    # tengono larghi per avere un bersaglio comodo.
    layers.append(
        alt.Chart(long)
        .mark_point(size=55, filled=True, opacity=0)
        .encode(x=x, y=y, color=color, tooltip=tooltip)
        .add_params(picked, hover)
    )

    visible_on_hover = alt.condition(hover, alt.value(1), alt.value(0))
    layers.append(
        alt.Chart(long)
        .mark_rule(color="#9ca3af", strokeDash=[4, 4])
        .encode(x=x, opacity=visible_on_hover)
    )
    layers.append(
        alt.Chart(long)
        .mark_point(size=55, filled=True)
        .encode(x=x, y=y, color=color, opacity=visible_on_hover)
    )

    return alt.layer(*layers).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title=alt.TitleParams(title, anchor="start")
    )


def _row_spec(panels: list[alt.LayerChart]) -> dict:
    """I due pannelli di una riga (settimanale e cumulato) in una vista Vega.

    Una vista per riga, e non una per tutta la griglia, perche' ogni riga sta
    dentro la sua sezione richiudibile (`st.expander`), e un elemento di
    Streamlit e' una vista. Il crosshair e' quindi condiviso dentro la riga, fra
    il grafico di periodo e il suo cumulato, e non fra una riga e l'altra: fra
    viste Vega distinte i segnali non passano (provato nel todo 03).

    La larghezza resta fissa, spiegato su `CHARTS_TOTAL_WIDTH`: un `hconcat`
    non si adatta al contenitore. L'autosize non lo tocchiamo: Streamlit mette
    `pad` da solo, che e' "nessun adattamento", cioe' quello che serve avendo
    gia' deciso noi i pixel.

    `resolve_scale(color="shared")` tiene la stessa scala dei colori nei due
    pannelli; fra una riga e l'altra ci pensa `_color_scale()`, che e' la
    stessa per tutti."""
    # Passare lo stesso `picked`/`hover` ai due pannelli e' voluto: e' cosi'
    # che il segnale e' uno solo dentro la riga. Altair vede il parametro
    # ripetuto, lo deduplica (che e' quello che vogliamo) e avvisa a ogni rerun.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")
        return alt.hconcat(*panels).resolve_scale(color="shared").to_dict()


def _period_total(
    df: pd.DataFrame, value: str, periods: pd.DatetimeIndex, scale: float = 1.0
) -> pd.Series:
    """`value` sommato per settimana su tutti gli sport insieme."""
    return df.groupby("period_start")[value].sum().reindex(periods).fillna(0) * scale


def _pair(
    spec: PeriodSpec,
    plotted: pd.DataFrame,
    everything: pd.DataFrame,
    value: str,
    periods: pd.DatetimeIndex,
    y_label: str,
    title: str,
    picked: alt.Parameter,
    hover: alt.Parameter,
    colors: dict[str, str],
    scale: float = 1.0,
    with_total: bool = True,
    show_x_title: bool = False,
    integer: bool = False,
) -> list[alt.LayerChart]:
    """La stessa grandezza due volte: prima periodo per periodo, poi il
    cumulato dall'inizio dell'intervallo (quanto si e' messo insieme finora).

    Restituisce i due pannelli in una lista: ad affiancarli in una vista sola
    ci pensa `_row_spec()`.

    `show_x_title` vale per tutti e due, perche' i due stanno sulla stessa
    riga della griglia: il titolo dell'asse dei tempi lo porta solo l'ultima.

    Nel cumulato il totale e' quello di *tutti* gli sport, non solo di quelli
    selezionati: le caselle scelgono quali linee guardare, ma il monte
    complessivo di km/ore/dislivello resta quello vero."""
    cumulative = _by_period(plotted, value, periods, scale, with_total=False).cumsum()
    # Con un solo sport selezionato il totale sparisce da tutti e due i
    # grafici: si sta guardando quello sport, non il quadro d'insieme.
    if with_total and cumulative.shape[1] > 1:
        cumulative[TOTAL_SERIES] = _period_total(everything, value, periods, scale).cumsum()

    return [
        _chart(
            spec,
            _by_period(plotted, value, periods, scale, with_total=with_total),
            y_label,
            title,
            picked,
            hover,
            colors,
            show_x_title=show_x_title,
            integer=integer,
        ),
        _chart(
            spec,
            cumulative,
            y_label,
            f"{title} (cumulative)",
            picked,
            hover,
            colors,
            show_x_title=show_x_title,
            integer=integer,
        ),
    ]


# Le righe della griglia, nell'ordine delle colonne della tabella dei totali.
# Ogni riga e' una grandezza disegnata due volte (settimanale e cumulato):
# colonna da sommare, unita' sull'asse, titolo, e gli argomenti in piu' che
# `_pair()` vuole per lei.
CHART_ROWS = {
    "Activities": ("_count", "count", {"integer": True}),
    "Distance": ("total_distance_km", "km", {}),
    "Duration": ("total_time_min", "h", {"scale": 1 / 60}),
    "Elevation gain": ("total_ascent_m", "m", {}),
}


def _clicked_period(event) -> str | None:
    """La settimana selezionata in una riga di grafici, o None.

    Ogni riga e' una vista a se', con la sua selezione, che resta accesa
    finche' non la si azzera: per sapere quale click e' quello appena fatto
    bisogna guardare quale riga e' *cambiata*, e lo fa chi chiama."""
    selection = (event.selection or {}).get("picked", []) if event else []
    for item in selection:
        value = item.get("period_key") if isinstance(item, dict) else item
        for picked in value if isinstance(value, list) else [value]:
            if picked:
                return picked
    return None


def render(spec: PeriodSpec) -> None:
    """Disegna la pagina, dal titolo all'elenco delle attivita'."""
    st.title(spec.title)

    activities = load_activities(DATA_DIR)

    if activities.empty:
        st.info(f"No *_ACTIVITY.fit file found in {DATA_DIR.resolve()}.")
        st.stop()

    # Ogni attivita' finisce nel suo periodo (il lunedi' della settimana, il
    # primo del mese): e' la chiave con cui raggruppiamo, ed e' l'unico punto
    # in cui si decide cosa sia un periodo. Tutto il resto del modulo lavora
    # sulla colonna `period_start` senza sapere che unita' porta.
    activities = activities.copy()
    activities["period_start"] = spec.bucket(activities["start_time"])
    sport_colors = _sport_colors(sorted(activities["sport"].dropna().unique()))

    activities["_hr_weighted"] = activities["avg_heart_rate"] * activities["total_time_min"]
    activities["_hr_time"] = activities["total_time_min"].where(
        activities["avg_heart_rate"].notna()
    )
    # La velocita' di un gruppo e' la distanza totale divisa per il tempo in
    # movimento totale, come quella di una singola attivita' (vedi
    # `fit._avg_speed_kmh`). Il tempo in movimento non e' in tabella, ma si
    # ricava: distanza / velocita' dell'attivita'. Sommare quello, invece di
    # `total_time_min` (che e' il tempo totale, soste comprese), e' cio' che
    # tiene il numero della settimana coerente con quelli delle sue attivita'.
    # Chi non ha velocita' resta fuori da entrambe le somme: la palestra, che ha
    # distanza e velocita' a zero, non deve tirare giu' la media.
    _moving = activities["total_distance_km"] / activities["avg_speed_kmh"].where(
        activities["avg_speed_kmh"] > 0
    )
    activities["_speed_distance"] = activities["total_distance_km"].where(_moving.notna())
    activities["_speed_time"] = _moving
    # Un uno per attivita': i grafici sommano una colonna per settimana e sport, e
    # sommando questa si ottiene il conteggio senza una strada a parte.
    activities["_count"] = 1

    period_totals = _totals(activities, "period_start").sort_index(ascending=False)

    # Lo stesso filtro a calendario della pagina Activities: stessa funzione,
    # non una copia. Qui pero' con le scorciatoie di periodo, perche' una
    # pagina cosi' si guarda quasi sempre sugli ultimi periodi e non su tutto
    # lo storico (che sono quasi novanta punti per grafico a settimane).
    start_date, end_date = date_range(
        activities,
        None,
        f"'From' is later than 'To': swap the two dates to see the {spec.unit}s.",
        presets=True,
        period=spec.presets,
        key=spec.key("dates"),
    )

    # Un periodo entra se si sovrappone all'intervallo, non solo se ci cade
    # dentro il primo giorno: scegliendo un mercoledi' ci si aspetta di vedere
    # anche la settimana che lo contiene, e un 15 del mese il suo mese intero.
    period_end = spec.bucket_end(period_totals.index)
    period_totals = period_totals[
        (period_totals.index.date <= end_date) & (period_end.date >= start_date)
    ]

    if period_totals.empty:
        st.info("No activity in the selected period.")
        st.stop()

    summary = period_totals.reset_index()
    # Il tempo diventa testo "hh:mm" solo per la tabella: `period_totals` resta
    # numerico, perche' alimenta anche i grafici e le schede per sport.
    summary["time"] = summary["time"].map(_hm)

    # La selezione e' per indice di riga: cambiando intervallo cambiano le
    # righe, quindi la tabella va rimontata (key diversa) per non ereditare una
    # selezione che ora punterebbe a periodi diversi. Il nome della pagina
    # davanti non e' un vezzo: le due pagine con "All" hanno lo stesso
    # intervallo, e la riga 40 di 55 settimane riletta su 21 mesi e' un
    # IndexError (vedi PeriodSpec.key).
    range_key = f"{start_date}_{end_date}"
    table_key = spec.key("table", range_key)

    # Anche la memoria di cosa era selezionato porta l'intervallo. I widget si
    # azzerano da soli cambiandolo (la key cambia), ma queste chiavi no: senza
    # il suffisso, il primo giro dopo il cambio confrontava la selezione nuova
    # con periodi di prima.
    prev_chart_key = spec.key("prev_chart", range_key)
    prev_rows_key = spec.key("prev_rows", range_key)
    prev_table_key = spec.key("prev_table", range_key)
    source_key = spec.key("source", range_key)

    # La tabella si legge per prima ma va creata per ultima. Lo stato di un widget
    # si puo' impostare solo prima di crearlo: disegnando i grafici per primi, al
    # momento di creare la tabella sappiamo gia' su quale periodo e' caduto il
    # click, e possiamo spuntare la riga giusta subito. E' il motivo per cui qui
    # non serve piu' rilanciare lo script: un click su un grafico costa un giro
    # invece di due. Prenotiamo il posto, riempiamo piu' sotto.
    table_area = st.container()
    # Stesso trucco, e per un motivo in piu': schede ed elenco dicono com'e'
    # andato il periodo scelto, e quale sia lo si sa solo dopo aver letto i
    # click sui grafici. Prenotare qui il posto li mette sotto la tabella e sopra i grafici,
    # cioe' vicino alla riga da cui nascono, senza doverli disegnare prima di
    # sapere cosa mostrare.
    cards_area = st.container()
    list_area = st.container()

    st.subheader(f"{spec.adjective} volume by sport")
    in_range = activities[activities["period_start"].isin(period_totals.index)]

    # Che questo filtro valga solo per i grafici era scritto unicamente qui nel
    # sorgente: ora lo dice la pagina, perche' e' chi guarda che deve saperlo.
    st.caption("Charts only — the tables on this page always cover every sport.")

    sport_options = sorted(in_range["sport"].dropna().unique())

    # La chiave porta il periodo come gia' fanno tabella e grafici: le voci
    # disponibili cambiano con l'intervallo, e il widget deve rimontarsi con loro.
    #
    # Ma la chiave da sola non basta, ed e' il punto del problema: Streamlit
    # scarta lo stato dei widget che un giro non ha disegnato. Prima succedeva a
    # uno sport uscito dall'intervallo (la sua casella spariva, e al rientro era
    # di nuovo accesa); con una chiave per periodo succederebbe a tutta la fila
    # ogni volta che si cambia intervallo. Percio' quello che l'utente ha spento
    # si ricorda a parte, in una chiave che non appartiene a nessun widget e che
    # quindi nessuno ripulisce: uno sport spento resta spento anche se sparisce
    # dall'intervallo e poi ritorna.
    sports_off = set(st.session_state.get(spec.key("sports_off"), ()))
    sport_key = spec.key("sports", range_key)
    if sport_key not in st.session_state:
        st.session_state[sport_key] = [s for s in sport_options if s not in sports_off]

    # Una riga sola fa da legenda e da filtro: ogni voce porta il colore della sua
    # serie, e cliccandola si spegne (diventa grigia, e la linea sparisce dai
    # grafici). Sono due widget affiancati e non uno, per via del totale: vedi
    # sotto.
    legend_row = st.container(horizontal=True)

    # `format_func` sa quali voci sono accese leggendo lo stato del widget, che
    # Streamlit scrive prima di far partire lo script: e' gia' quello di questo
    # giro, non del precedente.
    plotted_sports = legend_row.pills(
        "Sports",
        sport_options,
        format_func=lambda sport: _series_symbol(
            sport, sport_colors, sport in st.session_state.get(sport_key, ())
        ),
        selection_mode="multi",
        key=sport_key,
        label_visibility="collapsed",
        wrap=False,
    )

    # Gli sport spenti adesso, piu' quelli spenti in periodi dove non compaiono:
    # la memoria vale per tutta la sessione, non per l'intervallo aperto.
    st.session_state[spec.key("sports_off")] = sorted(
        (sports_off - set(sport_options)) | (set(sport_options) - set(plotted_sports))
    )

    # Il totale sta nella stessa riga ma in un widget suo. E' una serie che esiste
    # solo da due sport in su (con uno solo ricalcherebbe la sua linea, vedi
    # `_by_period`), e in quel caso la voce deve restare li', grigia e non
    # cliccabile: `disabled` pero' vale per un widget intero, non per una voce
    # sola. Da quinta pill del primo widget sarebbe stata solo grigia d'aspetto.
    total_available = len(plotted_sports) > 1
    # Chiave nuova rispetto al toggle di prima: li' lo stato era un booleano, qui
    # e' una lista, e una sessione rimasta aperta li avrebbe confusi.
    total_key = spec.key("total", range_key)
    if total_key not in st.session_state:
        # Spento resta spento anche cambiando intervallo, come per gli sport.
        st.session_state[total_key] = (
            [] if st.session_state.get(spec.key("total_off"), False) else [TOTAL_SERIES]
        )

    total_picked = legend_row.pills(
        "Total",
        [TOTAL_SERIES],
        format_func=lambda name: _series_symbol(
            name, sport_colors, total_available and name in st.session_state.get(total_key, ())
        ),
        selection_mode="multi",
        key=total_key,
        disabled=not total_available,
        label_visibility="collapsed",
        help="The sum of the selected sports. Needs at least two sports: with one, "
        "the total would just retrace its line.",
    )
    # Con un solo sport la voce e' disabilitata e non ha voce in capitolo: non si
    # registra come una scelta dell'utente.
    if total_available:
        st.session_state[spec.key("total_off")] = TOTAL_SERIES not in total_picked
    plot_total = total_available and TOTAL_SERIES in total_picked

    chart_period = None
    if not plotted_sports:
        st.info("Select at least one sport to plot.")
    else:
        plotted = in_range[in_range["sport"].isin(plotted_sports)]
        all_periods = pd.date_range(
            period_totals.index.min(), period_totals.index.max(), freq=spec.freq
        )

        # Un solo oggetto per il click e uno per il crosshair, passati a tutti i
        # pannelli. Dentro una riga (una vista Vega, `_row_spec()`) il segnale e'
        # davvero uno; fra le righe no, e il nome esplicito e' la chiave con cui
        # la selezione di ogni riga si rilegge dal suo evento.
        picked = alt.selection_point(
            name="picked", fields=["period_key"], on="click", clear="dblclick", toggle=False
        )
        # Nome esplicito come per `picked`: e' la chiave con cui il parametro
        # compare nell'evento di selezione, e un nome stabile vale piu' del
        # `param_N` che Altair genererebbe da se'.
        hover = alt.selection_point(
            name="hovered",
            fields=["period_key"],
            nearest=True,
            on="pointermove",
            empty=False,
            clear="pointerout",
        )

        # Una sezione richiudibile per riga: il titolo della sezione e' il
        # pulsante, sulla stessa linea dei suoi grafici, e chiudendola la riga si
        # ripiega come un paragrafo. Dentro, i due pannelli: a sinistra la
        # grandezza settimana per settimana, a destra il suo cumulato.
        #
        # `on_change="rerun"` rende la sezione un widget con uno stato (`.open`):
        # una riga chiusa non viene costruita affatto. La memoria a parte serve per
        # lo stesso motivo degli sport: cambiando pagina il widget non viene
        # disegnato e Streamlit ne butta via lo stato, e al ritorno le righe
        # chiuse si sarebbero riaperte da sole.
        #
        # Lo stato iniziale si scrive nella chiave del widget, e solo quando il
        # widget non c'e' ancora (prima apertura, o ritorno da un'altra pagina).
        # Passarlo con `expanded=` sembrava equivalente e non lo era: quel valore
        # veniva dalla memoria, che cambia il giro dopo ogni click, e una sezione
        # che si vede cambiare un parametro sotto i piedi si perdeva il click
        # successivo. Ne servivano due per aprire o chiudere.
        rows_closed = set(st.session_state.get(spec.key("rows_closed"), ()))
        sections = {}
        for name, (value, _, _) in CHART_ROWS.items():
            row_key = spec.key("row", value)
            if row_key not in st.session_state:
                st.session_state[row_key] = name not in rows_closed
            sections[name] = st.expander(name, key=row_key, on_change="rerun")
        st.session_state[spec.key("rows_closed")] = [
            name for name, section in sections.items() if not section.open
        ]

        # Il titolo dell'asse ("week") lo porta solo l'ultima riga aperta; le
        # etichette delle settimane stanno sotto ogni pannello comunque.
        open_rows = [name for name, section in sections.items() if section.open]
        row_periods = {}
        for name in open_rows:
            value, unit, extra = CHART_ROWS[name]
            panels = _pair(
                spec,
                plotted,
                in_range,
                value,
                all_periods,
                unit,
                name,
                picked,
                hover,
                sport_colors,
                with_total=plot_total,
                show_x_title=name == open_rows[-1],
                **extra,
            )
            # La `key` porta il periodo come la tabella: cambiando intervallo il
            # grafico si rimonta, e con lui la selezione, che altrimenti
            # punterebbe a una settimana di un altro periodo.
            row_periods[name] = _clicked_period(
                sections[name].vega_lite_chart(
                    _row_spec(panels),
                    width="stretch",
                    on_select="rerun",
                    key=spec.key("charts", value, range_key),
                )
            )

        # Una selezione per riga aperta: quella buona e' la sola cambiata in questo
        # giro, perche' le altre sono rimaste accese dov'erano. Una riga tornata a
        # vuoto e' un doppio click, e conta come cambiamento: azzera la scelta. Si
        # ricordano solo le righe disegnate: una riga chiusa perde la sua
        # selezione, e riaprendola riparte da vuota senza sembrare un click.
        previous = st.session_state.get(prev_rows_key, {})
        changed = [
            period for name, period in row_periods.items() if period != previous.get(name)
        ]
        st.session_state[prev_rows_key] = row_periods

        just_clicked = [period for period in changed if period]
        if just_clicked:
            chart_period = pd.Timestamp(just_clicked[0])
        elif not changed:
            # Nessuna riga toccata: resta valida la settimana scelta prima.
            chart_period = st.session_state.get(prev_chart_key)

    # Tabella e grafici sono due modi di scegliere la stessa cosa: vince quello
    # toccato per ultimo, altrimenti un click sul grafico resterebbe prigioniero
    # di una riga selezionata prima (e viceversa).
    #
    # La riga della tabella si legge dallo stato di sessione e non dal widget:
    # Streamlit ci scrive la selezione dell'utente prima di far partire lo script,
    # quindi la sappiamo gia' qui, prima ancora di creare la tabella.
    table_rows = st.session_state.get(table_key, {}).get("selection", {}).get("rows", [])
    table_period = period_totals.index[table_rows[0]] if table_rows else None

    chart_changed = chart_period != st.session_state.get(prev_chart_key)
    table_changed = table_period != st.session_state.get(prev_table_key)
    if chart_changed and chart_period is not None:
        source = "chart"
    elif table_changed and table_period is not None:
        source = "table"
    elif chart_changed:
        # Doppio click su un grafico: la selezione li' e' stata azzerata, quindi
        # torna a comandare la riga della tabella, che e' rimasta evidenziata.
        source = "table"
    else:
        source = st.session_state.get(source_key, "table")
    st.session_state[prev_chart_key] = chart_period
    st.session_state[prev_table_key] = table_period
    st.session_state[source_key] = source

    picked_period = chart_period if source == "chart" else table_period
    # Un click su una settimana vuota (barra a zero) non ha nulla da mostrare.
    if picked_period not in period_totals.index:
        picked_period = None

    # Rete di sicurezza: se resta tutto deselezionato (o si clicca il punto di una
    # settimana vuota) mostriamo comunque l'ultima settimana invece di una pagina
    # a meta'. `period_totals` e' ordinata dalla piu' recente, quindi e' la riga 0.
    showing_latest = picked_period is None
    if showing_latest:
        picked_period = period_totals.index.max()

    # La riga da spuntare, decisa prima che la tabella esista.
    st.session_state[table_key] = {
        "selection": {"rows": [int(period_totals.index.get_loc(picked_period))], "columns": []}
    }

    with table_area:
        st.subheader(f"{spec.adjective} totals")
        st.caption(
            f"Click a row to see the {spec.unit} below. Click a header to sort."
        )

        st.dataframe(
            summary[TABLE_COLUMNS],
            column_config=_column_config(spec),
            hide_index=True,
            # Larga quanto le sue colonne, non quanto la finestra, e alta quanto
            # serve fino a dieci righe: oltre, scorre al suo interno.
            width="content",
            height="auto",
            # Lo stesso trattino delle schede per sport al posto di una cella
            # vuota, non uno zero.
            placeholder="-",
            on_select="rerun",
            selection_mode="single-row",
            key=table_key,
        )

    period_activities = activities[activities["period_start"] == picked_period]
    picked_label = spec.label(picked_period)

    with cards_area:
        st.subheader(f"By sport — {picked_label}")
        # Una riga sempre presente, non solo quando si sta guardando l'ultima
        # settimana: se comparisse e sparisse, la pagina sotto si sposterebbe di
        # una riga a ogni click.
        st.caption(
            f"Latest {spec.unit} — select a {spec.unit} in the table, or click a point "
            "in a chart."
            if showing_latest
            else f"Selected {spec.unit} — the totals below cover it sport by sport."
        )

        # Una scheda per sport, con lo stesso impianto della singola attivita'
        # nella pagina Activities (icona, titolo, metriche): qui pero' i numeri
        # sono i totali di tutte le attivita' di quello sport nella settimana.
        # Affiancate a due per riga: impilate a tutta larghezza erano quasi una
        # schermata, e a tre per riga una scheda era troppo stretta per i valori
        # grandi delle metriche, che Streamlit tagliava con i puntini ("24.5 km",
        # "50.4 km" gia' a 1440px). A due ci stanno anche i piu' larghi dello
        # storico ("181.2 km", "50:48", "+3383 m"), misurati nel browser a 1920,
        # 1440 e 1280.
        by_sport = _totals(period_activities, "sport").sort_values("time", ascending=False)

        CARDS_PER_ROW = 2
        sports = list(by_sport.index)
        for row_start in range(0, len(sports), CARDS_PER_ROW):
            row_sports = sports[row_start : row_start + CARDS_PER_ROW]
            # Sempre due colonne anche con una scheda sola: cosi' una settimana di
            # un solo sport non si ritrova una scheda larga quanto la pagina.
            for column, sport in zip(st.columns(CARDS_PER_ROW), row_sports):
                totals = by_sport.loc[sport]
                with column.container(border=True):
                    head = st.container(horizontal=True, vertical_alignment="center")
                    icon_path = sport_icon_path(sport)
                    if icon_path:
                        head.image(icon_path, width=40)
                    # Il conteggio sta nel titolo e non fra le metriche, come la
                    # data nella scheda della singola attivita': cosi' le metriche
                    # sono sei come la', tre e tre, invece di sette in una griglia
                    # zoppa.
                    count = int(totals["n"])
                    head.markdown(
                        f"**{sport_label(sport)}** — {count} "
                        f"{'activity' if count == 1 else 'activities'}"
                    )

                    # Le stesse sei metriche della scheda di dettaglio, nello
                    # stesso ordine: qui sono pero' i totali della settimana per
                    # questo sport.
                    distance_col, time_col, ascent_col = st.columns(3)
                    distance_col.metric("Distance", f"{totals['distance']:.1f} km")
                    time_col.metric("Duration", _hm(totals["time"]))
                    ascent_col.metric(
                        "Elevation", f"+{totals['d+']:.0f} m" if pd.notna(totals["d+"]) else "-"
                    )

                    speed_col, hr_col, vo2_col = st.columns(3)
                    speed_col.metric(
                        "Avg speed",
                        f"{totals['speed']:.1f} km/h" if pd.notna(totals["speed"]) else "-",
                        help="Total distance over total moving time (the duration above is "
                        "elapsed time, stops included).",
                    )
                    hr_col.metric(
                        "Avg HR", f"{totals['hr']:.0f} bpm" if pd.notna(totals["hr"]) else "-"
                    )
                    vo2_col.metric(
                        "VO2Max",
                        f"{totals['vo2max']:.1f}" if pd.notna(totals["vo2max"]) else "-",
                        help=f"The watch's VO2max after the last activity of the {spec.unit} "
                        "for this "
                        "sport, in ml/kg/min — not an average. Runs update it; other activities "
                        "carry the last value. Empty when the watch stored none.",
                    )

    # Le stesse attivita' che compongono i totali qui sopra, elencate una per una
    # come nella pagina Activities: stessa tabella, stessa scheda di dettaglio
    # quando si clicca una riga. Insieme alla scheda e' il blocco piu' alto della
    # pagina, e stando sopra i grafici li allontana: e' il prezzo di avere di
    # seguito, in cima, tutto cio' che riguarda la settimana scelta.
    # "Activities" e' il conteggio (colonna di tabella e metrica di scheda): per
    # l'elenco vero e proprio serve un nome che non sia lo stesso.
    with list_area:
        st.subheader(f"Activity list — {picked_label}")
        st.caption("Click a row to see the details.")
        period_activities = period_activities.sort_values("start_time", ascending=False)
        # Nessun `key`: cosi' l'identita' della tabella dipende dai dati e
        # cambiando settimana la selezione riparte da zero invece di puntare a
        # un'altra riga.
        activity_event = activity_table(
            period_activities,
            on_select="rerun",
            selection_mode="single-row",
            # Alta quanto le righe che ha, fino a dieci: l'altezza fissa lasciava
            # mezza griglia vuota nelle settimane con una o due uscite.
            height="auto",
        )

        activity_rows = list(activity_event.selection.rows)
        if activity_rows:
            show_activity_detail(period_activities.iloc[activity_rows[0]])
