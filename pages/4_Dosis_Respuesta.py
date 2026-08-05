import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import requests
import io
import plotly.express as px
from datetime import datetime
from utils import aplicar_diseno_responsive

# =============================================================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# =============================================================================
aplicar_diseno_responsive()

st.set_page_config(
    page_title="Dosis - Respuesta | Adarve DH",
    page_icon="⚡",
    layout="wide"
)

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
    st.stop()

_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        import base64
        _b64 = base64.b64encode(_f.read()).decode()
        
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{
            position: fixed; bottom: 20px; left: 10px; width: 260px; text-align: center;
            z-index: 999; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.15);
        }}
        .footer-sello-unico img {{ width: 195px; height: auto; margin-bottom: 8px; }}
        .footer-sello-unico p {{ font-size: 11px !important; color: #CCCCCC !important; margin: 2px 0 0 0 !important; letter-spacing: 0.5px; }}
        </style>
        <div class="footer-sello-unico">
            <img src="data:image/png;base64,{_b64}">
            <p>© 2026 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

if 'jugadores_seleccionados_dosis' not in st.session_state:
    st.session_state.jugadores_seleccionados_dosis = []

# =============================================================================
# 2. CARGA DE DATOS SEGURA Y RÁPIDA
# =============================================================================
def descargar_csv_drive(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return pd.read_csv(io.StringIO(res.text))
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_basicos():
    # RPE
    df_rpe_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if df_rpe_raw.empty:
        return pd.DataFrame()
    
    cols = df_rpe_raw.columns
    col_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
    col_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
    col_t = next((c for c in cols if str(c).lower().strip() == 'tipo de sesión' or 'tipo de sesion' in str(c).lower()), cols[2])
    col_min = next((c for c in cols if 'minuto' in str(c).lower()), cols[3] if len(cols)>3 else None)
    col_c = next((c for c in cols if 'cardio' in str(c).lower()), cols[4] if len(cols)>4 else None)
    col_m = next((c for c in cols if 'muscular' in str(c).lower()), cols[5] if len(cols)>5 else None)

    df_rpe = pd.DataFrame()
    df_rpe['Fecha'] = pd.to_datetime(df_rpe_raw[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_rpe['Nombre_Cruce'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip().str.lower()
    df_rpe['Nombre_Oficial'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip()
    df_rpe['Tipo_Sesion'] = df_rpe_raw[col_t].fillna('Entreno').astype(str).str.strip().str.title()
    
    mins = pd.to_numeric(df_rpe_raw[col_min], errors='coerce').fillna(0) if col_min else 0
    val_c = pd.to_numeric(df_rpe_raw[col_c], errors='coerce').fillna(0) if col_c else 0
    val_m = pd.to_numeric(df_rpe_raw[col_m], errors='coerce').fillna(0) if col_m else 0
    
    df_rpe['Minutos'] = mins
    df_rpe['RPE_G'] = (val_c + val_m) / 2
    df_rpe['sRPE'] = df_rpe['RPE_G'] * df_rpe['Minutos']

    # GPS
    ruta_gps = os.path.join("data", "GPS")
    df_gps = pd.DataFrame()
    if os.path.exists(ruta_gps):
        archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
        lista_dfs = []
        for f in archivos:
            if "~$" in f: continue
            try:
                df_temp = pd.read_excel(f, sheet_name=1)
                cols_l = [str(c).lower().strip() for c in df_temp.columns]
                df_temp.columns = cols_l
                
                col_fecha = next((c for c in df_temp.columns if 'fecha' in c or 'date' in c), None)
                col_nombre = next((c for c in df_temp.columns if 'nombre' in c or 'player' in c), None)
                col_dt = next((c for c in df_temp.columns if 'distancia total' in c or 'distance' in c), None)
                col_18 = next((c for c in df_temp.columns if '> 18' in c or '>18' in c), None)
                col_25 = next((c for c in df_temp.columns if '> 25' in c or '>25' in c), None)
                col_acc = next((c for c in df_temp.columns if 'aceleraciones' in c or 'accel' in c), None)
                col_dec = next((c for c in df_temp.columns if 'desaceleraciones' in c or 'decel' in c), None)
                col_vmax = next((c for c in df_temp.columns if 'v. max' in c or 'top speed' in c), None)

                if not col_fecha or not col_nombre: continue

                def fix_num(v):
                    try: return float(str(v).replace(',', '.'))
                    except: return 0.0

                df_l = pd.DataFrame()
                df_l['Fecha'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                df_l['Nombre_Cruce'] = df_temp[col_nombre].astype(str).str.strip().str.lower()
                df_l['Dist_Total'] = df_temp[col_dt].apply(fix_num) if col_dt else 0.0
                df_l['Dist_18'] = df_temp[col_18].apply(fix_num) if col_18 else 0.0
                df_l['Dist_25'] = df_temp[col_25].apply(fix_num) if col_25 else 0.0
                df_l['Accels'] = df_temp[col_acc].apply(fix_num) if col_acc else 0.0
                df_l['Decels'] = df_temp[col_dec].apply(fix_num) if col_dec else 0.0
                df_l['V_MAX'] = df_temp[col_vmax].apply(fix_num) if col_vmax else 0.0

                lista_dfs.append(df_l.dropna(subset=['Fecha']))
            except Exception:
                continue

        if lista_dfs:
            df_gps = pd.concat(lista_dfs, ignore_index=True)
            if not df_gps.empty and df_gps['Dist_Total'].max() < 25:
                df_gps['Dist_Total'] *= 1000
                df_gps['Dist_18'] *= 1000
                df_gps['Dist_25'] *= 1000

    if df_gps.empty:
        return pd.DataFrame()

    df_base = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='inner')
    df_base['Carga_UA'] = (
        df_base['Dist_Total'] + 
        (df_base['Dist_18'] * 2) + 
        (df_base['Dist_25'] * 4) + 
        ((df_base['Accels'] + df_base['Decels']) * 1.5)
    ) * df_base['RPE_G']

    return df_base

# =============================================================================
# 3. RENDERIZADO DE INTERFAZ
# =============================================================================
st.title("DOSIS - RESPUESTA")
st.markdown("---")

df_dosis = cargar_datos_basicos()

if df_dosis.empty:
    st.info("🚧 No hay suficientes datos coincidentes de GPS y RPE para mostrar el análisis.")
else:
    c1, c2 = st.columns([1, 2])
    with c1:
        tipo_sel = st.selectbox("Tipo Sesión:", ["Todos"] + sorted(list(df_dosis['Tipo_Sesion'].unique())))
    with c2:
        fechas = sorted([datetime.strptime(f, '%Y-%m-%d').date() for f in df_dosis['Fecha'].unique()])
        rango = st.slider("Fechas:", min_value=fechas[0], max_value=fechas[-1], value=(fechas[0], fechas[-1]))

    df_f = df_dosis.copy()
    if tipo_sel != "Todos":
        df_f = df_f[df_f['Tipo_Sesion'] == tipo_sel]
    
    f_ini_str = rango[0].strftime('%Y-%m-%d')
    f_fin_str = rango[1].strftime('%Y-%m-%d')
    df_f = df_f[(df_f['Fecha'] >= f_ini_str) & (df_f['Fecha'] <= f_fin_str)]

    if df_f.empty:
        st.warning("No hay registros en el rango seleccionado.")
    else:
        # Gráfico Dispersión
        fig = px.scatter(
            df_f, x="sRPE", y="Carga_UA", color="Nombre_Oficial",
            title="Dosis (Carga UA) vs Respuesta (sRPE)",
            labels={
                "sRPE": "Carga Interna (sRPE)",
                "Carga_UA": "Carga Externa Ponderada (UA)",
                "Nombre_Oficial": "Jugador"
            },
            template="plotly_dark"
        )
        fig.update_traces(marker=dict(size=12))
        st.plotly_chart(fig, use_container_width=True)

        # Matriz de Correlación
        st.markdown("### 📊 Matriz de Correlaciones")
        cols_corr = ['sRPE', 'Carga_UA', 'Dist_Total', 'Dist_18', 'Dist_25', 'V_MAX']
        cols_ok = [c for c in cols_corr if c in df_f.columns]
        
        if len(cols_ok) > 1:
            matriz = df_f[cols_ok].corr()
            fig_corr = px.imshow(matriz, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", range_color=[-1, 1])
            fig_corr.update_layout(template="plotly_dark", height=450)
            st.plotly_chart(fig_corr, use_container_width=True)