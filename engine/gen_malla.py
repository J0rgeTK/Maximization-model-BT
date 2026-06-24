"""Generador de malla — convierte servicios programados en trayectorias espacio-tiempo.

Pieza base del generador de malla optimizada: el solver decidirá horarios de salida
y recorridos; aquí se traducen a trazos (linea, tren_id, sentido, estacion, dist_km,
hora_min), en el mismo formato que la malla real, para dibujarse en el mismo Marey.
"""
from __future__ import annotations
import pandas as pd


def plantilla_cinematica(mm: pd.DataFrame, linea: str, sentido: str) -> pd.DataFrame:
    """Perfil mediano estación→(dist_km, offset_min) desde la circulación real.

    offset_min = minutos desde la salida del origen hasta cada estación.
    """
    d = mm[(mm.linea == linea) & (mm.sentido == sentido)].copy()
    if d.empty:
        raise ValueError(f"sin datos para {linea} {sentido}")
    # origen del recorrido = estación con menor hora_min en cada tren
    filas = []
    for _, g in d.groupby("tren_id"):
        g = g.sort_values("hora_min")
        t0 = g.hora_min.iloc[0]
        for _, r in g.iterrows():
            filas.append((r.estacion, r.dist_km, r.hora_min - t0))
    p = pd.DataFrame(filas, columns=["estacion", "dist_km", "offset_min"])
    plant = (p.groupby(["estacion", "dist_km"], as_index=False)
               .offset_min.median()
               .sort_values("offset_min").reset_index(drop=True))
    return plant


def generar_servicio(plant: pd.DataFrame, linea: str, sentido: str,
                     tren_id: str, t_salida: float,
                     desde: str | None = None, hasta: str | None = None) -> pd.DataFrame:
    """Trayectoria de un servicio. 'desde'/'hasta' permiten recorridos parciales
    (p.ej. bucle Arenal–La Leonera, o arranque en Cristo Redentor)."""
    p = plant.copy()
    if desde is not None:
        i = p.index[p.estacion.str.upper() == desde.upper()]
        if len(i):
            p = p[p.offset_min >= p.loc[i[0], "offset_min"]]
    if hasta is not None:
        i = p.index[p.estacion.str.upper() == hasta.upper()]
        if len(i):
            p = p[p.offset_min <= p.loc[i[0], "offset_min"]]
    base = p.offset_min.min()
    return pd.DataFrame({
        "linea": linea, "tren_id": tren_id, "sentido": sentido,
        "estacion": p.estacion.values, "dist_km": p.dist_km.values,
        "hora_min": (t_salida + (p.offset_min - base)).values,
    })


def generar_malla(mm: pd.DataFrame, programacion: list[dict]) -> pd.DataFrame:
    """programacion: lista de dicts {linea, sentido, tren_id, t_salida, desde?, hasta?}."""
    cache: dict = {}
    out = []
    for s in programacion:
        key = (s["linea"], s["sentido"])
        if key not in cache:
            cache[key] = plantilla_cinematica(mm, *key)
        out.append(generar_servicio(cache[key], s["linea"], s["sentido"],
                                     s["tren_id"], s["t_salida"],
                                     s.get("desde"), s.get("hasta")))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
