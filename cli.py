"""Punto de entrada: corre el modelo de frontera para las 3 ventanas.

Uso:
    python cli.py
Salida:
    outputs/frontera.json   + reporte por consola
"""
from __future__ import annotations
import json
from pathlib import Path

from engine import data_io as io
from engine.model_frontera import Ventana, Params, max_frecuencia_ventana, chequeo_flota

OUT = Path(__file__).resolve().parent / "outputs"

# --- Parámetros físicos (explícitos y conservadores) ---------------------------
cuello = io.cargar_tramo_unico()
ocup_pax_s = io.tiempo_ocupacion_cuello(cuello["long_m"], vmax_kmh=40.0)
PARAMS = Params(
    ocup_pax_min=ocup_pax_s / 60.0,    # ~derivado de la long. del tramo único
    clearing_min=2.0,                  # separación de seguridad entre usos
    ocup_carga_min=10.0,               # tren de carga: más lento/largo
    headway_min=6,                     # headway mínimo mismo sentido
    desbalance_cap=99,                 # inyectados: el exceso direccional escapa a L1
)

VENTANAS = [
    Ventana("Punta mañana", 5 * 60 + 30, 9 * 60),       # 05:30–09:00
    Ventana("Valle",        9 * 60,      16 * 60),       # 09:00–16:00
    Ventana("Punta tarde",  16 * 60,     19 * 60 + 45),  # 16:00–19:45
]


def main():
    surcos = io.cargar_surcos_carga_cuello()
    ciclo = io.ciclo_redondo_min()
    flota = io.flota_l2_disponible()

    print("=" * 72)
    print("MODELO DE FRONTERA — máxima frecuencia L2 por ventana")
    print(f"Tramo único: {cuello['nombre']} ({cuello['long_m']:.0f} m)")
    print(f"Ocupación pax del tramo: {PARAMS.ocup_pax_min:.1f} min "
          f"(+{PARAMS.clearing_min:.0f} clearing) | carga: {PARAMS.ocup_carga_min:.0f} min")
    print(f"Ciclo redondo: {ciclo:.0f} min | flota disponible: {flota}")
    print(f"Surcos de carga que cruzan Concepción en el día: {len(surcos)}")
    print("=" * 72)

    resultados = []
    for v in VENTANAS:
        r = max_frecuencia_ventana(v, surcos, PARAMS)
        f_dir = max(r["serv_norte_por_hora"], r["serv_sur_por_hora"])
        r["flota"] = chequeo_flota(f_dir, ciclo, flota)
        resultados.append(r)

        print(f"\n▶ {r['ventana']}  ({r['rango']}, {r['horas']} h)  [{r['status']}]")
        print(f"    surcos de carga en la ventana : {r['surcos_carga_en_ventana']}")
        print(f"    servicios máx NORTE→Concepción : {r['pasos_norte']}  "
              f"({r['serv_norte_por_hora']}/h, headway ~{r['headway_norte_min']} min)")
        print(f"    servicios máx SUR→Coronel      : {r['pasos_sur']}  "
              f"({r['serv_sur_por_hora']}/h, headway ~{r['headway_sur_min']} min)")
        fl = r["flota"]
        marca = "⚠ FLOTA LIMITA" if fl["flota_limita"] else "✓ flota suficiente"
        print(f"    flota: requiere ~{fl['unidades_requeridas_aprox']} de "
              f"{fl['flota_disponible']} unidades  →  {marca}")

    OUT.mkdir(exist_ok=True)
    (OUT / "frontera.json").write_text(
        json.dumps({"params": PARAMS.__dict__, "ciclo_min": float(ciclo),
                    "surcos_carga_total": len(surcos), "ventanas": resultados},
                   ensure_ascii=False, indent=2))
    print(f"\n→ outputs/frontera.json escrito.")


if __name__ == "__main__":
    main()
