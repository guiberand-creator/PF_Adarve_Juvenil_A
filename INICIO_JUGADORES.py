import os
import pandas as pd
import streamlit as st
from utils import configurar_pagina, controles_sidebar, inyectar_css, render_html, nombre_bonito
from informe_jugador import inject_v0_css, render_informe, escudo_oficial_b64, TEXT

# =============================================================================
# PORTAL DEL JUGADOR (cada jugador entra con su PIN y solo ve su informe)
# El informe completo vive en informe_jugador.py (compartido con la página del staff)
# =============================================================================
configurar_pagina("Portal del Jugador | ADARVE DH")
inject_v0_css()
inyectar_css("[data-testid='stSidebarNav'] { display: none !important; }")   # los jugadores no ven el menú del staff

if 'jugador_autenticado' not in st.session_state:
    st.session_state['jugador_autenticado'] = None

if not st.session_state['jugador_autenticado']:
    render_html("<div style='height: 2rem;'></div>")
    col_c1, col_c2, col_c3 = st.columns([1, 1.8, 1])
    with col_c2:
        render_html(f"""
            <div style="text-align: center; margin-bottom: 15px;">
                <img src="{escudo_oficial_b64()}" style="width:80px; margin-bottom: 15px;">
                <h1 style="font-size:2rem; font-weight:800; margin-bottom: 0px; color:{TEXT};">PORTAL JUGADORES</h1>
            </div>
        """)
        pin_ingresado = st.text_input("Introduce tu contraseña:", type="password", key="input_pin_jugador")
        if st.button("ACCEDER A MI INFORME", type="primary", width="stretch"):
            r_pos_check = os.path.join("data", "Posiciones.xlsx")
            if os.path.exists(r_pos_check):
                df_p_check = pd.read_excel(r_pos_check)
                col_pass = next((c for c in df_p_check.columns if 'pass' in str(c).lower() or 'clave' in str(c).lower() or 'pin' in str(c).lower()), None)
                col_nom = next((c for c in df_p_check.columns if 'jugador' in str(c).lower() or 'nombre' in str(c).lower()), df_p_check.columns[0])
                if col_pass:
                    df_p_check['PASS_STR'] = df_p_check[col_pass].astype(str).str.split('.').str[0].str.strip()
                    match = df_p_check[df_p_check['PASS_STR'] == str(pin_ingresado).strip()]
                    if not match.empty:
                        st.session_state['jugador_autenticado'] = str(match.iloc[0][col_nom]).strip()
                        st.rerun()
                    else:
                        st.error("❌ PIN incorrecto. Revisa tu clave e inténtalo de nuevo.")
                else:
                    st.error("❌ No se encontró la columna 'PASSWORD' en Posiciones.xlsx.")
            else:
                st.error("❌ No se encontró el archivo de datos 'data/Posiciones.xlsx'.")
    st.stop()

jugador_sel = st.session_state['jugador_autenticado']
movil = controles_sidebar(mostrar_actualizar=False)
with st.sidebar:
    st.markdown(f"**👤 Jugador:** {nombre_bonito(jugador_sel)}")
    if st.button("🚪 Cerrar sesión", width="stretch"):
        st.session_state['jugador_autenticado'] = None
        st.rerun()

render_informe(jugador_sel, movil=movil)
