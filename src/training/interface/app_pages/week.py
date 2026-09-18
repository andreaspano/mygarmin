"""Week page: weekly training totals, with a per-sport breakdown of the
week(s) selected in the table."""

import warnings
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from training.interface.activity_detail import show_activity_detail
from training.interface.activity_table import activity_table, sport_icon_path
from training.interface.db import list_activities
from training.interface.filters import date_range

DATA_DIR = Path("data")

# Configurazione condivisa dalle due tabelle: le colonne dei valori sono le
# stesse, cambia solo la prima (settimana / sport).
VALUE_COLUMNS = {
    "n": st.column_config.NumberColumn("n", format="%d", width=60),
    "distance": st.column_config.NumberColumn("Distance (km)", format="%.1f", width=130),
    "time": st.column_config.NumberColumn("Time (h)", format="%.1f", width=110),
    "d+": st.column_config.NumberColumn("D+ (m)", format="%.0f", width=110),
    "hr": st.column_config.NumberColumn("Avg HR", format="%.0f", width=100),
}

st.title("Week")


def _activities() -> pd.DataFrame:
    return list_activities(DATA_DIR)


def _week_label(week_start: pd.Timestamp) -> str:
    return f"{week_start:%d %b %Y} - {week_start + pd.Timedelta(days=6):%d %b %Y}"


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
        by_week_sport["Total"] = by_week_sport.sum(axis=1)
    return by_week_sport


# La tabella e' elastica, i grafici no: stando tutti in un'unica vista Vega
# (e' cosi' che il crosshair si muove su tutti insieme) la larghezza e' per
# forza in pixel, perche' dentro un hconcat Vega-Lite non sa adattarsi al
# contenitore. Qui e' tarata su una finestra da 1920 in layout "wide": per
# cambiarla basta CHARTS_TOTAL_WIDTH, cioe' la larghezza della finestra meno
# i margini della pagina (~160px).
CHARTS_TOTAL_WIDTH = 1760
_LEGEND_WIDTH = 140  # la legenda, una sola per tutti, sta a destra del blocco
_AXIS_WIDTH = 60  # l'asse y di ogni grafico, fuori dall'area di disegno

# `width` in Vega e' la sola area di disegno: assi e legenda si aggiungono.
CHART_WIDTH = (CHARTS_TOTAL_WIDTH - _LEGEND_WIDTH) // 2 - _AXIS_WIDTH
CHART_HEIGHT = 320

# L'area del totale ha un colore suo, arancione, invece di pescare dalla
# tavolozza categorica (dove finiva su un marrone smorto). Le linee dei sport
# usano la tavolozza di default meno l'arancione, per non confondersi con lei.
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


def _chart(
    by_week_sport: pd.DataFrame,
    y_label: str,
    title: str,
    picked: alt.Parameter,
    hover: alt.Parameter,
    colors: dict[str, str],
) -> alt.LayerChart:
    """Costruisce (senza disegnarlo) un grafico: l'area del totale, le linee
    per sport, il crosshair e i punti che raccolgono il click.

    `picked` e `hover` arrivano da fuori e sono gli stessi per tutti i
    grafici: stando poi in un'unica vista Vega il segnale e' condiviso, e la
    verticale tratteggiata si muove su tutti i grafici insieme.

    La selezione viaggia su `week_key` (stringa) e non sulla data: cosi'
    torna indietro da Vega tale e quale, senza passare da epoch/millisecondi.

    Il titolo sta dentro il grafico e allineato a sinistra, come nella pagina
    Activities."""
    long = (
        by_week_sport.rename_axis("week_start")
        .reset_index()
        .melt(id_vars="week_start", var_name="series", value_name="value")
    )
    long["week_key"] = long["week_start"].dt.strftime("%Y-%m-%d")

    x = alt.X("week_start:T", title="week")
    y = alt.Y("value:Q", title=y_label)
    # Dominio esplicito: ogni layer vede solo una parte delle serie, senza
    # fissare la scala il totale si prenderebbe il colore del primo sport.
    series_names = [str(c) for c in by_week_sport.columns]
    color = alt.Color(
        "series:N",
        title=None,
        scale=alt.Scale(
            domain=series_names,
            range=[TOTAL_COLOR if name == "Total" else colors[name] for name in series_names],
        ),
    )

    layers = []

    # Il totale e' solo un'area riempita sullo sfondo, senza bordo: fa da ombra
    # sotto ai singoli sport, che ci passano sopra leggibili.
    total = long[long["series"] == "Total"]
    if not total.empty:
        layers.append(
            alt.Chart(total).mark_area(fillOpacity=0.25).encode(x=x, y=y, color=color)
        )

    by_sport = long[long["series"] != "Total"]
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
                alt.Tooltip("week_start:T", title="Week", format="%d %b %Y"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=y_label, format=".1f"),
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
) -> alt.HConcatChart:
    """La stessa grandezza due volte, affiancate: a sinistra settimana per
    settimana, a destra il cumulato dall'inizio del periodo (quanto si e'
    messo insieme finora).

    Nel cumulato il totale e' quello di *tutti* gli sport, non solo di quelli
    selezionati: le caselle scelgono quali linee guardare, ma il monte
    complessivo di km/ore/dislivello resta quello vero."""
    cumulative = _weekly_sum(plotted, value, weeks, scale, with_total=False).cumsum()
    # Con un solo sport selezionato il totale sparisce da tutti e due i
    # grafici: si sta guardando quello sport, non il quadro d'insieme.
    if with_total and cumulative.shape[1] > 1:
        cumulative["Total"] = _weekly_total(everything, value, weeks, scale).cumsum()

    return alt.hconcat(
        _chart(
            _weekly_sum(plotted, value, weeks, scale, with_total=with_total),
            y_label,
            title,
            picked,
            hover,
            colors,
        ),
        _chart(cumulative, y_label, f"{title} (cumulative)", picked, hover, colors),
    )


def _clicked_weeks(event) -> list:
    """Le settimane cliccate, lette dalla selezione condivisa dai grafici."""
    selection = (event.selection or {}).get("picked", []) if event else []

    weeks = []
    for item in selection:
        value = item.get("week_key") if isinstance(item, dict) else item
        weeks.extend(value if isinstance(value, list) else [value])
    return [w for w in weeks if w]


activities = _activities()

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

weekly = _totals(activities, "week_start").sort_index(ascending=False)

# Lo stesso filtro a calendario della pagina Activities: stessa funzione,
# non una copia.
start_date, end_date = date_range(
    activities,
    st.container(horizontal=True),
    "'From' is later than 'To': swap the two dates to see the weeks.",
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
summary["week"] = [_week_label(w) for w in weekly.index]

# La selezione e' per indice di riga: cambiando periodo cambiano le righe,
# quindi la tabella va rimontata (key diversa) per non ereditare una
# selezione che ora punterebbe a settimane diverse.
period_key = f"{start_date}_{end_date}"
table_key = f"weekly_{period_key}"

# Riga da spuntare: quella chiesta da un click su un grafico (vedi in fondo),
# altrimenti - alla prima apertura e a ogni cambio di periodo - la settimana
# piu' recente, cioe' la riga 0, perche' `weekly` e' ordinata dalla piu' nuova
# alla piu' vecchia.
forced_row = st.session_state.pop("_force_week_row", None)
if forced_row is not None:
    st.session_state[table_key] = {"selection": {"rows": [forced_row], "columns": []}}
elif table_key not in st.session_state:
    st.session_state[table_key] = {"selection": {"rows": [0], "columns": []}}

event = st.dataframe(
    summary[["week", "n", "distance", "time", "d+", "hr"]],
    column_config={"week": st.column_config.TextColumn("Week", width=200), **VALUE_COLUMNS},
    hide_index=True,
    height=600,
    on_select="rerun",
    selection_mode="single-row",
    key=table_key,
)

# Le tabelle stanno sopra i grafici, ma quello che mostrano dipende anche da
# dove si clicca nei grafici: prenotiamo qui il loro spazio e lo riempiamo
# piu' sotto, quando la settimana scelta e' nota.
summary_area = st.container()
activities_area = st.container()

st.subheader("Weekly volume by sport")
in_range = activities[activities["week_start"].isin(weekly.index)]

# Il filtro vale solo per il grafico: le tabelle restano su tutti gli sport.
# Una casella per sport, tutte attive di default.
sport_options = sorted(in_range["sport"].dropna().unique())
sport_row = st.container(horizontal=True)
plotted_sports = [
    sport
    for sport in sport_options
    if sport_row.checkbox(sport.replace("_", " "), value=True, key=f"plot_sport_{sport}")
]
# Il totale degli sport selezionati e' una serie come le altre: si accende e
# si spegne dalla stessa fila di caselle.
plot_total = sport_row.checkbox("Total", value=True, key="plot_sport_total")

clicked_weeks = []
if not plotted_sports:
    st.info("Select at least one sport to plot.")
else:
    plotted = in_range[in_range["sport"].isin(plotted_sports)]
    all_weeks = pd.date_range(weekly.index.min(), weekly.index.max(), freq="W-MON")

    # Un solo oggetto per il click e uno per il crosshair, passati a tutti e
    # sei i grafici. I sei stanno in un'unica vista Vega (un vconcat di righe
    # affiancate) e non in sei `st.altair_chart` separati: e' quello che
    # permette al segnale di passare da un grafico all'altro, cosi' la
    # verticale si muove su tutti insieme. Il prezzo e' la larghezza fissa:
    # dentro un hconcat Vega non sa adattarsi al contenitore.
    picked = alt.selection_point(
        name="picked", fields=["week_key"], on="click", clear="dblclick", toggle=False
    )
    # Nome esplicito: senza, Altair deduplica il parametro ripetuto sui sei
    # grafici e avvisa a ogni rerun.
    hover = alt.selection_point(
        name="hovered",
        fields=["week_key"],
        nearest=True,
        on="pointermove",
        empty=False,
        clear="pointerout",
    )

    # Passare lo stesso parametro a piu' grafici e' voluto (e' cosi' che il
    # segnale viene condiviso): Altair lo deduplica e avvisa a ogni rerun.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")
        charts = alt.vconcat(
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
                "Time",
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
                "D+",
                picked,
                hover,
                sport_colors,
                with_total=plot_total,
            ),
            # Una sola legenda per tutti invece di sei uguali.
        ).resolve_scale(color="shared")

    clicked_weeks = _clicked_weeks(
        st.altair_chart(charts, on_select="rerun", key=f"charts_{period_key}")
    )

# Tabella e grafici sono due modi di scegliere la stessa cosa: vince quello
# toccato per ultimo, altrimenti un click sul grafico resterebbe prigioniero
# di una riga selezionata prima (e viceversa).
selected_rows = list(event.selection.rows)
table_week = weekly.index[selected_rows[0]] if selected_rows else None
chart_week = pd.Timestamp(clicked_weeks[0]) if clicked_weeks else None

if chart_week != st.session_state.get("_prev_chart_week") and chart_week is not None:
    source = "chart"
elif table_week != st.session_state.get("_prev_table_week") and table_week is not None:
    source = "table"
else:
    source = st.session_state.get("_week_source", "table")
st.session_state["_prev_chart_week"] = chart_week
st.session_state["_prev_table_week"] = table_week
st.session_state["_week_source"] = source

picked_week = chart_week if source == "chart" else table_week
# Un click su una settimana vuota (barra a zero) non ha nulla da mostrare.
if picked_week not in weekly.index:
    picked_week = None

# Cliccando un grafico si deve spuntare anche la riga corrispondente. La
# tabella e' gia' stata disegnata in questo giro (sta piu' in alto), e lo
# stato di un widget non si puo' toccare dopo averlo creato: si lascia detta
# la riga in una chiave a parte e si rilancia lo script, che la ritrova prima
# di ridisegnare la tabella.
if source == "chart" and picked_week is not None and picked_week != table_week:
    st.session_state["_force_week_row"] = int(weekly.index.get_loc(picked_week))
    st.rerun()

# Rete di sicurezza: se resta tutto deselezionato (o si clicca il punto di una
# settimana vuota) mostriamo comunque l'ultima settimana invece di una pagina
# a meta'.
showing_latest = picked_week is None
if showing_latest:
    picked_week = weekly.index.max()

picked = activities[activities["week_start"] == picked_week]
picked_label = _week_label(picked_week)

with summary_area:
    if showing_latest:
        st.caption("Latest week - select a week in the table, or click a point in a chart.")

    st.subheader(f"By sport - {picked_label}")

    # Una scheda per sport, con lo stesso impianto della singola attivita' nella
    # pagina Activities (icona, titolo, metriche): qui pero' i numeri sono i
    # totali di tutte le attivita' di quello sport nella settimana.
    by_sport = _totals(picked, "sport").sort_values("time", ascending=False)

    for sport, totals in by_sport.iterrows():
        with st.container(border=True):
            icon_col, body_col = st.columns([1, 9])

            icon_path = sport_icon_path(sport)
            if icon_path:
                icon_col.image(icon_path, width=56)

            body_col.markdown(f"**{(sport or '?').replace('_', ' ')}**")
            n_col, distance_col, time_col, ascent_col, hr_col = body_col.columns(5)
            n_col.metric("Activities", f"{totals['n']:.0f}")
            distance_col.metric("Distance", f"{totals['distance']:.1f} km")
            time_col.metric("Time", f"{totals['time']:.1f} h")
            ascent_col.metric(
                "Elevation", f"+{totals['d+']:.0f} m" if pd.notna(totals["d+"]) else "-"
            )
            hr_col.metric("Avg HR", f"{totals['hr']:.0f} bpm" if pd.notna(totals["hr"]) else "-")

with activities_area:
    # Le stesse attivita' che compongono i totali qui sopra, elencate una per una
    # come nella pagina Activities: stessa tabella, stessa scheda di dettaglio
    # quando si clicca una riga.
    st.subheader(f"Activities - {picked_label}")
    st.caption("Click a row to see the details.")
    week_activities = picked.sort_values("start_time", ascending=False)
    # Nessun `key`: cosi' l'identita' della tabella dipende dai dati e cambiando
    # settimana la selezione riparte da zero invece di puntare a un'altra riga.
    activity_event = activity_table(
        week_activities,
        on_select="rerun",
        selection_mode="single-row",
        # Altezza fissa: con settimane lunghe la tabella scorre al suo interno,
        # cosi' la scheda dell'attivita' resta a portata di occhio subito sotto.
        height=300,
    )

    activity_rows = list(activity_event.selection.rows)
    if activity_rows:
        show_activity_detail(week_activities.iloc[activity_rows[0]])
