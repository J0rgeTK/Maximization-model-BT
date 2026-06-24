"""Runner del sub-modelo de disposición en Concepción (punta mañana).

Uso:  python cli_disposal.py
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path
from engine.concepcion_disposal import ParamsDisp, disponer_punta

DATA = Path(__file__).resolve().parent / "data"


def surcos_l2_concepcion() -> tuple:
    mc = pd.read_csv(DATA / "malla_carga.csv")
    sel = mc[(mc.linea == "L2") & mc.estacion.str.upper().str.contains("CONCEP")]
    return tuple(sorted(int(round(h)) for h in sel.hora_min.dropna()))


def run(n_iny, arenal_stab, via48=3, surcos=()):
    p = ParamsDisp(w0=330, w1=540, ocup_cuello_min=6, giro_min=10,
                   n_iny=n_iny, via12_cap=2, dwell_iny_min=5,
                   via48_cap=via48, espera_arenal_min=15, arenal_stab=arenal_stab,
                   surcos_carga=surcos, ocup_carga_min=12)
    return disponer_punta(p)


def main():
    surcos = surcos_l2_concepcion()
    print("Piso L1 (Circular): punta mañana 9 servicios intocables; ~4 cupos inyectables (de CW)")
    print("=" * 60)
    r = run(4, 8, surcos=surcos)
    print(f"BASE: {r['servicios_norte']} servicios L2 norte "
          f"(headway ~{r['headway_norte_min']} min) | "
          f"sur {r['ruta_sur']} / iny {r['ruta_iny']} / arenal {r['ruta_arenal']}")
    print()
    print(f"{'n_iny':>6} {'arenal':>7} {'via4/8':>7} | {'NORTE':>6} {'sur':>5} {'iny':>5} {'arenal':>7}")
    for n_iny, stab, via in [(4, 0, 3), (4, 4, 3), (4, 8, 3), (4, 12, 3),
                             (8, 8, 3), (8, 12, 4), (8, 20, 4)]:
        r = run(n_iny, stab, via, surcos)
        print(f"{n_iny:>6} {stab:>7} {via:>7} | {r['servicios_norte']:>6} "
              f"{r['ruta_sur']:>5} {r['ruta_iny']:>5} {r['ruta_arenal']:>7}")


if __name__ == "__main__":
    main()
