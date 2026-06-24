"""Simulación inicial Biotren — capa de presentación (Streamlit).

Toda la lógica vive en engine/. Esta capa solo dibuja y conecta controles.
Correr:  streamlit run app_streamlit.py
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
from pathlib import Path

from engine.viz_marey import build_marey
from engine.concepcion_disposal import ParamsDisp, disponer_punta

DATA = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="Biotren — simulación L1/L2", layout="wide")


@st.cache_data
def cargar_malla():
    return pd.read_csv(DATA / "malla_marey.csv")


@st.cache_data
def surcos_l2():
    mc = pd.read_csv(DATA / "malla_carga.csv")
    sel = mc[(mc.linea == "L2") & mc.estacion.str.upper().str.contains("CONCEP")]
    return tuple(sorted(int(round(h)) for h in sel.hora_min.dropna()))


mm = cargar_malla()

st.title("Biotren — simulación de circulación L1 / L2")
st.caption("Malla gráfica sobre la circulación real (Circular 2/445) + sub-modelo "
           "de disposición de inyectados en Concepción.")

# ---- barra lateral: controles ----
with st.sidebar:
    st.header("Malla gráfica")
    linea = st.radio("Línea", ["L2", "L1"], horizontal=True)
    ventana = st.select_slider(
        "Ventana", options=["Punta mañana", "Valle", "Punta tarde", "Día completo"],
        value="Punta mañana")
    rangos = {"Punta mañana": (300, 600), "Valle": (540, 960),
              "Punta tarde": (960, 1200), "Día completo": (300, 1465)}
    t0, t1 = rangos[ventana]

    st.divider()
    st.header("Disposición de inyectados")
    st.caption("Punta mañana, sentido norte. Piso L1 preservado.")
    n_iny = st.slider("Cupos inyectables a L1 (de CW)", 0, 10, 4)
    arenal = st.slider("Cupos espera + vacío a Arenal", 0, 20, 8)
    via48 = st.slider("Vías de espera (4/6/8)", 1, 4, 3)

# ---- malla gráfica ----
col_m, col_d = st.columns([3, 1])

with col_m:
    fig = build_marey(mm, linea=linea, t0=t0, t1=t1,
                      titulo=f"Malla {linea} — {ventana}")
    st.plotly_chart(fig, use_container_width=True)

# ---- panel del sub-modelo ----
with col_d:
    st.subheader("Sentido norte L2")
    p = ParamsDisp(w0=330, w1=540, ocup_cuello_min=6, giro_min=10,
                   n_iny=n_iny, via12_cap=2, dwell_iny_min=5,
                   via48_cap=via48, espera_arenal_min=15, arenal_stab=arenal,
                   surcos_carga=surcos_l2(), ocup_carga_min=12)
    r = disponer_punta(p)
    if r.get("servicios_norte") is not None:
        st.metric("Servicios al norte", r["servicios_norte"],
                  help="Punta mañana 05:30–09:00")
        st.metric("Headway", f"~{r['headway_norte_min']} min")
        st.write("**Reparto de la disposición**")
        st.dataframe(pd.DataFrame({
            "ruta": ["volver al sur", "inyectar a L1", "espera + vacío Arenal"],
            "servicios": [r["ruta_sur"], r["ruta_iny"], r["ruta_arenal"]],
        }), hide_index=True, use_container_width=True)
        st.caption(f"Real en la Circular: 22 al norte (~11 min).")
    else:
        st.warning(f"Sin solución: {r.get('status')}")

# ---- restricciones operativas codificadas ----
with st.expander("Restricciones operativas consideradas"):
    st.markdown(
        "- **Cuello Chepe–Concepción (L2)**: vía única sin desvío → alternancia "
        "estricta; techo de frecuencia simétrica ~11 min.\n"
        "- **Inyectados**: cada llegada al norte se dispone como volver al sur / "
        "inyectar a L1 (Vía 1-2) / esperar + vacío a Arenal (Vía 4-8).\n"
        "- **Bucle L1** (Arenal ↔ La Leonera): tipo de servicio corto, además de "
        "los completos Laja–Talcahuano.\n"
        "- **L2 direccional**: el desvío de Lagunillas está del lado de la vía "
        "Coronel→Concepción; un servicio arranca en Cristo Redentor (no en "
        "Coronel) y el posicionamiento en vacío matinal corre a contra-sentido, "
        "ocupando en exclusiva la vía opuesta mientras dura.")
