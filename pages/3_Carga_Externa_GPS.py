import streamlit as st
import pandas as pd
import os
from utils import aplicar_diseno_responsive

# ==========================================
# 1. CONFIGURACIÓN Y DISEÑO
# ==========================================
aplicar_diseno_responsive()

# PROTEGER SUBPÁGINA: Si no viene logueado desde la portada, lo bloqueamos
if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
    st.stop()

# ==========================================
# 2. SELLO FIJO AL PIE DEL SIDEBAR
# ==========================================
_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        import base64
        _b64 = base64.b64encode(_f.read()).decode()
        
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{
            position: fixed;
            bottom: 20px;
            left: 10px;
            width: 260px;
            text-align: center;
            z-index: 999;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
        }}
        .footer-sello-unico img {{
            width: 195px;
            height: auto;
            margin-bottom: 8px;
        }}
        .footer-sello-unico p {{
            font-size: 11px !important;
            color: #CCCCCC !important;
            margin: 2px 0 0 0 !important;
            letter-spacing: 0.5px;
        }}
        </style>

        <div class="footer-sello-unico">
            <img src="data:image/png;base64,{_b64}">
            <p>© 2026 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. INTERFAZ PRINCIPAL (EN CONSTRUCCIÓN)
# ==========================================
st.title("🛰️ CARGA EXTERNA (GPS)")
st.caption("Monitorización de métricas de posicionamiento, distancias y velocidades del equipo ADARVE JUVENIL DH.")
st.markdown("---")

# Aquí meteremos todo el código de gráficas y análisis más adelante
st.info("🚧 Módulo de Carga Externa (GPS) preparado. Pendiente de configurar la ingesta de datos.")