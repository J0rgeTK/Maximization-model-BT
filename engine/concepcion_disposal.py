"""Sub-modelo de disposición en Concepción (bloque 1 de la v2).

Pregunta que responde: en la punta mañana, ¿cuántos servicios L2 al NORTE se
pueden correr, dado que cada llegada a Concepción debe disponerse por una de tres
rutas (volver al sur / inyectar a L1 / esperar+vacío a Arenal), con sus recursos?

- 'sur'    : vuelve al sur. Usa un paso de cuello de salida (alterna con las llegadas).
- 'iny'    : se inyecta a L1. Usa un cupo inyectable de L1 (de CW) y andén Vía 1/2.
- 'arenal' : espera en Vía 4/8 y sale vacío a Arenal a estacionar. No usa el cuello.

El piso de L1 se preserva: 'iny' solo consume cupos inyectables (sobre el piso),
nunca desplaza un servicio L1 programado.

Maximiza el número de servicios L2 al norte. El cuello limita las LLEGADAS; la
disposición (iny + arenal + sur) limita cuántas de esas llegadas se sostienen.
"""
from __future__ import annotations
from dataclasses import dataclass
from ortools.sat.python import cp_model


@dataclass
class ParamsDisp:
    w0: int                 # inicio ventana (min desde medianoche)
    w1: int                 # fin ventana
    ocup_cuello_min: int    # ocupación + clearing del tramo único por paso
    giro_min: int           # giro en Concepción antes de salir al sur
    n_iny: int              # cupos inyectables de L1 en la ventana (de CW)
    via12_cap: int          # andenes L1 simultáneos para inyectar (Vía 1, 2)
    dwell_iny_min: int      # ocupación de andén L1 al inyectar
    via48_cap: int          # posiciones de espera L2 (Vía 4, 6, 8)
    espera_arenal_min: int  # espera en Vía 4/8 antes del vacío a Arenal
    arenal_stab: int        # cupos de estacionamiento en Arenal (tope global)
    surcos_carga: tuple     # minutos de surcos de carga que cruzan el cuello
    ocup_carga_min: int     # ocupación del cuello por surco de carga


def disponer_punta(p: ParamsDisp) -> dict:
    m = cp_model.CpModel()
    L = p.ocup_cuello_min
    slots = list(range(p.w0, p.w1 - L + 1))

    pres, sur, iny, are = {}, {}, {}, {}
    inb, surdep, inyiv, areiv = [], [], [], []
    for t in slots:
        pres[t] = m.NewBoolVar(f"pres_{t}")
        sur[t] = m.NewBoolVar(f"sur_{t}")
        iny[t] = m.NewBoolVar(f"iny_{t}")
        are[t] = m.NewBoolVar(f"are_{t}")
        m.Add(sur[t] + iny[t] + are[t] == pres[t])           # una ruta si se corre
        # llegada por el cuello (inbound) — TODA llegada lo usa
        inb.append(m.NewOptionalIntervalVar(t, L, t + L, pres[t], f"inb_{t}"))
        # 'sur' agrega una salida por el cuello tras el giro (outbound)
        s = t + p.giro_min
        if s + L <= p.w1:
            surdep.append(m.NewOptionalIntervalVar(s, L, s + L, sur[t], f"sd_{t}"))
        else:
            m.Add(sur[t] == 0)
        # 'iny' ocupa andén L1 (Vía 1/2)
        inyiv.append(m.NewOptionalIntervalVar(t, p.dwell_iny_min, t + p.dwell_iny_min,
                                              iny[t], f"iv_{t}"))
        # 'arenal' ocupa Vía 4/8 durante la espera
        areiv.append(m.NewOptionalIntervalVar(t, p.espera_arenal_min,
                                              t + p.espera_arenal_min, are[t], f"av_{t}"))

    # surcos de carga: fusionar solapados y bloquear el cuello
    Lf = p.ocup_carga_min
    crudos = sorted((f, f + Lf) for f in p.surcos_carga if f + Lf > p.w0 and f < p.w1)
    fusion = []
    for s, e in crudos:
        s, e = max(s, p.w0), min(e, p.w1)
        if fusion and s <= fusion[-1][1]:
            fusion[-1][1] = max(fusion[-1][1], e)
        else:
            fusion.append([s, e])
    carga_iv = [m.NewIntervalVar(s, e - s, e, f"frg_{k}") for k, (s, e) in enumerate(fusion)]

    # CUELLO: llegadas + salidas-sur + carga no se solapan (alternancia física)
    m.AddNoOverlap(inb + surdep + carga_iv)
    # ANDENES L1: a lo más via12_cap inyecciones simultáneas
    m.AddCumulative(inyiv, [1] * len(inyiv), p.via12_cap)
    # VÍAS L2 de espera: a lo más via48_cap esperas simultáneas
    m.AddCumulative(areiv, [1] * len(areiv), p.via48_cap)
    # cupos inyectables y estacionamiento de Arenal (topes globales)
    m.Add(sum(iny.values()) <= p.n_iny)
    m.Add(sum(are.values()) <= p.arenal_stab)

    m.Maximize(sum(pres.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    solver.parameters.num_search_workers = 8
    st = solver.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(st)}
    n_sur = sum(int(solver.Value(sur[t])) for t in slots)
    n_iny = sum(int(solver.Value(iny[t])) for t in slots)
    n_are = sum(int(solver.Value(are[t])) for t in slots)
    horas = (p.w1 - p.w0) / 60.0
    norte = n_sur + n_iny + n_are
    # nota: aquí 'norte' = llegadas al norte sostenidas; 'sur' son además servicios sur
    return {
        "status": solver.StatusName(st),
        "servicios_norte": norte,
        "norte_por_hora": round(norte / horas, 2),
        "headway_norte_min": round(60 * horas / norte, 1) if norte else None,
        "ruta_sur": n_sur, "ruta_iny": n_iny, "ruta_arenal": n_are,
        "carga_bloqueos": len(fusion),
    }
