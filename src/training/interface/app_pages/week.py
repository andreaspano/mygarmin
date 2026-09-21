"""Week page: weekly training totals, with a per-sport breakdown of the
week(s) selected in the table."""

import warnings

import altair as alt
import pandas as pd
import streamlit as st

from training.garmin.config import DATA_DIR
from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import activity_table, sport_icon_path, sport_label
from training.interface.data import load_activities
from training.interface.filters import date_range


# Configurazione della tabella dei totali settimanali. Segue le convenzioni
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
WEEK_TABLE_COLUMNS = ["week_start", "n", "distance", "time", "d+", "hr"]

WEEK_COLUMN_CONFIG = {
    "week_start": st.column_config.DatetimeColumn(
        "Week",
        format="D MMM YYYY",
        width=130,
        help="Monday that opens the week (Mon-Sun).",
    ),
    "n": st.column_config.NumberColumn(
        "Activities",
        format="%d",
        width=95,
        alignment="right",
        help="Number of activities in the week.",
    ),
    "distance": st.column_config.NumberColumn(
        "Distance (km)", format="%.1f", width=120, alignment="right"
    ),
    "time": st.column_config.TextColumn(
        "Duration (h:mm)",
        width=130,
        alignment="right",
        help="Total duration of the week, hours:minutes.",
    ),
    "d+": st.column_config.NumberColumn(
        "Elevation gain (m)",
        format="%.0f",
        width=150,
        alignment="right",
        help="Total elevation gain of the week.",
    ),
    "hr": st.column_config.NumberColumn(
        "Avg HR (bpm)",
        format="%.0f",
        width=120,
        alignment="right",
        help="Average heart rate, weighted by activity duration. "
        "Empty when no activity of the week recorded it.",
    ),
}

st.title("Week")


def _week_label(week_start: pd.Timestamp) -> str:
    """L'intervallo della settimana, con il trattino medio degli intervalli:
    quello lungo separa le frasi nei sottotitoli, e i due ruoli non vanno
    confusi ora che compaiono nella stessa riga."""
    return f"{week_start:%d %b %Y} – {week_start + pd.Timedelta(days=6):%d %b %Y}"


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
    """Totali (n, distanza, tempo, dislivello, FC media) raggruppati per `key`.

    La FC media e' pesata sulla durata (una sgambata di 20' non puo' pesare
    come un'uscita di 5h) e considera solo le attivita' che hanno davvero un
    dato di FC: le altre non entrano ne' al numeratore ne' al denominatore."""
    grouped = df.groupby(key).agg(
        n=("activity_id", "count"),
        distance=("total_distance_km", "sum"),
        time_min=("total_time_min", "sum"),
        ascent=("total_ascent_m", "sum"),
        hr_weighted=("_hr_weighted", "sum"),
        hr_time=("_hr_time", "sum"),
    )
    return pd.DataFrame(
        {
            "n": grouped["n"],
            "distance": grouped["distance"],
            "time": grouped["time_min"] / 60,
            "d+": grouped["ascent"],
            # Gruppi senza nessuna attivita' con FC: cella vuota, non uno zero.
            "hr": (grouped["hr_weighted"] / grouped["hr_time"]).where(grouped["hr_time"] > 0),
        }
    )


def _weekly_sum(
    df: pd.DataFrame,
    value: str,
    weeks: pd.DatetimeIndex,
    scale: float = 1.0,
    with_total: bool = True,
) -> pd.DataFrame:
    """`value` sommato per settimana, una colonna per sport e, se richiesto,
    il totale degli sport selezionati.

    Le settimane senza attivita' non esistono nel pivot: reindicizzando su
    tutti i lunedi' del periodo restano a zero, cosi' le pause di allenamento
    si vedono invece di sparire con una linea che salta il buco."""
    by_week_sport = df.pivot_table(
        index="week_start", columns="sport", values=value, aggfunc="sum"
    )
    by_week_sport = by_week_sport.reindex(weeks).fillna(0) * scale
    # Con un solo sport il totale ricalcherebbe esattamente la sua linea.
    if with_total and by_week_sport.shape[1] > 1:
        by_week_sport[TOTAL_SERIES] = by_week_sport.sum(axis=1)
    return by_week_sport


# La larghezza in pixel non e' una pigrizia, e' l'unica strada: la griglia
# a due colonne e il crosshair condiviso si pagano cosi'.
#
# Il crosshair su tutti i pannelli li vuole tutti in una vista Vega sola (fra
# viste distinte i segnali non passano). Ma una vista sola disposta a griglia
# e' un `vconcat` di `hconcat`, e quella forma non sa adattarsi al
# contenitore: provato, `autosize: fit-x` la fa collassare a larghezza zero,
# e con `fit` o `pad` la larghezza resta quella scritta qui. Il frontend di
# Streamlit passa la larghezza misurata ai figli di un `vconcat`, ma non
# scende dentro gli `hconcat`. Nemmeno calcolarla si puo': `st.context` non
# espone la larghezza della finestra.
#
# Tarata per stare in una finestra da 1440 con la sidebar aperta: li' il
# contenitore del grafico e' largo 980px. Attenzione, si misura sul
# contenitore del grafico, non sull'area principale della pagina, che a 1440
# e' 1.140: la differenza sono i margini, e sbagliare misura vuol dire
# scoprire lo sbordamento dopo.
#
# La barra di scorrimento non compare fino a 1440 con la sidebar aperta, e mai
# con la sidebar chiusa. Sotto, torna a sforare: basta chiudere la sidebar,
# oppure abbassare questo numero.
CHARTS_TOTAL_WIDTH = 940
_AXIS_WIDTH = 55  # l'asse y di ogni pannello, fuori dall'area di disegno
_VEGA_PADDING = 80  # i margini interni della vista, misurati nel browser

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


def _chart(
    by_week_sport: pd.DataFrame,
    y_label: str,
    title: str,
    picked: alt.Parameter,
    hover: alt.Parameter,
    colors: dict[str, str],
    show_x_axis: bool = True,
    integer: bool = False,
) -> alt.LayerChart:
    """Costruisce (senza disegnarlo) un pannello: l'area del totale, le linee
    per sport, il crosshair e i punti che raccolgono il click.

    `picked` e `hover` arrivano da fuori e sono lo stesso oggetto per tutti i
    pannelli, e qui il segnale **e'** condiviso: stanno tutti in una vista Vega
    sola, quindi la verticale tratteggiata si muove su tutti insieme, alla
    stessa settimana.

    `show_x_axis` lo accende solo sull'ultima riga della griglia: le righe
    hanno tutte lo stesso asse dei tempi, e ripeterlo non dice niente di nuovo
    mentre allunga il blocco.

    `integer` e' per le grandezze che si contano invece di misurarsi (il
    numero di attivita'): l'asse non scende sotto il passo di uno, che con
    poche attivita' darebbe tacche a 0,5, e il tooltip non mostra decimali.

    La selezione viaggia su `week_key` (stringa) e non sulla data: cosi'
    torna indietro da Vega tale e quale, senza passare da epoch/millisecondi.

    Il titolo sta dentro il grafico e allineato a sinistra, come nella pagina
    Activities."""
    long = (
        by_week_sport.rename_axis("week_start")
        .reset_index()
        .melt(id_vars="week_start", var_name="series", value_name="value")
    )
    # Da qui in poi `series` e' l'etichetta, non la chiave: e' quello che
    # finisce in legenda e nel tooltip. `TOTAL_SERIES` attraversa la mappatura
    # immutato, quindi i confronti qui sotto continuano a valere.
    long["series"] = long["series"].map(_series_label)
    long["week_key"] = long["week_start"].dt.strftime("%Y-%m-%d")
    # Numero di settimana ISO, calcolato qui e non nel grafico: serve al
    # tooltip, ed e' anche il riscontro di quello che l'asse deve mostrare.
    long["week_no"] = "w" + long["week_start"].dt.isocalendar().week.astype(int).map(
        "{:02d}".format
    )

    # L'asse resta temporale (e' quello che tiene le distanze giuste fra le
    # settimane, comprese le pause), ma i tick cadono su ogni lunedi' invece
    # che sui confini di mese: cosi' ogni etichetta corrisponde davvero a un
    # punto della serie. L'etichetta e' il numero di settimana ISO, w01..w53,
    # e Vega nasconde da se' quelle che si sovrapporrebbero.
    x = alt.X(
        "week_start:T",
        title="week" if show_x_axis else None,
        axis=alt.Axis(format="w%V", tickCount={"interval": "week", "step": 1})
        if show_x_axis
        else None,
    )
    y = alt.Y(
        "value:Q",
        title=y_label,
        axis=alt.Axis(tickMinStep=1) if integer else alt.Undefined,
    )
    # Legenda spenta: la legenda e' la riga di pills sopra i grafici, che porta
    # gli stessi colori e in piu' si clicca. Due elenchi delle stesse voci, uno
    # sopra l'altro, erano il problema da togliere.
    series_names = [str(c) for c in by_week_sport.columns]
    color = alt.Color(
        "series:N",
        title=None,
        scale=_color_scale(series_names, colors),
        legend=None,
    )

    layers = []

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

    # Punti trasparenti: non si vedono (restano solo le linee) ma sono loro a
    # raccogliere il click sulla settimana e a guidare il crosshair, percio'
    # si tengono larghi per avere un bersaglio comodo.
    layers.append(
        alt.Chart(long)
        .mark_point(size=55, filled=True, opacity=0)
        .encode(
            x=x,
            y=y,
            color=color,
            tooltip=[
                alt.Tooltip("week_no:N", title="Week"),
                alt.Tooltip("week_start:T", title="Starting", format="%d %b %Y"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=y_label, format=".0f" if integer else ".1f"),
            ],
        )
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


def _charts_spec(rows: list[list[alt.LayerChart]]) -> dict:
    """Le righe da due pannelli in **una sola** vista Vega.

    Una vista sola e' quello che fa muovere il crosshair su tutti i pannelli
    insieme: fra viste Vega distinte i segnali non passano, provato
    nel todo 03, che per questo aveva dovuto rinunciarci.

    Il prezzo e' la larghezza fissa, spiegato su `CHARTS_TOTAL_WIDTH`: a
    griglia Vega non si adatta al contenitore, e l'autosize non ci salva.
    Qui non lo tocchiamo: Streamlit ci mette `pad` da solo (per lui un
    `vconcat` di `hconcat` e' una composizione annidata), che e' esattamente
    "nessun adattamento", cioe' quello che vogliamo avendo gia' deciso noi i
    pixel.

    `resolve_scale(color="shared")` tiene lo stesso colore per lo stesso sport
    in tutti i pannelli e riduce le legende a una sola."""
    # Passare lo stesso `picked`/`hover` a tutti i pannelli e' il punto di
    # tutto: e' cosi' che il segnale e' uno solo. Dentro una specifica sola
    # pero' Altair vede il parametro ripetuto, lo deduplica (che e' quello che
    # vogliamo) e avvisa a ogni rerun.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")
        return (
            alt.vconcat(*[alt.hconcat(*row) for row in rows])
            .resolve_scale(color="shared")
            .to_dict()
        )


def _weekly_total(
    df: pd.DataFrame, value: str, weeks: pd.DatetimeIndex, scale: float = 1.0
) -> pd.Series:
    """`value` sommato per settimana su tutti gli sport insieme."""
    return df.groupby("week_start")[value].sum().reindex(weeks).fillna(0) * scale


def _pair(
    plotted: pd.DataFrame,
    everything: pd.DataFrame,
    value: str,
    weeks: pd.DatetimeIndex,
    y_label: str,
    title: str,
    picked: alt.Parameter,
    hover: alt.Parameter,
    colors: dict[str, str],
    scale: float = 1.0,
    with_total: bool = True,
    show_x_axis: bool = False,
    integer: bool = False,
) -> list[alt.LayerChart]:
    """La stessa grandezza due volte: prima settimana per settimana, poi il
    cumulato dall'inizio del periodo (quanto si e' messo insieme finora).

    Restituisce i due pannelli in una lista, uno sotto l'altro: a comporli ci
    pensa `_charts_spec()`, che li mette tutti in una vista sola.

    `show_x_axis` vale per tutti e due, perche' i due stanno sulla stessa
    riga della griglia: l'asse dei tempi lo disegna solo l'ultima riga.

    Nel cumulato il totale e' quello di *tutti* gli sport, non solo di quelli
    selezionati: le caselle scelgono quali linee guardare, ma il monte
    complessivo di km/ore/dislivello resta quello vero."""
    cumulative = _weekly_sum(plotted, value, weeks, scale, with_total=False).cumsum()
    # Con un solo sport selezionato il totale sparisce da tutti e due i
    # grafici: si sta guardando quello sport, non il quadro d'insieme.
    if with_total and cumulative.shape[1] > 1:
        cumulative[TOTAL_SERIES] = _weekly_total(everything, value, weeks, scale).cumsum()

    return [
        _chart(
            _weekly_sum(plotted, value, weeks, scale, with_total=with_total),
            y_label,
            title,
            picked,
            hover,
            colors,
            show_x_axis=show_x_axis,
            integer=integer,
        ),
        _chart(
            cumulative,
            y_label,
            f"{title} (cumulative)",
            picked,
            hover,
            colors,
            show_x_axis=show_x_axis,
            integer=integer,
        ),
    ]


def _clicked_weeks(event) -> list:
    """Le settimane cliccate, lette dalla selezione condivisa dai pannelli.

    Una selezione sola perche' i pannelli sono una vista sola: e' sparita la
    trafila del todo 03, che con sei eventi indipendenti doveva capire quale
    dei sei fosse cambiato in questo giro."""
    selection = (event.selection or {}).get("picked", []) if event else []

    weeks = []
    for item in selection:
        value = item.get("week_key") if isinstance(item, dict) else item
        weeks.extend(value if isinstance(value, list) else [value])
    return [week for week in weeks if week]


activities = load_activities(DATA_DIR)

if activities.empty:
    st.info(f"No *_ACTIVITY.fit file found in {DATA_DIR.resolve()}.")
    st.stop()

# Ogni attivita' viene assegnata al lunedi' della sua settimana: e' la
# chiave con cui raggruppiamo (e anche l'etichetta mostrata all'utente).
activities = activities.copy()
activities["week_start"] = (
    activities["start_time"] - pd.to_timedelta(activities["start_time"].dt.weekday, unit="D")
).dt.normalize()
sport_colors = _sport_colors(sorted(activities["sport"].dropna().unique()))

activities["_hr_weighted"] = activities["avg_heart_rate"] * activities["total_time_min"]
activities["_hr_time"] = activities["total_time_min"].where(activities["avg_heart_rate"].notna())
# Un uno per attivita': i grafici sommano una colonna per settimana e sport, e
# sommando questa si ottiene il conteggio senza una strada a parte.
activities["_count"] = 1

weekly = _totals(activities, "week_start").sort_index(ascending=False)

# Lo stesso filtro a calendario della pagina Activities: stessa funzione,
# non una copia. Qui pero' con le scorciatoie di periodo, perche' una pagina
# settimanale si guarda quasi sempre sulle ultime settimane e non su tutto lo
# storico (che sono quasi novanta righe e altrettanti punti per grafico).
start_date, end_date = date_range(
    activities,
    None,
    "'From' is later than 'To': swap the two dates to see the weeks.",
    presets=True,
    key="week_dates",
)

# Una settimana entra se si sovrappone all'intervallo, non solo se ci cade
# dentro il lunedi': scegliendo un mercoledi' ci si aspetta di vedere anche
# la settimana che lo contiene.
week_end = weekly.index + pd.Timedelta(days=6)
weekly = weekly[(weekly.index.date <= end_date) & (week_end.date >= start_date)]

if weekly.empty:
    st.info("No activity in the selected period.")
    st.stop()

summary = weekly.reset_index()
# Il tempo diventa testo "hh:mm" solo per la tabella: `weekly` resta numerico,
# perche' alimenta anche i grafici e le schede per sport.
summary["time"] = summary["time"].map(_hm)

# La selezione e' per indice di riga: cambiando periodo cambiano le righe,
# quindi la tabella va rimontata (key diversa) per non ereditare una
# selezione che ora punterebbe a settimane diverse.
period_key = f"{start_date}_{end_date}"
table_key = f"weekly_{period_key}"

# Anche la memoria di cosa era selezionato porta il periodo. I widget si
# azzerano da soli cambiando intervallo (la key cambia), ma queste chiavi no:
# senza il suffisso, il primo giro dopo il cambio confrontava la selezione
# nuova con settimane del periodo precedente.
prev_chart_key = f"_prev_chart_week_{period_key}"
prev_table_key = f"_prev_table_week_{period_key}"
source_key = f"_week_source_{period_key}"

# La tabella si legge per prima ma va creata per ultima. Lo stato di un widget
# si puo' impostare solo prima di crearlo: disegnando i grafici per primi, al
# momento di creare la tabella sappiamo gia' su quale settimana e' caduto il
# click, e possiamo spuntare la riga giusta subito. E' il motivo per cui qui
# non serve piu' rilanciare lo script: un click su un grafico costa un giro
# invece di due. Prenotiamo il posto, riempiamo piu' sotto.
table_area = st.container()

st.subheader("Weekly volume by sport")
in_range = activities[activities["week_start"].isin(weekly.index)]

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
sports_off = set(st.session_state.get("_week_sports_off", ()))
sport_key = f"plot_sports_{period_key}"
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
st.session_state["_week_sports_off"] = sorted(
    (sports_off - set(sport_options)) | (set(sport_options) - set(plotted_sports))
)

# Il totale sta nella stessa riga ma in un widget suo. E' una serie che esiste
# solo da due sport in su (con uno solo ricalcherebbe la sua linea, vedi
# `_weekly_sum`), e in quel caso la voce deve restare li', grigia e non
# cliccabile: `disabled` pero' vale per un widget intero, non per una voce
# sola. Da quinta pill del primo widget sarebbe stata solo grigia d'aspetto.
total_available = len(plotted_sports) > 1
# Chiave nuova rispetto al toggle di prima: li' lo stato era un booleano, qui
# e' una lista, e una sessione rimasta aperta li avrebbe confusi.
total_key = f"plot_total_pill_{period_key}"
if total_key not in st.session_state:
    # Spento resta spento anche cambiando intervallo, come per gli sport.
    st.session_state[total_key] = (
        [] if st.session_state.get("_week_total_off", False) else [TOTAL_SERIES]
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
    st.session_state["_week_total_off"] = TOTAL_SERIES not in total_picked
plot_total = total_available and TOTAL_SERIES in total_picked

chart_week = None
if not plotted_sports:
    st.info("Select at least one sport to plot.")
else:
    plotted = in_range[in_range["sport"].isin(plotted_sports)]
    all_weeks = pd.date_range(weekly.index.min(), weekly.index.max(), freq="W-MON")

    # Un solo oggetto per il click e uno per il crosshair, passati a tutti i
    # pannelli. Stando tutti in una vista Vega sola (`_charts_spec()`),
    # il segnale e' davvero uno: la verticale si muove su tutti insieme, e il
    # click torna come una selezione sola. Il nome esplicito e' la chiave con
    # cui la selezione si rilegge dall'evento.
    picked = alt.selection_point(
        name="picked", fields=["week_key"], on="click", clear="dblclick", toggle=False
    )
    # Nome esplicito come per `picked`: e' la chiave con cui il parametro
    # compare nell'evento di selezione, e un nome stabile vale piu' del
    # `param_N` che Altair genererebbe da se'.
    hover = alt.selection_point(
        name="hovered",
        fields=["week_key"],
        nearest=True,
        on="pointermove",
        empty=False,
        clear="pointerout",
    )

    # Quattro righe da due pannelli, nell'ordine delle colonne della tabella
    # dei totali (Activities, Distance, Duration, Elevation gain): a sinistra
    # la grandezza settimana per settimana, a destra il suo cumulato. L'asse
    # dei tempi lo disegna solo l'ultima riga: le righe ce l'hanno uguale, e
    # ripeterlo allungava il blocco per niente.
    rows = [
        _pair(
            plotted,
            in_range,
            "_count",
            all_weeks,
            "count",
            "Activities",
            picked,
            hover,
            sport_colors,
            with_total=plot_total,
            integer=True,
        ),
        _pair(
            plotted,
            in_range,
            "total_distance_km",
            all_weeks,
            "km",
            "Distance",
            picked,
            hover,
            sport_colors,
            with_total=plot_total,
        ),
        _pair(
            plotted,
            in_range,
            "total_time_min",
            all_weeks,
            "h",
            "Duration",
            picked,
            hover,
            sport_colors,
            scale=1 / 60,
            with_total=plot_total,
        ),
        _pair(
            plotted,
            in_range,
            "total_ascent_m",
            all_weeks,
            "m",
            "Elevation gain",
            picked,
            hover,
            sport_colors,
            with_total=plot_total,
            show_x_axis=True,
        ),
    ]

    # Una `key` sola per una vista sola. Porta il periodo come la tabella:
    # cambiando intervallo il grafico si rimonta, e con lui la selezione, che
    # altrimenti punterebbe a una settimana di un altro periodo.
    clicked_weeks = _clicked_weeks(
        st.vega_lite_chart(
            _charts_spec(rows),
            width="stretch",
            on_select="rerun",
            key=f"charts_{period_key}",
        )
    )
    if clicked_weeks:
        chart_week = pd.Timestamp(clicked_weeks[0])

# Tabella e grafici sono due modi di scegliere la stessa cosa: vince quello
# toccato per ultimo, altrimenti un click sul grafico resterebbe prigioniero
# di una riga selezionata prima (e viceversa).
#
# La riga della tabella si legge dallo stato di sessione e non dal widget:
# Streamlit ci scrive la selezione dell'utente prima di far partire lo script,
# quindi la sappiamo gia' qui, prima ancora di creare la tabella.
table_rows = st.session_state.get(table_key, {}).get("selection", {}).get("rows", [])
table_week = weekly.index[table_rows[0]] if table_rows else None

chart_changed = chart_week != st.session_state.get(prev_chart_key)
table_changed = table_week != st.session_state.get(prev_table_key)
if chart_changed and chart_week is not None:
    source = "chart"
elif table_changed and table_week is not None:
    source = "table"
elif chart_changed:
    # Doppio click su un grafico: la selezione li' e' stata azzerata, quindi
    # torna a comandare la riga della tabella, che e' rimasta evidenziata.
    source = "table"
else:
    source = st.session_state.get(source_key, "table")
st.session_state[prev_chart_key] = chart_week
st.session_state[prev_table_key] = table_week
st.session_state[source_key] = source

picked_week = chart_week if source == "chart" else table_week
# Un click su una settimana vuota (barra a zero) non ha nulla da mostrare.
if picked_week not in weekly.index:
    picked_week = None

# Rete di sicurezza: se resta tutto deselezionato (o si clicca il punto di una
# settimana vuota) mostriamo comunque l'ultima settimana invece di una pagina
# a meta'. `weekly` e' ordinata dalla piu' recente, quindi e' la riga 0.
showing_latest = picked_week is None
if showing_latest:
    picked_week = weekly.index.max()

# La riga da spuntare, decisa prima che la tabella esista.
st.session_state[table_key] = {
    "selection": {"rows": [int(weekly.index.get_loc(picked_week))], "columns": []}
}

with table_area:
    st.subheader("Weekly totals")
    st.caption("Click a row to see the week below. Click a header to sort.")

    st.dataframe(
        summary[WEEK_TABLE_COLUMNS],
        column_config=WEEK_COLUMN_CONFIG,
        hide_index=True,
        # Larga quanto le sue colonne, non quanto la finestra, e alta quanto
        # serve fino a dieci righe: oltre, scorre al suo interno.
        width="content",
        height="auto",
        # Solo la FC puo' mancare (settimane senza nessun dato di FC): lo
        # stesso trattino delle schede per sport, non uno zero.
        placeholder="-",
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )

week_activities = activities[activities["week_start"] == picked_week]
picked_label = _week_label(picked_week)

st.subheader(f"By sport — {picked_label}")
# Una riga sempre presente, non solo quando si sta guardando l'ultima
# settimana: se comparisse e sparisse, la pagina sotto si sposterebbe di una
# riga a ogni click.
st.caption(
    "Latest week — select a week in the table, or click a point in a chart."
    if showing_latest
    else "Selected week — the totals below cover it sport by sport."
)

# Una scheda per sport, con lo stesso impianto della singola attivita' nella
# pagina Activities (icona, titolo, metriche): qui pero' i numeri sono i
# totali di tutte le attivita' di quello sport nella settimana. Affiancate
# fino a tre per riga: impilate a tutta larghezza erano quasi una schermata.
by_sport = _totals(week_activities, "sport").sort_values("time", ascending=False)

CARDS_PER_ROW = 3
sports = list(by_sport.index)
for row_start in range(0, len(sports), CARDS_PER_ROW):
    row_sports = sports[row_start : row_start + CARDS_PER_ROW]
    # Sempre tre colonne anche con una scheda sola: cosi' una settimana di un
    # solo sport non si ritrova una scheda larga quanto la pagina.
    for column, sport in zip(st.columns(CARDS_PER_ROW), row_sports):
        totals = by_sport.loc[sport]
        with column.container(border=True):
            head = st.container(horizontal=True, vertical_alignment="center")
            icon_path = sport_icon_path(sport)
            if icon_path:
                head.image(icon_path, width=40)
            head.markdown(f"**{sport_label(sport)}**")

            n_col, distance_col, time_col = st.columns(3)
            n_col.metric("Activities", f"{totals['n']:.0f}")
            distance_col.metric("Distance", f"{totals['distance']:.1f} km")
            time_col.metric("Duration", _hm(totals["time"]))
            ascent_col, hr_col = st.columns(2)
            ascent_col.metric(
                "Elevation gain", f"+{totals['d+']:.0f} m" if pd.notna(totals["d+"]) else "-"
            )
            hr_col.metric("Avg HR", f"{totals['hr']:.0f} bpm" if pd.notna(totals["hr"]) else "-")

# Le stesse attivita' che compongono i totali qui sopra, elencate una per una
# come nella pagina Activities: stessa tabella, stessa scheda di dettaglio
# quando si clicca una riga. Sta in fondo perche' la scheda di dettaglio e' il
# blocco piu' alto della pagina: in mezzo avrebbe allontanato tutto il resto.
# "Activities" e' il conteggio (colonna di tabella e metrica di scheda): per
# l'elenco vero e proprio serve un nome che non sia lo stesso.
st.subheader(f"Activity list — {picked_label}")
st.caption("Click a row to see the details.")
week_activities = week_activities.sort_values("start_time", ascending=False)
# Nessun `key`: cosi' l'identita' della tabella dipende dai dati e cambiando
# settimana la selezione riparte da zero invece di puntare a un'altra riga.
activity_event = activity_table(
    week_activities,
    on_select="rerun",
    selection_mode="single-row",
    # Alta quanto le righe che ha, fino a dieci: l'altezza fissa lasciava
    # mezza griglia vuota nelle settimane con una o due uscite.
    height="auto",
)

activity_rows = list(activity_event.selection.rows)
if activity_rows:
    show_activity_detail(week_activities.iloc[activity_rows[0]])
