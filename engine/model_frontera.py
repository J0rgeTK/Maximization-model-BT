"""Modelo de frontera (Etapa 1) — máxima frecuencia por ventana.

Trata el tramo único Chepe–Concepción como un recurso compartido por TODOS los
trenes que entran o salen de Concepción (pasajeros en ambos sentidos + carga).
La restricción física: a lo más un tren dentro del tramo único a la vez.

NO usa demanda. Responde "cuánto se PUEDE correr", no "cuánto conviene".
La oferta queda limitada por el tramo único y, en el valle, por la carga que
lo ocupa. La flota se chequea aparte (puede limitar por debajo de la frontera).
"""
from __future__ import annotations
from dataclasses import dataclass
from ortools.sat.python import cp_model


@dataclass
class Ventana:
    nombre: str
    inicio_min: int      # minutos desde medianoche
    fin_min: int


@dataclass
class Params:
    ocup_pax_min: float       # ocupación del tramo único por automotor (min)
    clearing_min: float       # separación de seguridad entre usos sucesivos (min)
    ocup_carga_min: float     # ocupación del tramo único por tren de carga (min)
    headway_min: int          # headway mínimo mismo sentido (min)
    desbalance_cap: int       # |N - S| máximo dentro de la ventana (estacionamiento CC)


def max_frecuencia_ventana(v: Ventana, surcos_carga: list[int],
                           p: Params) -> dict:
    """Maximiza pasos de pasajeros por el tramo único en la ventana."""
    m = cp_model.CpModel()
    L = int(round(p.ocup_pax_min + p.clearing_min))          # largo efectivo pax
    Lf = int(round(p.ocup_carga_min + p.clearing_min))       # largo efectivo carga
    W0, W1 = v.inicio_min, v.fin_min
    sentidos = ["N", "S"]

    # slots candidatos cada 1 min
    slots = list(range(W0, W1 - L + 1))
    pick: dict = {}
    intervals = []
    for d in sentidos:
        for t in slots:
            b = m.NewBoolVar(f"pick_{d}_{t}")
            iv = m.NewOptionalIntervalVar(t, L, t + L, b, f"iv_{d}_{t}")
            pick[(d, t)] = b
            intervals.append(iv)

    # surcos de carga: intervalos fijos en el mismo recurso.
    # La carga no se solapa consigo misma: se fusionan los surcos que caen
    # juntos en un único bloque ocupado (unión), que es la física real del tramo.
    crudos = sorted((f, f + Lf) for f in surcos_carga if f + Lf > W0 and f < W1)
    fusion: list[list[int]] = []
    for s, e in crudos:
        s = max(s, W0); e = min(e, W1)
        if fusion and s <= fusion[-1][1]:
            fusion[-1][1] = max(fusion[-1][1], e)
        else:
            fusion.append([s, e])
    carga_en_ventana = [f for f in surcos_carga if W0 <= f < W1]
    for k, (s, e) in enumerate(fusion):
        intervals.append(m.NewIntervalVar(s, e - s, e, f"frg_{k}"))

    # núcleo físico: nada se solapa en el tramo único
    m.AddNoOverlap(intervals)

    # headway mínimo mismo sentido (regularidad operacional)
    for d in sentidos:
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                if slots[j] - slots[i] >= p.headway_min:
                    break
                m.AddBoolOr([pick[(d, slots[i])].Not(), pick[(d, slots[j])].Not()])

    # desbalance direccional acotado por estacionamiento en Concepción
    nN = sum(pick[("N", t)] for t in slots)
    nS = sum(pick[("S", t)] for t in slots)
    m.Add(nN - nS <= p.desbalance_cap)
    m.Add(nS - nN <= p.desbalance_cap)

    m.Maximize(sum(pick.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)

    horas = (W1 - W0) / 60.0
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"ventana": v.nombre, "status": solver.StatusName(status),
                "rango": f"{W0//60:02d}:{W0%60:02d}–{W1//60:02d}:{W1%60:02d}",
                "horas": round(horas, 2), "error": "sin solución factible"}

    min_carga = sum(e - s for s, e in fusion)
    sel = {d: sorted(t for t in slots if solver.Value(pick[(d, t)]))
           for d in sentidos}
    n_n, n_s = len(sel["N"]), len(sel["S"])
    total = n_n + n_s
    return {
        "ventana": v.nombre,
        "rango": f"{W0//60:02d}:{W0%60:02d}–{W1//60:02d}:{W1%60:02d}",
        "horas": round(horas, 2),
        "status": solver.StatusName(status),
        "surcos_carga_en_ventana": len(carga_en_ventana),
        "bloques_carga_fusionados": len(fusion),
        "min_tramo_ocupado_carga": int(min_carga),
        "pasos_norte": n_n,
        "pasos_sur": n_s,
        "pasos_totales": total,
        "serv_norte_por_hora": round(n_n / horas, 2),
        "serv_sur_por_hora": round(n_s / horas, 2),
        "headway_norte_min": round(60 * horas / n_n, 1) if n_n else None,
        "headway_sur_min": round(60 * horas / n_s, 1) if n_s else None,
        "horarios_norte": sel["N"],
        "horarios_sur": sel["S"],
    }


def chequeo_flota(serv_por_hora_dir: float, ciclo_min: float,
                  flota_disp: int) -> dict:
    """¿La frontera del tramo único exige más flota de la disponible?"""
    # unidades necesarias ≈ frecuencia/hora/sentido × ciclo(h)  (cada unidad
    # produce 60/ciclo servicios por hora por sentido)
    req = serv_por_hora_dir * (ciclo_min / 60.0)
    return {
        "ciclo_min": round(float(ciclo_min), 1),
        "unidades_requeridas_aprox": round(float(req), 1),
        "flota_disponible": int(flota_disp),
        "flota_limita": bool(req > flota_disp),
    }
