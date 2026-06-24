# biotren-maxserv — Etapa 1: modelo de frontera

Calcula la **máxima frecuencia** que el tramo único Chepe–Concepción de L2
aguanta por ventana (punta mañana / valle / punta tarde), entre los surcos de
carga. No usa demanda: responde "cuánto se PUEDE correr", no "cuánto conviene".

## Uso
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python cli.py
```
Salida: reporte por consola + `outputs/frontera.json`.

## Estructura
- `engine/data_io.py` — carga datos canónicos y deriva parámetros físicos.
- `engine/model_frontera.py` — modelo CP-SAT (tramo único como recurso NoOverlap).
- `cli.py` — corre las 3 ventanas y emite el reporte.
- `data/` — datos canónicos (via_unica, bloques, itinerario_tiempos, malla_carga, flota, cocheras).

## Alcance v1 (honesto)
- El tramo único es el único recurso limitante modelado; la carga lo bloquea.
- La flota se chequea de forma agregada (ciclo redondo), no con conservación fina.
- No modela aún tripulaciones, headway en el resto de la línea, ni dinámica de cocheras.
- Resultado = techo superior. Parámetro clave: ocupación del cuello (calibrar con datos medidos).
