import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import requests
import io
import plotly.express as px
import plotly.graph_objects as go
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

# Variables de sesión para la selección de jugadores por clic
if 'jugadores_seleccionados_dosis' not in st.session_state:
    st.session_state.jugadores_seleccionados_dosis = []
if 'dosis_key' not in st.session_state:
    st.session_state.dosis_key = 0

# =============================================================================
# 2. EXTRACCIÓN Y UNIFICACIÓN DE DATOS (GPS + RPE)
# =============================================================================
def descargar_csv_drive(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return pd.read_csv(io.StringIO(res.text))
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_datos_dosis_respuesta():
    # 1. Cargar RPE desde Google Sheets
    df_rpe_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    df_rpe = pd.DataFrame()
    
    if not df_rpe_raw.empty:
        cols = df_rpe_raw.columns
        col_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        col_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        col_t = next((c for c in cols if str(c).lower().strip() == 'tipo de sesión' or 'tipo de sesion' in str(c).lower()), cols[2])
        col_min = next((c for c in cols if 'minuto' in str(c).lower()), cols[3] if len(cols)>3 else None)
        col_c = next((c for c in cols if 'cardio' in str(c).lower()), cols[4] if len(cols)>4 else None)
        col_m = next((c for c in cols if 'muscular' in str(c).lower()), cols[5] if len(cols)>5 else None)

        df_rpe['Fecha'] = pd.to_datetime(df_rpe_raw[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_rpe['Nombre_Cruce'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip().str.lower()
        df_rpe['Nombre_Oficial'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip()
        df_rpe['Tipo_Sesion'] = df_rpe_raw[col_t].fillna('Entreno').astype(str).str.strip().str.title()
        
        mins = pd.to_numeric(df_rpe_raw[col_min], errors='coerce').fillna(0) if col_min else 0
        val_c = pd.to_numeric(df_rpe_raw[col_c], errors='coerce').fillna(0) if col_c else 0
        val_m = pd.to_numeric(df_rpe_raw[col_m], errors='coerce').fillna(0) if col_m else 0
        
        df_rpe['Minutos'] = mins
        df_rpe['RPE_G'] = (val_c + val_m) / 2
        # sRPE = RPE_G * Minutos
        df_rpe['sRPE'] = df_rpe['RPE_G'] * df_rpe['Minutos']
        df_rpe = df_rpe.dropna(subset=['Fecha'])

    # 2. Cargar GPS local
    ruta_gps = os.path.join("data", "GPS")
    df_gps = pd.DataFrame()
    if os.path.exists(ruta_gps):
        archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
        lista_dfs = []
        for f in archivos:
            if "~$" in f: continue
            try:
                df_temp = pd.read_excel(f, sheet_name=1)
                cols_lower = [str(c).lower().strip() for c in df_temp.columns]
                df_temp.columns = cols_lower
                
                def buscar_col(keywords):
                    for c in df_temp.columns:
                        if any(k in c for k in keywords): return c
                    return None
                    
                col_fecha = buscar_col(['fecha', 'date'])
                col_nombre = buscar_col(['nombre', 'name', 'player'])
                col_dt = buscar_col(['distancia total', 'distance'])
                col_18 = buscar_col(['> 18', '>18'])
                col_25 = buscar_col(['> 25', '>25'])
                col_acc = buscar_col(['aceleraciones', 'accel', 'nº aceleraciones'])
                col_dec = buscar_col(['desaceleraciones', 'decel', 'nº desaceleraciones'])
                
                if not col_fecha or not col_nombre: continue
                
                def fix_num(val):
                    try: return float(str(val).replace(',', '.'))
                    except: return 0.0

                df_l = pd.DataFrame()
                df_l['Fecha'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                df_l['Nombre_GPS'] = df_temp[col_nombre].astype(str).str.strip()
                df_l['Nombre_Cruce'] = df_l['Nombre_GPS'].str.lower()
                
                df_l['Dist_Total'] = df_temp[col_dt].apply(fix_num) if col_dt else 0.0
                df_l['Dist_18'] = df_temp[col_18].apply(fix_num) if col_18 else 0.0
                df_l['Dist_25'] = df_temp[col_25].apply(fix_num) if col_25 else 0.0
                df_l['Accels'] = df_temp[col_acc].apply(fix_num) if col_acc else 0.0
                df_l['Decels'] = df_temp[col_dec].apply(fix_num) if col_dec else 0.0

                lista_dfs.append(df_l.dropna(subset=['Fecha']))
            except: continue
                
        if lista_dfs:
            df_gps = pd.concat(lista_dfs, ignore_index=True)
            if df_gps['Dist_Total'].max() < 25: 
                df_gps['Dist_Total'] = df_gps['Dist_Total'] * 1000
                df_gps['Dist_18'] = df_gps['Dist_18'] * 1000
                df_gps['Dist_25'] = df_gps['Dist_25'] * 1000

    if df_gps.empty or df_rpe.empty:
        return pd.DataFrame()

    # 3. Fusionar GPS + RPE
    df_merged = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='inner')
    
    # Carga UA = [ Dist_Total + (Dist_18 * 2) + (Dist_25 * 4) + ((Acel + Desac) * 1.5) ] * RPE_G
    df_merged['Carga_UA'] = (
        df_merged['Dist_Total'] + 
        (df_merged['Dist_18'] * 2) + 
        (df_merged['Dist_25'] * 4) + 
        ((df_merged['Accels'] + df_merged['Decels']) * 1.5)
    ) * df_merged['RPE_G']

    return df_merged

df_dosis = cargar_datos_dosis_respuesta()

# =============================================================================
# 3. INTERFAZ Y GRÁFICO DOSIS - RESPUESTA
# =============================================================================
st.markdown("""
    <div>
        <h1 style="margin-bottom: 0px;">DOSIS - RESPUESTA</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Relación entre la Carga Externa Ponderada (UA) y la Carga Interna Percibida (sRPE).</p>
    </div>
""", unsafe_allow_html=True)

if df_dosis.empty:
    st.info("🚧 No hay suficientes datos coincidentes de GPS y RPE para construir la relación Dosis-Respuesta.")
    st.stop()

st.markdown("---")

# --- FILTROS ---
c_f1, c_f2 = st.columns([1, 2.5])

with c_f1:
    tipos_sesion = ["Todos"] + sorted(list(df_dosis['Tipo_Sesion'].unique()))
    tipo_sel = st.selectbox("⚽ Tipo de Sesión:", tipos_sesion)

with c_f2:
    # 1. FILTRO DE FECHAS EN SLIDER (BARRITA DESLIZANTE)
    fechas_dt_unicas = sorted([datetime.strptime(f, '%Y-%m-%d').date() for f in df_dosis['Fecha'].unique()])
    min_date_val, max_date_val = fechas_dt_unicas[0], fechas_dt_unicas[-1]
    
    rango_slider = st.slider(
        "📅 Rango de Fechas:",
        min_value=min_date_val,
        max_value=max_date_val,
        value=(min_date_val, max_date_val),
        format="DD/MM/YYYY"
    )

# Aplicar Filtro de Fecha y Tipo de Sesión
df_filtrado = df_dosis.copy()

if tipo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Tipo_Sesion'] == tipo_sel]

if len(rango_slider) == 2:
    f_ini_str = rango_slider[0].strftime('%Y-%m-%d')
    f_fin_str = rango_slider[1].strftime('%Y-%m-%d')
    df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= f_ini_str) & (df_filtrado['Fecha'] <= f_fin_str)]

# Lógica del botón de limpieza de selección de jugador
c_info_f, c_btn = st.columns([3, 1])
with c_info_f:
    if st.session_state.jugadores_seleccionados_dosis:
        st.markdown(f"🏃 **Filtrado por jugador(es):** `{', '.join(st.session_state.jugadores_seleccionados_dosis)}`")
    else:
        st.caption("💡 Haz clic sobre los círculos del gráfico para filtrar/aislar a esos jugadores.")

with c_btn:
    if st.session_state.jugadores_seleccionados_dosis:
        if st.button("🧹 Limpiar Selección", use_container_width=True):
            st.session_state.jugadores_seleccionados_dosis = []
            st.session_state.dosis_key += 1
            st.rerun()

if st.session_state.jugadores_seleccionados_dosis:
    df_grafico = df_filtrado[df_filtrado['Nombre_Oficial'].isin(st.session_state.jugadores_seleccionados_dosis)]
else:
    df_grafico = df_filtrado.copy()

if df_grafico.empty:
    st.warning("No hay registros para los filtros seleccionados.")
    st.stop()

# --- CONSTRUCCIÓN DE LA GRÁFICA DE DISPERSIÓN ---
media_srpe = df_filtrado['sRPE'].mean()
media_ua = df_filtrado['Carga_UA'].mean()

fig = px.scatter(
    df_grafico,
    x="sRPE",
    y="Carga_UA",
    color="Nombre_Oficial",
    custom_data=["Nombre_Oficial", "Fecha", "Tipo_Sesion"],
    hover_data=["Fecha", "Tipo_Sesion", "Minutos", "RPE_G", "Dist_Total"],
    labels={
        "sRPE": "Carga Interna (sRPE) → [RPE * Duración]",
        "Carga_UA": "Carga Externa Ponderada (UA) ↑",
        "Nombre_Oficial": "Jugador"
    },
    template="plotly_dark"
)

# Estilo de puntos
fig.update_traces(marker=dict(size=14, line=dict(width=1, color='White')))

# Líneas cruzadas de la media global
fig.add_vline(x=media_srpe, line=dict(color="#F1C40F", width=1.5, dash="dash"))
fig.add_hline(y=media_ua, line=dict(color="#F1C40F", width=1.5, dash="dash"))

fig.update_layout(
    height=600,
    plot_bgcolor='rgba(0,0,0,0.2)',
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(l=20, r=20, t=30, b=80)
)

# 2. CAPTURA DE CLICS EN LOS CÍRCULOS DEL GRÁFICO
dosis_chart_key = f"dosis_chart_{st.session_state.dosis_key}"
try:
    seleccion_dosis = st.plotly_chart(
        fig,
        use_container_width=True,
        config={'displayModeBar': False},
        on_select="rerun",
        selection_mode=["points", "box", "lasso"],
        key=dosis_chart_key
    )
    
    if seleccion_dosis and hasattr(seleccion_dosis, 'selection'):
        pts = getattr(seleccion_dosis.selection, 'points', [])
        cambio = False
        for p in pts:
            cd = p.get('customdata')
            if cd:
                nom_j = cd[0] if isinstance(cd, list) else cd
                if nom_j not in st.session_state.jugadores_seleccionados_dosis:
                    st.session_state.jugadores_seleccionados_dosis.append(nom_j)
                    cambio = True
        if cambio:
            st.session_state.dosis_key += 1
            st.rerun()
except Exception:
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})