"""Carga de datos canónicos y derivación de parámetros físicos del modelo.

Toda magnitud que el modelo necesita se deriva aquí de los CSV validados,
o se declara como parámetro explícito y conservador (no escondido en el solver).
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def cargar_tramo_unico() -> dict:
    """Tramo único de L2 (cuello Chepe–Concepción) y su longitud."""
    vu = pd.read_csv(DATA / "via_unica.csv")
    bl = pd.read_csv(DATA / "bloques.csv")
    l2_single = bl[(bl.linea == "L2") & (bl.tipo == "single")]
    long_m = float(l2_single.longitud_m.sum())          # ~2000 m (km1–3)
    km_lo = float(l2_single.dist_lo.min())
    km_hi = float(l2_single.dist_hi.max())
    return {"long_m": long_m, "km_lo": km_lo, "km_hi": km_hi,
            "nombre": "Concepción ↔ salida Túnel Chepe"}


def tiempo_ocupacion_cuello(long_m: float, vmax_kmh: float = 40.0,
                            margen_arranque_s: float = 60.0) -> float:
    """Tiempo (s) que un automotor ocupa el tramo único.

    Traversal de `long_m` a una velocidad media conservadora (la salida es desde
    detención en Concepción, por eso vmax bajo) + margen de arranque. Es el tiempo
    durante el cual NINGÚN otro tren —ni de carga— puede entrar al tramo.
    """
    t_marcha = long_m / (vmax_kmh / 3.6)                 # s
    return t_marcha + margen_arranque_s


def cargar_surcos_carga_cuello() -> list[int]:
    """Minutos (desde medianoche) en que un tren de carga cruza Concepción en L2.

    Cada uno bloquea el tramo único en torno a esa hora.
    """
    mc = pd.read_csv(DATA / "malla_carga.csv")
    l2 = mc[mc.linea == "L2"]
    conce = l2[l2.estacion.str.upper().str.contains("CONCEP")]
    return sorted(int(round(h)) for h in conce.hora_min.dropna().unique())


def ciclo_redondo_min() -> float:
    """Tiempo de ciclo de un servicio (ida + vuelta + giros), en minutos.

    Suma de tiempos de viaje extendidos + detenciones de un sentido, ×2,
    + tiempo de giro/cambio de cabina en cada terminal.
    """
    it = pd.read_csv(DATA / "itinerario_tiempos.csv")
    una_via = it[it.sentido == "CC->CW"]
    s = una_via.t_viaje_ext_s.fillna(una_via.t_viaje_s).sum()
    s += una_via.detencion_s.fillna(0).sum()
    GIRO_S = 8 * 60                                       # cambio de cabina por terminal
    total_s = 2 * s + 2 * GIRO_S
    return total_s / 60.0


def flota_l2_disponible() -> int:
    """Automotores SFE disponibles para L2 (parámetro operacional)."""
    # material_rodante lista la flota; en operación L2 usa ~7 de los 12 activos.
    return 12
