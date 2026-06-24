"""Malla gráfica (diagrama espacio-tiempo / Marey) — motor puro, sin Streamlit.

build_marey() devuelve una figura Plotly desde una tabla de circulación con
columnas: linea, tren_id, sentido, estacion, dist_km, hora_min (min desde 00:00).
Verificable headless:  fig = build_marey(df); fig.to_dict()
"""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go

# bandas de vía única por línea (km_lo, km_hi, etiqueta)
VIA_UNICA = {
    "L2": [(1.0, 3.0, "Cuello Chepe (vía única)")],
    "L1": [(46.92, 55.32, "Hualqui–La Leonera"), (82.79, 84.78, "Mercado–Arenal")],
}
COLOR = {"CC->CW": "#c0504d", "CW->CC": "#1f6f6f"}  # sur dominante / norte dominante


def _hhmm(mins: float) -> str:
    h, m = divmod(int(round(mins)), 60)
    return f"{h:02d}:{m:02d}"


def build_marey(df: pd.DataFrame, linea: str = "L2",
                sentidos: list[str] | None = None,
                t0: float | None = None, t1: float | None = None,
                titulo: str | None = None) -> go.Figure:
    d = df[df.linea == linea].copy()
    if sentidos:
        d = d[d.sentido.isin(sentidos)]
    if t0 is not None:
        d = d[d.hora_min >= t0]
    if t1 is not None:
        d = d[d.hora_min <= t1]

    fig = go.Figure()
    # bandas de vía única (sombreado horizontal)
    for lo, hi, etq in VIA_UNICA.get(linea, []):
        fig.add_hrect(y0=lo, y1=hi, fillcolor="#999", opacity=0.12,
                      line_width=0, annotation_text=etq,
                      annotation_position="top left",
                      annotation_font_size=10)

    leyenda_vista = set()
    for tren, g in d.groupby("tren_id"):
        g = g.sort_values("hora_min")
        sen = g.sentido.iloc[0]
        show = sen not in leyenda_vista
        leyenda_vista.add(sen)
        fig.add_trace(go.Scatter(
            x=g.hora_min, y=g.dist_km, mode="lines",
            line=dict(color=COLOR.get(sen, "#444"), width=1.1),
            name=sen, legendgroup=sen, showlegend=show,
            hovertemplate=f"{tren}<br>%{{customdata}}<br>km %{{y:.1f}}<extra></extra>",
            customdata=[_hhmm(x) for x in g.hora_min],
        ))

    # eje de tiempo en HH:MM
    lo = t0 if t0 is not None else d.hora_min.min()
    hi = t1 if t1 is not None else d.hora_min.max()
    ticks = list(range(int(lo // 30 * 30), int(hi) + 1, 30))
    fig.update_xaxes(title="Hora", tickvals=ticks,
                     ticktext=[_hhmm(t) for t in ticks], range=[lo, hi])
    fig.update_yaxes(title="Distancia (km)", autorange="reversed"
                     if linea == "L2" else True)
    fig.update_layout(
        title=titulo or f"Malla gráfica {linea}",
        height=620, hovermode="closest",
        legend=dict(orientation="h", y=1.04, x=0),
        margin=dict(l=60, r=20, t=60, b=40), plot_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eee")
    fig.update_yaxes(showgrid=True, gridcolor="#eee")
    return fig
