import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils import aplicar_diseno_responsive

# =============================================================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# =============================================================================
aplicar_diseno_responsive()

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

# =============================================================================
# 2. MOTOR DE EXTRACCIÓN DE DATOS (RPE + GPS LOCAL)
# =============================================================================
@st.cache_data(ttl=10)
def obtener_rpe_maestro():
    sheet_id = "1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s"
    gid = "1785642271"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df_rpe = pd.read_csv(url_csv)
        df_rpe['Fecha'] = pd.to_datetime(df_rpe['Marca temporal'], dayfirst=True, errors='coerce').dt.date
        df_rpe['Nombre'] = df_rpe['Nombre y apellidos'].fillna('Anónimo').astype(str).str.strip()
        df_rpe['Tipo de Sesión'] = df_rpe['Tipo de sesión'].fillna('Entreno').astype(str).str.strip().str.lower()
        df_rpe['Minutos_RPE'] = pd.to_numeric(df_rpe['Minutos entreno/partido'], errors='coerce').fillna(0)
        
        # Calcular RPE General
        col_c = [c for c in df_rpe.columns if 'CARDIO' in c.upper()][0]
        col_m = [c for c in df_rpe.columns if 'MUSCULAR' in c.upper()][0]
        df_rpe['RPE_G'] = (pd.to_numeric(df_rpe[col_c], errors='coerce').fillna(0) + pd.to_numeric(df_rpe[col_m], errors='coerce').fillna(0)) / 2
        
        # Determinar el tipo de sesión oficial del día (la respuesta que más se repite)
        df_sesion_dia = df_rpe.groupby('Fecha')['Tipo de Sesión'].apply(lambda x: x.mode()[0] if not x.mode().empty else 'entreno').reset_index()
        df_sesion_dia.rename(columns={'Tipo de Sesión': 'Tipo_Dia_Oficial'}, inplace=True)
        
        df_rpe = pd.merge(df_rpe, df_sesion_dia, on='Fecha', how='left')
        return df_rpe[['Fecha', 'Nombre', 'Tipo_Dia_Oficial', 'Minutos_RPE', 'RPE_G']]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_archivos_gps():
    ruta_gps = os.path.join("data", "GPS")
    if not os.path.exists(ruta_gps):
        return pd.DataFrame()
        
    archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
    lista_dfs = []
    
    for f in archivos:
        if "~$" in f: continue  # Ignorar archivos temporales abiertos
        try:
            # Leer específicamente la página 2 (índice 1)
            df_temp = pd.read_excel(f, sheet_name=1)
            
            # Limpieza y mapeo robusto de columnas
            cols_lower = [str(c).lower().strip() for c in df_temp.columns]
            df_temp.columns = cols_lower
            
            # Buscar columnas clave
            def buscar_col(keywords):
                for c in df_temp.columns:
                    if any(k in c for k in keywords): return c
                return None
                
            col_fecha = buscar_col(['fecha', 'date'])
            col_nombre = buscar_col(['nombre', 'name', 'player'])
            col_pos = buscar_col(['posicion', 'position'])
            col_dur = buscar_col(['duracion', 'duration'])
            
            col_dt = buscar_col(['distancia total', 'distance'])
            col_18 = buscar_col(['> 18', '>18'])
            col_25 = buscar_col(['> 25', '>25'])
            col_28 = buscar_col(['> 28', '>28', 'sprints']) # Ajustado según Excel
            col_spr = buscar_col(['nº sprints', 'sprints'])
            col_acc = buscar_col(['aceleraciones', 'accel'])
            col_dec = buscar_col(['desaceleraciones', 'decel'])
            
            # Si faltan vitales, saltamos
            if not col_fecha or not col_nombre: continue
            
            df_limpio = pd.DataFrame()
            
            # Arreglar formatos europeos de miles (si viene 4.406 como 4406)
            def fix_num(val):
                try:
                    v = str(val).replace(',', '.')
                    return float(v)
                except: return 0.0
            
            # Asignaciones
            df_limpio['Fecha'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.date
            df_limpio['Nombre'] = df_temp[col_nombre].astype(str)
            df_limpio['Posicion'] = df_temp[col_pos].astype(str) if col_pos else 'Sin Posición'
            df_limpio['Duracion_GPS'] = df_temp[col_dur].apply(fix_num) if col_dur else 60.0
            
            df_limpio['Dist_Total'] = df_temp[col_dt].apply(fix_num) if col_dt else 0.0
            df_limpio['Dist_18'] = df_temp[col_18].apply(fix_num) if col_18 else 0.0
            df_limpio['Dist_25'] = df_temp[col_25].apply(fix_num) if col_25 else 0.0
            df_limpio['Dist_28'] = df_temp[col_28].apply(fix_num) if col_28 else 0.0
            
            df_limpio['Sprints'] = df_temp[col_spr].apply(fix_num) if col_spr else 0.0
            df_limpio['Accels'] = df_temp[col_acc].apply(fix_num) if col_acc else 0.0
            df_limpio['Decels'] = df_temp[col_dec].apply(fix_num) if col_dec else 0.0

            lista_dfs.append(df_limpio.dropna(subset=['Fecha']))
        except Exception as e:
            st.warning(f"Error leyendo {f}: {e}")
            
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        # Ajuste de escala: Si la distancia viene como 4.406 km, la pasamos a metros
        if df_final['Dist_Total'].max() < 25: 
            df_final['Dist_Total'] = df_final['Dist_Total'] * 1000
            df_final['Dist_18'] = df_final['Dist_18'] * 1000
            df_final['Dist_25'] = df_final['Dist_25'] * 1000
            df_final['Dist_28'] = df_final['Dist_28'] * 1000
        return df_final
    return pd.DataFrame()

# =============================================================================
# 3. PROCESAMIENTO Y CRUCE (EL CEREBRO DEL SISTEMA)
# =============================================================================
df_rpe = obtener_rpe_maestro()
df_gps = cargar_archivos_gps()

if df_gps.empty:
    st.markdown("""
        <div style="margin-bottom: 15px;">
            <h1 style="margin-bottom: 0px; padding-bottom: 0px;">CARGA EXTERNA (GPS)</h1>
            <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Panel de control y dashboard interactivo de la sesión.</p>
        </div>
    """, unsafe_allow_html=True)
    st.info("🚧 Aún no hay archivos de GPS en la carpeta `data/GPS`. Sube tu primer archivo para ver la magia.")
    st.stop()

# Cruce de datos (GPS manda, añadimos RPE)
if not df_rpe.empty:
    df_master = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre'], how='left')
    df_master['Tipo_Dia_Oficial'] = df_master['Tipo_Dia_Oficial'].fillna('entreno')
    df_master['RPE_G'] = df_master['RPE_G'].fillna(5) # Valor medio por defecto
    df_master['Minutos_RPE'] = df_master['Minutos_RPE'].fillna(df_master['Duracion_GPS'])
else:
    df_master = df_gps.copy()
    df_master['Tipo_Dia_Oficial'] = 'entreno'
    df_master['RPE_G'] = 5
    df_master['Minutos_RPE'] = df_master['Duracion_GPS']

# FILTRO INTELIGENTE DE EXCLUSIONES (+1, +2 y PARTIDOS)
def incluir_en_media(row):
    tipo = str(row['Tipo_Dia_Oficial'])
    mins = row['Minutos_RPE']
    if 'partido' in tipo: return mins >= 60
    if '+1' in tipo or '+2' in tipo: return mins < 60
    return True

df_master['Valido_Media'] = df_master.apply(incluir_en_media, axis=1)

# CÁLCULO CARGA UA INDICADOR (El que pediste)
# (Dist Total + (Dist >18 * 1.5) + Dist > 25) * RPE
df_master['Carga_UA'] = (df_master['Dist_Total'] + (df_master['Dist_18'] * 1.5) + df_master['Dist_25']) * df_master['RPE_G']

# Fechas ordenadas
fechas_disp = sorted(df_master['Fecha'].unique(), reverse=True)

# =============================================================================
# 4. INTERFAZ: CABECERA Y DASHBOARD #1
# =============================================================================
st.markdown("""
    <div style="margin-bottom: 5px;">
        <h1 style="margin-bottom: 0px; padding-bottom: 0px;">SESSION DASHBOARD (GPS)</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Evolución táctica, referencias de partido y fatiga neuromuscular.</p>
    </div>
""", unsafe_allow_html=True)

# Barra de herramientas superior
col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    fecha_sel = st.selectbox("📅 Select Date:", fechas_disp)
with col_f2:
    # FIX: Limpiamos los vacíos (nan) antes de ordenar para evitar el TypeError
    posiciones_validas = [str(p) for p in df_master['Posicion'].unique() if str(p).lower() != 'nan']
    posiciones = ["Equipo Completo"] + sorted(posiciones_validas)
    pos_sel = st.selectbox("⚽ Posición:", posiciones)

# Filtro por posición para las medias
if pos_sel == "Equipo Completo":
    df_sesion = df_master[(df_master['Fecha'] == fecha_sel) & (df_master['Valido_Media'] == True)]
else:
    df_sesion = df_master[(df_master['Fecha'] == fecha_sel) & (df_master['Valido_Media'] == True) & (df_master['Posicion'] == pos_sel)]

tipo_sesion = str(df_master[df_master['Fecha'] == fecha_sel]['Tipo_Dia_Oficial'].iloc[0]).upper()

# FIX: Si la duración está vacía, ponemos 0 en vez de que crashee
max_dur = df_master[df_master['Fecha'] == fecha_sel]['Duracion_GPS'].max()
duracion_sesion = int(max_dur) if pd.notna(max_dur) else 0

# --- CONSTRUCCIÓN DEL HISTÓRICO 28 DÍAS ---
fecha_inicio_28 = fecha_sel - timedelta(days=28)
df_hist = df_master[(df_master['Fecha'] >= fecha_inicio_28) & (df_master['Fecha'] <= fecha_sel) & (df_master['Valido_Media'] == True)]
if pos_sel != "Equipo Completo": df_hist = df_hist[df_hist['Posicion'] == pos_sel]

df_hist_eq = df_hist.groupby('Fecha').agg({'Carga_UA': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()

fig_hist = go.Figure()
colores_hist = ['#FF9F1C' if 'partido' in str(t) else '#555555' for t in df_hist_eq['Tipo_Dia_Oficial']]
textos_hist = ['P' if 'partido' in str(t) else 'Tr' for t in df_hist_eq['Tipo_Dia_Oficial']]

fig_hist.add_trace(go.Bar(
    x=df_hist_eq['Fecha'], y=df_hist_eq['Carga_UA'],
    marker_color=colores_hist, text=textos_hist, textposition='outside',
    hoverinfo='x+y', textfont=dict(color="white", size=12)
))
fig_hist.update_layout(
    template="plotly_dark", height=150, margin=dict(l=0, r=0, t=20, b=0),
    xaxis=dict(showgrid=False, showticklabels=False),
    yaxis=dict(showgrid=False, showticklabels=False, visible=False),
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
)

st.markdown("---")
# PINTAR CABECERA TIPO BULLET
c_dur, c_hist, c_info = st.columns([1.5, 3, 2])
with c_dur:
    st.markdown("<p style='color:#A0AEC0; font-size:14px; margin-bottom:0;'>Session duration</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color:#8C52FF; font-size:55px; margin-top:0;'>{duracion_sesion} min</h1>", unsafe_allow_html=True)
with c_hist:
    st.markdown(f"<p style='color:#A0AEC0; font-size:14px; margin-bottom:0;'><b>Last 28 days</b> training schedule</p>", unsafe_allow_html=True)
    st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
with c_info:
    st.markdown(f"<p style='color:#A0AEC0; font-size:14px; margin-bottom:0;'>Session Type / Focus</p>", unsafe_allow_html=True)
    st.markdown(f"<h2>{tipo_sesion}</h2>", unsafe_allow_html=True)
    st.caption("Filtro Activo: Se ocultan titulares en post-partido y suplentes en partidos para las medias.")

# =============================================================================
# 5. CÁLCULO DE LA LÍNEA ROJA (TARGET 4 PARTIDOS)
# =============================================================================
df_partidos = df_master[df_master['Tipo_Dia_Oficial'].str.contains('partido')]
# Partidos solo validos (> 60 min)
df_partidos = df_partidos[df_partidos['Valido_Media'] == True]

target_refs = {}
if not df_partidos.empty:
    # Coger ultimos 4 partidos
    ultimos_4_fechas = sorted(df_partidos['Fecha'].unique(), reverse=True)[:4]
    df_ult_4 = df_partidos[df_partidos['Fecha'].isin(ultimos_4_fechas)]
    
    if pos_sel != "Equipo Completo":
        df_ult_4 = df_ult_4[df_ult_4['Posicion'] == pos_sel]
        
    for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']:
        if not df_ult_4.empty:
            mean_m = df_ult_4[metrica].mean()
            max_m = df_ult_4[metrica].max()
            target_refs[metrica] = (mean_m + max_m) / 2
        else:
            target_refs[metrica] = 0.0
else:
    # Fallback a 0 si no hay partidos grabados aun
    for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']: target_refs[metrica] = 0.0

# Medias de la sesion actual
medias_sesion = {}
for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']:
    medias_sesion[metrica] = df_sesion[metrica].mean() if not df_sesion.empty else 0.0

# =============================================================================
# 6. PINTAR LOS BULLET CHARTS ESTILO PROFESIONAL
# =============================================================================
st.markdown("### 📊 Metrics Summary vs Match Target")

def pintar_bullet(metrica, nombre_mostrar, row_col, max_val_global):
    val = medias_sesion.get(metrica, 0)
    target = target_refs.get(metrica, 0)
    
    # Prevenir bugs de grafico roto si es 0
    max_range = max(val, target) * 1.3 if max(val, target) > 0 else 10
    
    fig = go.Figure(go.Indicator(
        mode = "number+gauge", value = val,
        number = {'valueformat': ".1f" if val < 100 else ".0f", 'font': {'size': 25, 'color': 'white'}},
        gauge = {
            'shape': "bullet",
            'axis': {'range': [None, max_range], 'visible': False},
            'bar': {'color': "#E67E22", 'thickness': 0.8},
            'bgcolor': "rgba(255,255,255,0.1)",
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.9, 'value': target
            }
        }
    ))
    fig.update_layout(height=80, margin=dict(t=20, b=0, l=0, r=40), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    
    with row_col:
        st.markdown(f"<p style='margin-bottom:0; font-size:14px; color:#CCCCCC;'>{nombre_mostrar}</p>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Fila 1
r1_1, r1_2, r1_3, r1_4 = st.columns(4)
pintar_bullet('Dist_Total', 'Total Distance (m)', r1_1, 12000)
pintar_bullet('Dist_18', 'Distance > 18 km/h (m)', r1_2, 1000)
pintar_bullet('Dist_25', 'Distance > 25 km/h (m)', r1_3, 400)
pintar_bullet('Dist_28', 'Distance > 28 km/h (m)', r1_4, 150)

# Fila 2
r2_1, r2_2, r2_3, r2_4 = st.columns(4)
pintar_bullet('Sprints', 'Total Sprints', r2_1, 30)
pintar_bullet('Accels', 'Accelerations', r2_2, 60)
pintar_bullet('Decels', 'Decelerations', r2_3, 60)

# Para llenar el hueco con una mini-leyenda:
with r2_4:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("🟠 **Barra Naranja:** Media del grupo (Filtrado)")
    st.markdown("🔴 **Línea Roja (Target):** (Media + Máx) / 2 de últimos 4 Partidos")

st.markdown("---")
st.info("🎯 **Próximo paso:** Programar las pestañas inferiores (Dashboard #2 y #3) para ver a los jugadores de forma individual.")