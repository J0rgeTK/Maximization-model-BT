"""Malla gráfica / Diagrama de Marey (distancia–tiempo) — motor puro, sin Streamlit.

Estilo: estaciones nominadas en el eje Y posicionadas por distancia, marcadores
por parada, tiempo en HH:MM, bandas de vía única. Verificable headless:
    fig = build_marey(df, "L1"); fig.to_dict()
"""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go

# bandas de vía única por línea: (km_lo, km_hi, dureza, etiqueta)
#   "duro"  = sin posibilidad de cruce ; "suave" = vía única con desvíos
VIA_UNICA = {
    "L2": [(1.0, 3.0, "duro", "Cuello Chepe (vía única, sin cruce)")],
    "L1": [(1.6, 46.92, "suave", "Laja–Hualqui (vía única c/ desvíos)"),
           (46.92, 55.32, "suave", "Hualqui–La Leonera (vía única)"),
           (82.79, 84.78, "duro", "Mercado–Arenal (vía única, sin cruce)")],
}
FILL = {"duro": "rgba(220,40,40,0.13)", "suave": "rgba(255,120,80,0.06)"}

# azul = sentido hacia el norte de la cadena (CC->CW, LJ->TH) ; rojo = inverso
COLOR = {"CC->CW": "#1F4E78", "CW->CC": "#C0392B",
         "LJ->TH": "#1F4E78", "TH->LJ": "#C0392B"}
ETIQ = {"CC->CW": "CC → CW", "CW->CC": "CW → CC",
        "LJ->TH": "LJ → TH", "TH->LJ": "TH → LJ"}
BASE = pd.Timestamp("2026-01-01")
ORIGEN = {"L1": "Laja → Talcahuano ↓", "L2": "Concepción → Coronel ↓"}


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

    # mapa estación -> distancia (de los propios datos), ordenado
    est = (d.drop_duplicates("estacion")[["estacion", "dist_km"]]
             .sort_values("dist_km"))
    estaciones = list(zip(est.estacion, est.dist_km))
    kmin, kmax = est.dist_km.min(), est.dist_km.max()

    # filtro de ventana (sobre una copia para los trazos)
    dd = d
    if t0 is not None:
        dd = dd[dd.hora_min >= t0 - 60]   # margen para no cortar trazos a medias
    if t1 is not None:
        dd = dd[dd.hora_min <= t1 + 60]

    fig = go.Figure()
    # bandas de vía única (fondo)
    for lo, hi, dureza, etq in VIA_UNICA.get(linea, []):
        fig.add_hrect(y0=lo, y1=hi, fillcolor=FILL[dureza], line_width=0,
                      layer="below", annotation_text=etq,
                      annotation_position="top right", annotation_font_size=9,
                      annotation_font_color="#9a3a3a")

    vista = set()
    for tren, g in dd.groupby("tren_id"):
        g = g.sort_values("hora_min")
        sen = g.sentido.iloc[0]
        show = sen not in vista
        vista.add(sen)
        fig.add_trace(go.Scatter(
            x=BASE + pd.to_timedelta(g.hora_min, unit="m"), y=g.dist_km,
            mode="lines+markers",
            line=dict(color=COLOR.get(sen, "#777"), width=1.4),
            marker=dict(size=4, color=COLOR.get(sen, "#777")),
            name=ETIQ.get(sen, sen), legendgroup=sen, showlegend=show,
            opacity=0.85,
            customdata=[[tren, e, _hhmm(h)] for e, h in zip(g.estacion, g.hora_min)],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}"
                          "<br>%{customdata[2]} · km %{y:.1f}<extra></extra>",
        ))

    # eje Y: nombres de estación por distancia, origen arriba (rango invertido)
    fig.update_yaxes(tickmode="array",
                     tickvals=[k for _, k in estaciones],
                     ticktext=[n for n, _ in estaciones],
                     range=[kmax + 0.5, kmin - 0.5],
                     title=f"Estación ({ORIGEN.get(linea, '')})",
                     gridcolor="#EEEEEE")
    # eje X: tiempo del día HH:MM
    rng = None
    if t0 is not None and t1 is not None:
        rng = [BASE + pd.to_timedelta(t0, unit="m"),
               BASE + pd.to_timedelta(t1, unit="m")]
    fig.update_xaxes(title="Tiempo del día", tickformat="%H:%M",
                     dtick=30 * 60 * 1000, range=rng, gridcolor="#EEEEEE")
    win = f" · ventana {_hhmm(t0)}–{_hhmm(t1)}" if t0 is not None else ""
    fig.update_layout(
        title=titulo or f"Diagrama de Marey — {linea}{win}",
        height=680, hovermode="closest", plot_bgcolor="white",
        legend=dict(orientation="h", y=1.05, x=0.78),
        margin=dict(l=120, r=20, t=60, b=40))
    return fig
