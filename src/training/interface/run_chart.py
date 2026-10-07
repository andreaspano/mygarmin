"""Il grafico a tre fasce della scheda di dettaglio (todo 28): battiti in
alto, velocita' reale ed equivalente in mezzo, pendenza in basso, con le
zone cardiache come bande verticali dietro a tutto.

I calcoli (bande, effetti, intervalli) sono separati dal disegno: le prime
funzioni lavorano sui record dell'attivita' (`db.load_activity_records`) e
non sanno niente di Altair. Il tempo in ascissa e' quello trascorso dalla
partenza, in minuti, pause comprese.

I parametri vengono da un grafico messo a punto fuori dal progetto sulla
corsa del 03/10/2026, e i valori attesi su quella corsa sono nel todo 28."""

import math
import warnings

import altair as alt
import numpy as np
import pandas as pd

from training.interface.grade import MODEL_SLOPE_LIMIT_PCT, rolling_mean, segments, slope_pct

BIN_S = 30
# Un intervallo con meno di 10 s di dati si scarta: 10 campioni a un record al
# secondo, ma contati in secondi, cosi' vale anche per i file piu' radi.
_MIN_SECONDS_PER_BIN = 10
_SPEED_SMOOTH = "30s"
_SLOPE_BAR_SMOOTH = "20s"
_HR_ZONE_SMOOTH = "45s"
_ZONE_MIN_BAND_S = 60
# Sotto queste frazioni della durata un'etichetta non ci sta e finirebbe
# sopra quella accanto: la zona, la media dei battiti, la scritta "pause".
_ZONE_LABEL_MIN_SHARE = 0.025
_AVG_LABEL_MIN_SHARE = 0.06
_PAUSE_LABEL_MIN_SHARE = 0.03

EFFECTS = ("Low aerobic", "High aerobic", "Anaerobic")

# Tema chiaro e scuro: gli stessi colori del grafico di riferimento. Le zone
# hanno un solo colore a intensita' crescente perche' verde e rosso sono gia'
# della pendenza; la velocita' reale e' nel colore del testo, perche' sul
# viola il blu si staccava poco.
_PALETTES = {
    "light": {
        "speed": "#0b0b0b",
        "equiv": "#eb6834",
        "up": "#008300",
        "down": "#e34948",
        "zone": "rgb(74,58,167)",
        "zone_half": "rgba(74,58,167,0.5)",
        "anaerobic": "#e87ba4",
        "zone_opacity": [0.03, 0.10, 0.22, 0.40, 0.56],
        "muted": "#6b7280",
    },
    "dark": {
        "speed": "#f0efec",
        "equiv": "#d95926",
        "up": "#199e70",
        "down": "#e66767",
        "zone": "rgb(144,133,233)",
        "zone_half": "rgba(144,133,233,0.5)",
        "anaerobic": "#d55181",
        "zone_opacity": [0.04, 0.13, 0.26, 0.44, 0.60],
        "muted": "#9ca3af",
    },
}


def _elapsed_s(records: pd.DataFrame) -> np.ndarray:
    return (records.index - records.index[0]).total_seconds().to_numpy()


def durations_s(records: pd.DataFrame) -> pd.Series:
    """Quanti secondi vale ogni record: fino al record dopo, e uno solo
    attraverso una pausa e per l'ultimo. Con un record al secondo e' un
    conteggio; i file vecchi ne hanno di piu' radi."""
    gap = pd.Series(records.index, index=records.index).diff().shift(-1).dt.total_seconds()
    return gap.where(segments(records.index).diff().shift(-1).fillna(0) == 0, 1).fillna(1)


def pauses(records: pd.DataFrame) -> list[tuple[float, float]]:
    """Le pause, come (minuto di inizio, minuto di fine): dall'ultimo record
    di un tratto (piu' un secondo) al primo del tratto dopo."""
    if records.empty:
        return []
    t = _elapsed_s(records)
    seg = segments(records.index).to_numpy()
    starts = np.flatnonzero(np.diff(seg)) + 1
    return [((t[i - 1] + 1) / 60, t[i] / 60) for i in starts]


def zone_of(hr: float, bounds: list[int]) -> int:
    """La zona (1-5) dei battiti: 1 piu' i tetti superati."""
    return 1 + sum(hr > top for top in bounds)


def zone_bands(records: pd.DataFrame, bounds: list[int]) -> pd.DataFrame:
    """Le bande delle zone: inizio e fine in minuti, zona, media dei battiti.

    I battiti si lisciano a 45 s dentro ogni tratto e si raggruppano i
    secondi consecutivi nella stessa zona; ogni tratto sotto i 60 s si
    accorpa al vicino piu' lungo, poi si uniscono i vicini uguali, finche'
    non restano tratti corti. Senza lisciatura e accorpamento i battiti che
    oscillano intorno a una soglia fanno tante strisce sottili. La media e'
    sui battiti grezzi."""
    columns = ["start", "end", "zone", "hr"]
    hr_all = records["heart_rate"].astype(float)
    if hr_all.isna().all():
        return pd.DataFrame(columns=columns)
    smooth_all = rolling_mean(hr_all, _HR_ZONE_SMOOTH)
    t_all = _elapsed_s(records)
    seg_all = segments(records.index).to_numpy()

    bands = []
    for seg_id in np.unique(seg_all):
        mask = (seg_all == seg_id) & smooth_all.notna().to_numpy()
        if not mask.any():
            continue
        t = t_all[mask]
        hr = hr_all.to_numpy()[mask]
        zone = np.array([zone_of(h, bounds) for h in smooth_all.to_numpy()[mask]])

        runs, start = [], 0
        for i in range(1, len(t) + 1):
            if i == len(t) or zone[i] != zone[start]:
                runs.append([start, i - 1, int(zone[start])])
                start = i

        def length(run):
            return t[run[1]] - t[run[0]]

        changed = True
        while changed and len(runs) > 1:
            changed = False
            for i, run in enumerate(runs):
                if length(run) < _ZONE_MIN_BAND_S:
                    if i == 0:
                        j = 1
                    elif i == len(runs) - 1:
                        j = i - 1
                    else:
                        j = i - 1 if length(runs[i - 1]) >= length(runs[i + 1]) else i + 1
                    a, b = min(i, j), max(i, j)
                    runs[a] = [runs[a][0], runs[b][1], runs[j][2]]
                    del runs[b]
                    changed = True
                    break
            k = 0
            while k < len(runs) - 1:
                if runs[k][2] == runs[k + 1][2]:
                    runs[k] = [runs[k][0], runs[k + 1][1], runs[k][2]]
                    del runs[k + 1]
                else:
                    k += 1

        for a, b, z in runs:
            bands.append([t[a] / 60, (t[b] + 1) / 60, z, float(np.nanmean(hr[a : b + 1]))])
    return pd.DataFrame(bands, columns=columns)


def has_effects(bounds: list[int] | None, threshold_hr: int | None) -> bool:
    """Se le soglie bastano per gli effetti: servono i tetti delle zone e una
    soglia anaerobica sopra il tetto di Z3. Alcune attivita' (la palestra)
    salvano la soglia a zero."""
    return bool(bounds) and threshold_hr is not None and threshold_hr > bounds[2]


def effect_of(hr: float, bounds: list[int], threshold_hr: int) -> str:
    """L'effetto stimato dai battiti: basso aerobico fino al tetto di Z3, alto
    aerobico fino alla soglia anaerobica, anaerobico sopra."""
    if hr <= bounds[2]:
        return EFFECTS[0]
    if hr <= threshold_hr:
        return EFFECTS[1]
    return EFFECTS[2]


def effects(records: pd.DataFrame, bounds: list[int], threshold_hr: int) -> dict[str, float]:
    """I secondi passati in ciascun effetto, sui battiti grezzi.

    E' una stima: Garmin calcola il Training Effect con un algoritmo suo, e
    nel file salva solo i totali della sessione."""
    hr = records["heart_rate"].astype(float)
    seconds = durations_s(records)
    result = dict.fromkeys(EFFECTS, 0.0)
    for value, duration in zip(hr, seconds):
        if pd.notna(value):
            result[effect_of(value, bounds, threshold_hr)] += duration
    return result


def bins(records: pd.DataFrame) -> pd.DataFrame:
    """Una riga per intervallo di 30 s con almeno 10 s di dati: minuto di
    inizio, di centro e di fine, velocita' (lisciata a 30 s), velocita'
    equivalente, pendenza (lisciata a 20 s, in % e in
    gradi) e battiti medi.

    La velocita' equivalente nel database e' grezza (`grade.equivalent_speed_series`):
    la media dell'intervallo e' gia' la sua lisciatura a 30 s, e una media
    mobile in piu' prima la spostava dai valori del grafico di riferimento.

    Le colonne senza dato restano vuote: una bici non ha velocita'
    equivalente, una palestra non ha ne' velocita' ne' pendenza."""
    t = _elapsed_s(records)
    frame = pd.DataFrame(index=records.index)
    frame["bin"] = (t // BIN_S).astype(int)
    frame["seconds"] = durations_s(records).to_numpy()
    frame["hr"] = records["heart_rate"].astype(float)
    frame["speed"] = rolling_mean(records["speed_kmh"], _SPEED_SMOOTH)
    frame["equiv"] = records["equiv_speed_kmh"].astype(float)
    frame["slope_pct"] = rolling_mean(slope_pct(records), _SLOPE_BAR_SMOOTH)

    grouped = frame.groupby("bin")
    out = grouped[["hr", "speed", "equiv", "slope_pct"]].mean()
    out = out[grouped["seconds"].sum() >= _MIN_SECONDS_PER_BIN]
    # Le barre si fermano dove si ferma il modello di costo (±45%, circa 24
    # gradi): oltre e' quasi sempre un salto dell'altimetro da fermi, e una
    # barra sola schiaccerebbe tutte le altre.
    out["slope_pct"] = out["slope_pct"].clip(-MODEL_SLOPE_LIMIT_PCT, MODEL_SLOPE_LIMIT_PCT)
    out["slope_deg"] = np.degrees(np.arctan(out["slope_pct"] / 100))
    out["start"] = out.index * BIN_S / 60
    out["end"] = (out.index + 1) * BIN_S / 60
    out["minute"] = (out["start"] + out["end"]) / 2
    return out.reset_index()


def _clock(minutes: float) -> str:
    seconds = round(minutes * 60)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _ceil(value: float, step: float = 1) -> float:
    return max(step, math.ceil(value / step) * step)




def run_analysis_chart(
    records: pd.DataFrame,
    bounds: list[int] | None,
    threshold_hr: int | None,
    theme: str = "light",
) -> alt.VConcatChart | None:
    """Il grafico a tre fasce, o None se non c'e' niente da disegnare.

    Ogni pannello c'e' solo se c'e' il suo dato: battiti se c'e' la FC,
    velocita' se c'e' la velocita', pendenza se ci sono quota e distanza. La
    linea equivalente c'e' solo se il database ha `equiv_speed_kmh` (gli sport
    a piedi). Senza `bounds` niente bande, senza `threshold_hr` niente
    effetti. I pannelli hanno ognuno la sua scala: velocita' e pendenza non si
    confrontano in altezza, e i battiti non partono da zero."""
    if records.empty:
        return None
    palette = _PALETTES.get(theme, _PALETTES["light"])
    data = bins(records)
    if data.empty:
        return None

    has_hr = data["hr"].notna().any()
    has_speed = (data["speed"] > 0).any()
    has_slope = data["slope_pct"].notna().any()
    has_equiv = data["equiv"].notna().any()
    if not (has_hr or has_speed):
        return None
    with_zones = bool(bounds) and has_hr
    with_effects = with_zones and has_effects(bounds, threshold_hr)

    t = _elapsed_s(records)
    total_min = (t[-1] + 1) / 60
    x_scale = alt.Scale(domain=[0, total_min], nice=False, zero=True)
    # Un po' di stacco fra le barre, proporzionale all'intervallo.
    data["bar_end"] = data["end"] - BIN_S / 60 * 0.15

    # Il tooltip e' uno solo per tutti i pannelli: ogni colonna che manca
    # resta fuori invece di comparire vuota.
    data["time"] = data["start"].map(_clock) + "–" + data["end"].map(_clock)
    tooltip = [alt.Tooltip("time:N", title="Time")]
    if has_hr:
        tooltip.append(alt.Tooltip("hr:Q", title="HR (bpm)", format=".0f"))
    if with_zones:
        data["zone"] = data["hr"].map(lambda h: f"Z{zone_of(h, bounds)}" if pd.notna(h) else None)
        tooltip.append(alt.Tooltip("zone:N", title="Zone"))
    if with_effects:
        data["effect"] = data["hr"].map(
            lambda h: effect_of(h, bounds, threshold_hr) if pd.notna(h) else None
        )
        tooltip.append(alt.Tooltip("effect:N", title="Effect (estimated)"))
    if has_speed:
        tooltip.append(alt.Tooltip("speed:Q", title="Speed (km/h)", format=".1f"))
    if has_equiv:
        tooltip.append(alt.Tooltip("equiv:Q", title="Grade-adjusted (km/h)", format=".1f"))
    if has_slope:
        tooltip.append(alt.Tooltip("slope_deg:Q", title="Slope (°)", format=".1f"))
        tooltip.append(alt.Tooltip("slope_pct:Q", title="Slope (%)", format=".1f"))

    hover = alt.selection_point(
        name="hovered", fields=["start"], nearest=True, on="pointermove", empty=False, clear="pointerout"
    )
    base = alt.Chart(data)
    bands = zone_bands(records, bounds) if with_zones else pd.DataFrame()
    pause_list = pauses(records)

    def background(x_axis: alt.Axis) -> list:
        """Le bande delle zone, a tutta altezza, e il crosshair: in ogni
        pannello, con le stesse x, cosi' sembrano una banda sola."""
        layers = []
        if not bands.empty:
            layers.append(
                alt.Chart(bands)
                .mark_rect(color=palette["zone"])
                .encode(
                    x=alt.X("start:Q", scale=x_scale, axis=x_axis),
                    x2="end:Q",
                    opacity=alt.Opacity(
                        "zone:O",
                        scale=alt.Scale(domain=[1, 2, 3, 4, 5], range=palette["zone_opacity"]),
                        legend=None,
                    ),
                )
            )
        return layers

    def crosshair(x_axis: alt.Axis) -> list:
        # Il selettore e' una regola trasparente per intervallo: il punto piu'
        # vicino al mouse lungo x accende la stessa regola in tutti i pannelli.
        rule = (
            base.mark_rule(color=palette["muted"], strokeDash=[4, 4])
            .encode(
                x=alt.X("minute:Q", scale=x_scale, axis=x_axis),
                opacity=alt.condition(hover, alt.value(1), alt.value(0)),
                tooltip=tooltip,
            )
            .add_params(hover)
        )
        return [rule]

    panels = []
    panel_count = sum([has_hr, has_speed, has_slope])

    def axis_for(position: int) -> alt.Axis:
        """L'asse del tempo: con le etichette solo nel pannello in fondo, che
        basta leggerle una volta; sopra, stessa scala e niente scritte."""
        if position == panel_count - 1:
            return alt.Axis(title="Elapsed time (min)")
        return alt.Axis(labels=False, ticks=False, title=None)

    position = 0
    if has_hr:
        x_axis = axis_for(position)
        x = alt.X("start:Q", scale=x_scale, axis=x_axis)
        position += 1
        hr_low = math.floor(data["hr"].min() / 10) * 10
        hr_high = _ceil(data["hr"].max(), 10)
        hr_scale = alt.Scale(domain=[hr_low, hr_high], zero=False, nice=False)
        y = alt.Y("hr:Q", title="HR (bpm)", scale=hr_scale, axis=alt.Axis(tickCount=3))
        color = (
            alt.Color(
                "effect:N",
                title="Effect (estimated)",
                scale=alt.Scale(
                    domain=list(EFFECTS),
                    range=[palette["zone_half"], palette["zone"], palette["anaerobic"]],
                ),
                legend=alt.Legend(orient="bottom", title=None),
            )
            if with_effects
            else alt.value(palette["zone"])
        )
        layers = background(x_axis)
        layers.append(
            base.mark_bar(clip=True)
            .encode(x=x, x2="bar_end:Q", y=y, y2=alt.datum(hr_low), color=color)
        )
        if with_effects:
            # Le due soglie degli effetti, sopra le barre, e il nome di ogni
            # fascia sul bordo destro, a meta' fra le soglie (se ci cade).
            limits = [hr_low, bounds[2], threshold_hr, hr_high]
            rules = pd.DataFrame({"y": [bounds[2], threshold_hr]})
            rules = rules[(rules["y"] > hr_low) & (rules["y"] < hr_high)]
            if not rules.empty:
                layers.append(
                    alt.Chart(rules)
                    .mark_rule(color=palette["muted"], strokeDash=[4, 3])
                    .encode(y=alt.Y("y:Q", scale=hr_scale))
                )
            labels = pd.DataFrame(
                {
                    "label": [e.lower() for e in EFFECTS],
                    "y": [(max(lo, hr_low) + min(hi, hr_high)) / 2 for lo, hi in zip(limits, limits[1:])],
                    "visible": [min(hi, hr_high) - max(lo, hr_low) >= (hr_high - hr_low) * 0.15
                                for lo, hi in zip(limits, limits[1:])],
                }
            )
            labels = labels[labels["visible"]]
            if not labels.empty:
                layers.append(
                    alt.Chart(labels)
                    .mark_text(align="right", baseline="middle", dx=-4, fontSize=10, color=palette["muted"])
                    .encode(x=alt.datum(total_min, scale=x_scale), y=alt.Y("y:Q", scale=hr_scale), text="label:N")
                )
        # Sopra il pannello piu' in alto, la zona di ogni banda e, se la banda
        # e' abbastanza larga, la media dei battiti; e "pause" sulle pause.
        if position == 1 and not bands.empty:
            band_labels = bands.assign(
                mid=(bands["start"] + bands["end"]) / 2,
                zone_label="Z" + bands["zone"].astype(str),
                avg_label=bands["hr"].map(lambda h: f"avg {h:.0f}"),
                labelled=(bands["end"] - bands["start"]) >= total_min * _ZONE_LABEL_MIN_SHARE,
                wide=(bands["end"] - bands["start"]) >= total_min * _AVG_LABEL_MIN_SHARE,
            )
            layers.append(
                alt.Chart(band_labels[band_labels["labelled"]])
                .mark_text(baseline="bottom", fontSize=11, fontWeight="bold", color=palette["zone"])
                .encode(x=alt.X("mid:Q", scale=x_scale), y=alt.value(-14), text="zone_label:N")
            )
            layers.append(
                alt.Chart(band_labels[band_labels["wide"]])
                .mark_text(baseline="bottom", fontSize=10, color=palette["muted"])
                .encode(x=alt.X("mid:Q", scale=x_scale), y=alt.value(-2), text="avg_label:N")
            )
        if position == 1 and pause_list:
            pause_frame = pd.DataFrame(pause_list, columns=["start", "end"])
            pause_frame["mid"] = (pause_frame["start"] + pause_frame["end"]) / 2
            pause_frame = pause_frame[
                pause_frame["end"] - pause_frame["start"] >= total_min * _PAUSE_LABEL_MIN_SHARE
            ]
            layers.append(
                alt.Chart(pause_frame)
                .mark_text(baseline="bottom", fontSize=10, fontStyle="italic", color=palette["muted"])
                .encode(x=alt.X("mid:Q", scale=x_scale), y=alt.value(-14), text=alt.value("pause"))
            )
        layers.extend(crosshair(x_axis))
        panels.append(alt.layer(*layers).properties(height=130, width="container"))

    if has_speed:
        x_axis = axis_for(position)
        position += 1
        # Le linee si interrompono dove manca un intervallo (pause, o tratti
        # con troppo pochi campioni): una riga vuota per ogni buco.
        full = data.set_index("bin").reindex(range(data["bin"].min(), data["bin"].max() + 1))
        full["start"] = (full.index + 0.5) * BIN_S / 60
        series = {"speed": "Speed"}
        if has_equiv:
            series["equiv"] = "Grade-adjusted"
        lines = full[["start", *series]].rename(columns=series).melt(
            id_vars="start", var_name="series", value_name="kmh"
        )
        speed_high = _ceil(np.nanmax(full[list(series)].to_numpy()))
        y_scale = alt.Scale(domain=[0, speed_high], nice=False)
        layers = background(x_axis)
        # Con intervalli tutti isolati (una vasca in piscina ha pochi record)
        # una linea non si vedrebbe: allora i punti.
        isolated = not (data["bin"].diff() == 1).any()
        layers.append(
            alt.Chart(lines)
            .mark_line(strokeWidth=2, point=isolated)
            .encode(
                x=alt.X("start:Q", scale=x_scale, axis=x_axis),
                y=alt.Y("kmh:Q", title="Speed (km/h)", scale=y_scale),
                color=alt.Color(
                    "series:N",
                    scale=alt.Scale(domain=list(series.values()), range=[palette["speed"], palette["equiv"]][: len(series)]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                strokeDash=alt.StrokeDash(
                    "series:N",
                    scale=alt.Scale(domain=list(series.values()), range=[[1, 0], [5, 3]][: len(series)]),
                    legend=None,
                ),
            )
        )
        layers.extend(crosshair(x_axis))
        panels.append(alt.layer(*layers).properties(height=260, width="container"))

    if has_slope:
        x_axis = axis_for(position)
        x = alt.X("start:Q", scale=x_scale, axis=x_axis)
        position += 1
        data["slope_abs"] = data["slope_deg"].abs()
        data["direction"] = np.where(data["slope_deg"] >= 0, "Uphill", "Downhill")
        slope_base = alt.Chart(data)
        layers = background(x_axis)
        layers.append(
            slope_base.mark_bar(opacity=0.8)
            .encode(
                x=x,
                x2="bar_end:Q",
                y=alt.Y(
                    "slope_abs:Q",
                    title="Slope (°)",
                    scale=alt.Scale(domain=[0, _ceil(data["slope_abs"].max())], nice=False),
                    axis=alt.Axis(orient="right", tickCount=3),
                ),
                y2=alt.datum(0),
                color=alt.Color(
                    "direction:N",
                    scale=alt.Scale(domain=["Uphill", "Downhill"], range=[palette["up"], palette["down"]]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
            )
        )
        layers.extend(crosshair(x_axis))
        panels.append(alt.layer(*layers).properties(height=100, width="container"))

    # Lo stesso `hover` sta in tutti i pannelli apposta, perche' il crosshair
    # si muova insieme su tutti: Altair lo unisce in un parametro solo e lo
    # segnala con un avviso, che qui non dice niente di nuovo.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Automatically deduplicated selection parameter")
        chart = alt.vconcat(*panels, spacing=8)
    return (
        chart
        .resolve_scale(color="independent", opacity="independent", strokeDash="independent")
        .properties(
            description="Activity chart over elapsed time: heart rate"
            + (" with heart-rate zones" if with_zones else "")
            + (", speed and grade-adjusted speed" if has_equiv else ", speed" if has_speed else "")
            + (", and slope in degrees" if has_slope else "")
            + "."
        )
    )
