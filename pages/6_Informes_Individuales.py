import streamlit as st
from utils import configurar_pagina, exigir_login_staff, controles_sidebar, render_html, nombre_bonito
from informe_jugador import inject_v0_css, lista_jugadores_disponibles, render_informe

# El informe completo vive en informe_jugador.py (compartido con el portal de jugadores)
configurar_pagina("Informe individual | Adarve DH")
exigir_login_staff()
movil = controles_sidebar()
inject_v0_css()

lista_jugadores = lista_jugadores_disponibles()
if not lista_jugadores:
    st.warning("⚠️ No se encontraron jugadores registrados en el sistema.")
    st.stop()

render_html("<div style='height: 1rem;'></div>")
# Mismo ancho que la columna de la foto (1.0 de 4.8) para que el selector no invada la tarjeta
col_filtro, _ = st.columns([1.0, 3.8])
with col_filtro:
    jugador_sel = st.selectbox("Jugador", lista_jugadores, format_func=nombre_bonito, label_visibility="collapsed")
render_html("<div style='height: 1.2rem;'></div>")

render_informe(jugador_sel, movil=movil)
