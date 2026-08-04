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
        # FIX: Respetar mayusculas/minusculas originales de "Sesion +2", etc.
        df_rpe['Tipo de Sesión'] = df_rpe['Tipo de sesión'].fillna('Entreno').astype(str).str.strip()
        df_rpe['Minutos_RPE'] = pd.to_numeric(df_rpe['Minutos entreno/partido'], errors='coerce').fillna(0)
        
        # Calcular RPE General
        col_c = [c for c in df_rpe.columns if 'CARDIO' in c.upper()][0]
        col_m = [c for c in df_rpe.columns if 'MUSCULAR' in c.upper()][0]
        df_rpe['RPE_G'] = (pd.to_numeric(df_rpe[col_c], errors='coerce').fillna(0) + pd.to_numeric(df_rpe[col_m], errors='coerce').fillna(0)) / 2
        
        # Determinar el tipo de sesión oficial del día
        df_sesion_dia = df_rpe.groupby('Fecha')['Tipo de Sesión'].apply(lambda x: x.mode()[0] if not x.mode().empty else 'Entreno').reset_index()
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
            col_pos = buscar_col(['posicion', 'position'])
            col_dur = buscar_col(['duracion', 'duration'])
            
            col_dt = buscar_col(['distancia total', 'distance'])
            col_18 = buscar_col(['> 18', '>18'])
            col_25 = buscar_col(['> 25', '>25'])
            col_28 = buscar_col(['> 28', '>28', 'sprints']) 
            col_spr = buscar_col(['nº sprints', 'sprints'])
            col_acc = buscar_col(['aceleraciones', 'accel'])
            col_dec = buscar_col(['desaceleraciones', 'decel'])
            col_vmax = buscar_col(['v. max', 'v.max', 'top speed', 'velocidad maxima'])
            
            if not col_fecha or not col_nombre: continue
            
            df_limpio = pd.DataFrame()
            
            def fix_num(val):
                try:
                    v = str(val).replace(',', '.')
                    return float(v)
                except: return 0.0
            
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
            df_limpio['Top_Speed'] = df_temp[col_vmax].apply(fix_num) if col_vmax else 0.0

            lista_dfs.append(df_limpio.dropna(subset=['Fecha']))
        except Exception as e:
            st.warning(f"Error leyendo {f}: {e}")
            
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        if df_final['Dist_Total'].max() < 25: 
            df_final['Dist_Total'] = df_final['Dist_Total'] * 1000
            df_final['Dist_18'] = df_final['Dist_18'] * 1000
            df_final['Dist_25'] = df_final['Dist_25'] * 1000
            df_final['Dist_28'] = df_final['Dist_28'] * 1000
        return df_final
    return pd.DataFrame()

# =============================================================================
# 3. PROCESAMIENTO Y CRUCE 
# =============================================================================
df_rpe = obtener_rpe_maestro()
df_gps = cargar_archivos_gps()

if df_gps.empty:
    st.info("🚧 Aún no hay archivos de GPS en la carpeta `data/GPS`.")
    st.stop()

if not df_rpe.empty:
    df_master = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre'], how='left')
    df_master['Tipo_Dia_Oficial'] = df_master['Tipo_Dia_Oficial'].fillna('Entreno')
    df_master['RPE_G'] = df_master['RPE_G'].fillna(5) 
    df_master['Minutos_RPE'] = df_master['Minutos_RPE'].fillna(df_master['Duracion_GPS'])
else:
    df_master = df_gps.copy()
    df_master['Tipo_Dia_Oficial'] = 'Entreno'
    df_master['RPE_G'] = 5
    df_master['Minutos_RPE'] = df_master['Duracion_GPS']

def incluir_en_media(row):
    tipo = str(row['Tipo_Dia_Oficial']).lower()
    mins = row['Minutos_RPE']
    if 'partido' in tipo: return mins >= 60
    if '+1' in tipo or '+2' in tipo: return mins < 60
    return True

df_master['Valido_Media'] = df_master.apply(incluir_en_media, axis=1)
df_master['Carga_UA'] = (df_master['Dist_Total'] + (df_master['Dist_18'] * 1.5) + df_master['Dist_25']) * df_master['RPE_G']
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

col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    fecha_sel = st.selectbox("📅 Select Date:", fechas_disp)
with col_f2:
    posiciones_validas = [str(p) for p in df_master['Posicion'].unique() if str(p).lower() != 'nan']
    posiciones = ["Equipo Completo"] + sorted(posiciones_validas)
    pos_sel = st.selectbox("⚽ Posición:", posiciones)

if pos_sel == "Equipo Completo":
    df_sesion = df_master[(df_master['Fecha'] == fecha_sel) & (df_master['Valido_Media'] == True)]
else:
    df_sesion = df_master[(df_master['Fecha'] == fecha_sel) & (df_master['Valido_Media'] == True) & (df_master['Posicion'] == pos_sel)]

tipo_sesion = str(df_master[df_master['Fecha'] == fecha_sel]['Tipo_Dia_Oficial'].iloc[0]).upper()
max_dur = df_master[df_master['Fecha'] == fecha_sel]['Duracion_GPS'].max()
duracion_sesion = int(max_dur) if pd.notna(max_dur) else 0

fecha_inicio_vmax = fecha_sel - timedelta(days=28)
df_28d = df_master[(df_master['Fecha'] >= fecha_inicio_vmax) & (df_master['Fecha'] <= fecha_sel)]

vmax_hist = df_28d.groupby('Nombre')['Top_Speed'].max().reset_index()
vmax_hist.rename(columns={'Top_Speed': 'Vmax_4_semanas'}, inplace=True)

df_vmax_sesion = df_master[df_master['Fecha'] == fecha_sel][['Nombre', 'Top_Speed', 'Posicion']].merge(vmax_hist, on='Nombre', how='left')
df_vmax_sesion['Porcentaje_Vmax'] = np.where(
    df_vmax_sesion['Vmax_4_semanas'] > 0, 
    (df_vmax_sesion['Top_Speed'] / df_vmax_sesion['Vmax_4_semanas']) * 100, 
    0
)

if pos_sel != "Equipo Completo":
    df_vmax_sesion = df_vmax_sesion[df_vmax_sesion['Posicion'] == pos_sel]

media_vmax_sesion = df_vmax_sesion['Porcentaje_Vmax'].mean() if not df_vmax_sesion.empty else 0
alcanzan_90 = df_vmax_sesion[df_vmax_sesion['Porcentaje_Vmax'] >= 90].sort_values(by='Porcentaje_Vmax', ascending=False)
no_alcanzan_90 = df_vmax_sesion[(df_vmax_sesion['Porcentaje_Vmax'] < 90) & (df_vmax_sesion['Vmax_4_semanas'] > 0)].sort_values(by='Porcentaje_Vmax', ascending=False)

df_hist = df_28d[df_28d['Valido_Media'] == True]
if pos_sel != "Equipo Completo": df_hist = df_hist[df_hist['Posicion'] == pos_sel]

df_hist_eq = df_hist.groupby('Fecha').agg({'Carga_UA': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()

fig_hist = go.Figure()
colores_hist = ['#FF9F1C' if 'partido' in str(t).lower() else '#555555' for t in df_hist_eq['Tipo_Dia_Oficial']]
textos_hist = ['P' if 'partido' in str(t).lower() else 'Tr' for t in df_hist_eq['Tipo_Dia_Oficial']]

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
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Session duration</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color:white; font-size:55px; margin-top:0; margin-bottom:0px;'>{duracion_sesion} min</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:white; font-size:16px; font-weight:bold; margin-top:0;'>TIPO: {tipo_sesion}</p>", unsafe_allow_html=True)
    
with c_hist:
    st.markdown(f"<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Last 28 days training schedule</p>", unsafe_allow_html=True)
    st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False}, key="hist_28")

with c_info:
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Exposición Velocidad Máxima (>90%)</p>", unsafe_allow_html=True)
    color_vmax = "#2ECC71" if media_vmax_sesion >= 90 else "#F1C40F" if media_vmax_sesion >= 85 else "#E74C3C"
    st.markdown(f"<h2 style='color:{color_vmax}; margin-top:0;'>{media_vmax_sesion:.1f}% <span style='font-size:14px; color:#A0AEC0; font-weight:normal;'>media equipo</span></h2>", unsafe_allow_html=True)
    
    with st.expander("👁️ Ver Jugadores"):
        st.markdown("**✅ Lograron el 90%:**")
        if not alcanzan_90.empty:
            for _, row in alcanzan_90.iterrows():
                st.markdown(f"<span style='color:#2ECC71; font-size:14px;'>• {row['Nombre']} ({row['Porcentaje_Vmax']:.1f}%)</span>", unsafe_allow_html=True)
        else:
            st.caption("Ninguno")
            
        st.markdown("**❌ No llegaron al 90%:**")
        if not no_alcanzan_90.empty:
            for _, row in no_alcanzan_90.iterrows():
                st.markdown(f"<span style='color:#E74C3C; font-size:14px;'>• {row['Nombre']} ({row['Porcentaje_Vmax']:.1f}%)</span>", unsafe_allow_html=True)
        else:
            st.caption("Ninguno")

# =============================================================================
# 5. CÁLCULO DE LA LÍNEA ROJA Y ACUMULADOS
# =============================================================================
df_partidos = df_master[df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido', na=False)]
df_partidos = df_partidos[df_partidos['Valido_Media'] == True]

target_refs = {}
if not df_partidos.empty:
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
    for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']: target_refs[metrica] = 0.0

medias_sesion = {}
for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']:
    medias_sesion[metrica] = df_sesion[metrica].mean() if not df_sesion.empty else 0.0

# Calculo de Acumulado Semanal (ultimos 7 dias)
fecha_inicio_sem = fecha_sel - timedelta(days=6)
df_sem = df_master[(df_master['Fecha'] >= fecha_inicio_sem) & (df_master['Fecha'] <= fecha_sel) & (df_master['Valido_Media'] == True)]
if pos_sel != "Equipo Completo":
    df_sem = df_sem[df_sem['Posicion'] == pos_sel]

weekly_sums = {}
for metrica in ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels']:
    if not df_sem.empty:
        daily_means = df_sem.groupby('Fecha')[metrica].mean()
        weekly_sums[metrica] = daily_means.sum()
    else:
        weekly_sums[metrica] = 0.0

# =============================================================================
# 6. PINTAR LOS BULLET CHARTS ESTILO PROFESIONAL
# =============================================================================
st.markdown("### 📊 Metrics Summary vs Match Target")

def pintar_bullet(metrica, nombre_mostrar, row_col):
    val = medias_sesion.get(metrica, 0)
    target = target_refs.get(metrica, 0)
    accum = weekly_sums.get(metrica, 0)
    
    # Textos matemáticos
    pct_sesion = (val / target * 100) if target > 0 else 0
    multiplier_sem = (accum / target) if target > 0 else 0
    
    texto_val = f"{val:.1f} ({pct_sesion:.0f}%)" if val < 100 else f"{val:.0f} ({pct_sesion:.0f}%)"
    str_acumulado = f"Acumulado semana: {multiplier_sem:.1f}x Partido" if target > 0 else "Acumulado semana: Sin Ref."
    
    max_range = max(val, target) * 1.2 if max(val, target) > 0 else 10
    
    fig = go.Figure()
    
    # 1. Barra de fondo (gris)
    fig.add_trace(go.Bar(
        x=[max_range], y=["1"], orientation='h',
        marker=dict(color="rgba(255,255,255,0.1)"),
        hoverinfo="none", width=0.6
    ))
    
    # 2. Barra de valor (Naranja oscuro para contraste) con % incluido
    fig.add_trace(go.Bar(
        x=[val], y=["1"], orientation='h',
        marker=dict(color="#B35900"), 
        text=[texto_val], 
        textposition='auto', 
        insidetextanchor='end', 
        textfont=dict(color="white", size=18, family="Arial Black"),
        hoverinfo="x", width=0.6
    ))
    
    # 3. Línea roja (Target)
    if target > 0:
        fig.add_shape(
            type="line",
            x0=target, x1=target,
            y0=-0.4, y1=0.4,
            line=dict(color="red", width=4)
        )

    fig.update_layout(
        barmode='overlay',
        height=65, 
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        xaxis=dict(range=[0, max_range], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    
    with row_col:
        st.markdown(f"<p style='margin-bottom:0px; font-size:16px; color:white; font-weight:bold;'>{nombre_mostrar}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-bottom:5px; font-size:12px; color:#A0AEC0;'>{str_acumulado}</p>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"bullet_{metrica}")

# Fila 1
r1_1, r1_2, r1_3, r1_4 = st.columns(4)
pintar_bullet('Dist_Total', 'Total Distance (m)', r1_1)
pintar_bullet('Dist_18', 'Distance > 18 km/h (m)', r1_2)
pintar_bullet('Dist_25', 'Distance > 25 km/h (m)', r1_3)
pintar_bullet('Dist_28', 'Distance > 28 km/h (m)', r1_4)

# Fila 2
r2_1, r2_2, r2_3, r2_4 = st.columns(4)
pintar_bullet('Sprints', 'Total Sprints', r2_1)
pintar_bullet('Accels', 'Accelerations', r2_2)
pintar_bullet('Decels', 'Decelerations', r2_3)

# =============================================================================
# 7. TABLA DE ANÁLISIS INDIVIDUAL POR POSICIÓN (MACRO Y SUB-COLUMNAS)
# =============================================================================
st.markdown("---")
st.markdown("### 🧑‍🤝‍🧑 Análisis Individual (Z-Score y Referencias)")

# Definir las métricas clave que vamos a meter en la tabla
metricas_tabla = {
    'Dist_Total': 'Dist. Total',
    'Dist_25': 'Dist. >25',
    'Sprints': 'Sprints',
    'RPE_G': 'RPE'
}

datos_tabla = []
# Filtramos la sesión actual y ordenamos por posición para hacer los "bloques"
df_sesion_tabla = df_master[df_master['Fecha'] == fecha_sel].sort_values(['Posicion', 'Nombre'])

for _, row in df_sesion_tabla.iterrows():
    jugador = row['Nombre']
    pos = row['Posicion']
    
    # Histórico del jugador (solo los días que tiene datos) hasta la fecha seleccionada
    df_hist_jugador = df_master[(df_master['Nombre'] == jugador) & (df_master['Fecha'] <= fecha_sel)].sort_values('Fecha')
    
    # Tomamos solo las últimas 28 SESIONES REALES CON DATOS
    df_hist_28 = df_hist_jugador.tail(28)
    
    fila = {'Posición': pos, 'Jugador': jugador}
    
    for metrica_col, metrica_nombre in metricas_tabla.items():
        val_sesion = row[metrica_col]
        target_part = target_refs.get(metrica_col, 0)
        
        # 1. Sesión (vs Partido)
        pct_partido = (val_sesion / target_part * 100) if target_part > 0 else 0
        
        # 2. Z-Score (Media móvil 28 sesiones)
        if len(df_hist_28) > 2:
            media_28 = df_hist_28[metrica_col].mean()
            std_28 = df_hist_28[metrica_col].std()
            z_score = (val_sesion - media_28) / std_28 if std_28 > 0 else 0
        else:
            z_score = 0
            
        # Nombres de las sub-columnas combinando la Macro-Métrica
        fila[f"{metrica_nombre} | Sesión"] = val_sesion
        fila[f"{metrica_nombre} | % Partido"] = pct_partido
        fila[f"{metrica_nombre} | Z-Score"] = z_score

    datos_tabla.append(fila)

if datos_tabla:
    df_resumen = pd.DataFrame(datos_tabla)
    
    # Agrupamos por Posición para que visualmente se vea en bloques (como en tu foto)
    df_resumen.set_index(['Posición', 'Jugador'], inplace=True)
    
    # Función para pintar los Z-Scores de rojo si superan el umbral 2 o se acercan
    def resaltar_alertas(val):
        try:
            v = float(val)
            if v > 2.0: return 'background-color: #8B0000; color: white; font-weight: bold;' # Rojo oscuro (Peligro)
            elif v > 1.5: return 'background-color: #E74C3C; color: white;' # Rojo claro (Alerta / Se aproxima)
            elif v < -2.0: return 'background-color: #1F618D; color: white;' # Azul (Sub-carga severa)
            return ''
        except:
            return ''

    # Aplicar el estilo solo a las columnas de Z-Score y formatear decimales
    cols_zscore = [c for c in df_resumen.columns if 'Z-Score' in c]
    
    # Formateo visual
    formato_columnas = {c: "{:.1f}" for c in df_resumen.columns}
    for c in df_resumen.columns:
        if '% Partido' in c: formato_columnas[c] = "{:.0f}%"
        if 'Z-Score' in c: formato_columnas[c] = "{:.2f}"
        if 'Dist. Total | Sesión' in c: formato_columnas[c] = "{:.0f}"

    df_estilado = df_resumen.style.map(resaltar_alertas, subset=cols_zscore).format(formato_columnas)
    
    st.dataframe(df_estilado, use_container_width=True, height=600)
else:
    st.info("No hay datos individuales para mostrar en esta fecha.")