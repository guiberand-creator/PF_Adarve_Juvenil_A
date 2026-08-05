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
# 2. MOTOR DE EXTRACCIÓN DE DATOS 
# =============================================================================
@st.cache_data(ttl=10)
def obtener_rpe_maestro():
    sheet_id = "1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s" 
    gid = "1785642271"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df_rpe = pd.read_csv(url_csv)
        df_rpe['Fecha'] = pd.to_datetime(df_rpe['Marca temporal'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_rpe['Nombre_Cruce'] = df_rpe['Nombre y apellidos'].fillna('Anónimo').astype(str).str.strip().str.lower()
        
        df_rpe['Tipo de Sesión'] = df_rpe['Tipo de sesión'].fillna('Entreno').astype(str).str.strip()
        df_rpe['Minutos_RPE'] = pd.to_numeric(df_rpe['Minutos entreno/partido'], errors='coerce').fillna(0)
        
        col_c = [c for c in df_rpe.columns if 'CARDIO' in str(c).upper()][0]
        col_m = [c for c in df_rpe.columns if 'MUSCULAR' in str(c).upper()][0]
        df_rpe['RPE_G'] = (pd.to_numeric(df_rpe[col_c], errors='coerce').fillna(0) + pd.to_numeric(df_rpe[col_m], errors='coerce').fillna(0)) / 2
        
        df_sesion_dia = df_rpe.groupby('Fecha')['Tipo de Sesión'].apply(lambda x: x.mode()[0] if not x.mode().empty else 'Entreno').reset_index()
        df_sesion_dia.rename(columns={'Tipo de Sesión': 'Tipo_Dia_Oficial'}, inplace=True)
        
        df_rpe = pd.merge(df_rpe, df_sesion_dia, on='Fecha', how='left')
        return df_rpe[['Fecha', 'Nombre_Cruce', 'Tipo_Dia_Oficial', 'Minutos_RPE', 'RPE_G']]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_archivos_gps():
    ruta_gps = os.path.join("data", "GPS")
    if not os.path.exists(ruta_gps): return pd.DataFrame()
        
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
            col_28 = buscar_col(['> 28', '>28']) 
            col_spr = buscar_col(['nº sprints', 'sprints'])
            col_acc = buscar_col(['aceleraciones', 'accel', 'nº aceleraciones'])
            col_dec = buscar_col(['desaceleraciones', 'decel', 'nº desaceleraciones'])
            col_acc_max = buscar_col(['ac. max', 'acc. max'])
            col_dec_max = buscar_col(['dec. max', 'desac. max'])
            col_vmax = buscar_col(['v. max', 'v.max', 'top speed'])
            col_pload = buscar_col(['player load', 'carga'])
            
            if not col_fecha or not col_nombre: continue
            
            df_limpio = pd.DataFrame()
            def fix_num(val):
                try: return float(str(val).replace(',', '.'))
                except: return 0.0
            
            df_limpio['Fecha'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            df_limpio['Nombre'] = df_temp[col_nombre].astype(str).str.strip()
            df_limpio['Nombre_Cruce'] = df_limpio['Nombre'].str.lower()
            df_limpio['Posicion'] = df_temp[col_pos].astype(str) if col_pos else 'Sin Posición'
            df_limpio['Duracion_GPS'] = df_temp[col_dur].apply(fix_num) if col_dur else 60.0
            
            df_limpio['Dist_Total'] = df_temp[col_dt].apply(fix_num) if col_dt else 0.0
            df_limpio['Dist_18'] = df_temp[col_18].apply(fix_num) if col_18 else 0.0
            df_limpio['Dist_25'] = df_temp[col_25].apply(fix_num) if col_25 else 0.0
            df_limpio['Dist_28'] = df_temp[col_28].apply(fix_num) if col_28 else 0.0
            df_limpio['Sprints'] = df_temp[col_spr].apply(fix_num) if col_spr else 0.0
            df_limpio['Accels'] = df_temp[col_acc].apply(fix_num) if col_acc else 0.0
            df_limpio['Decels'] = df_temp[col_dec].apply(fix_num) if col_dec else 0.0
            df_limpio['Acc_Max'] = df_temp[col_acc_max].apply(fix_num) if col_acc_max else 0.0
            df_limpio['Dec_Max'] = df_temp[col_dec_max].apply(fix_num) if col_dec_max else 0.0
            df_limpio['Top_Speed'] = df_temp[col_vmax].apply(fix_num) if col_vmax else 0.0
            df_limpio['Player_Load'] = df_temp[col_pload].apply(fix_num) if col_pload else 0.0

            lista_dfs.append(df_limpio.dropna(subset=['Fecha']))
        except: continue
            
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
# 3. PROCESAMIENTO, CRUCE Y MODELO DE JUEGO (PERIODIZACIÓN)
# =============================================================================
df_rpe = obtener_rpe_maestro()
df_gps = cargar_archivos_gps()

if df_gps.empty:
    st.info("🚧 Aún no hay archivos de GPS en la carpeta `data/GPS`.")
    st.stop()

if not df_rpe.empty:
    df_master = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='left')
    df_master['Tipo_Dia_Oficial'] = df_master['Tipo_Dia_Oficial'].fillna('Entreno')
    df_master['RPE_G'] = df_master['RPE_G'].fillna(5) 
    df_master['Minutos_RPE'] = df_master['Minutos_RPE'].fillna(df_master['Duracion_GPS'])
else:
    df_master = df_gps.copy()
    df_master['Tipo_Dia_Oficial'] = 'Entreno'
    df_master['RPE_G'] = 5
    df_master['Minutos_RPE'] = df_master['Duracion_GPS']

df_master = df_master.sort_values(by='Fecha')
ultimos_mins_partido = {}
validez = []
jugo_mas_60 = []

for _, row in df_master.iterrows():
    tipo = str(row['Tipo_Dia_Oficial']).lower()
    mins = row['Minutos_RPE']
    jugador = row['Nombre_Cruce']
    
    if 'partido' in tipo:
        ultimos_mins_partido[jugador] = mins
        validez.append(mins >= 60)
        jugo_mas_60.append(mins >= 60)
    elif '+1' in tipo or '+2' in tipo:
        ult_mins = ultimos_mins_partido.get(jugador, 0)
        validez.append(ult_mins < 60)
        jugo_mas_60.append(ult_mins >= 60)
    else:
        validez.append(True)
        jugo_mas_60.append(False)

df_master['Valido_Media'] = validez
df_master['Jugo_60_Ultimo_Partido'] = jugo_mas_60
df_master['Carga_UA'] = (df_master['Dist_Total'] + (df_master['Dist_18'] * 1.5) + df_master['Dist_25']) * df_master['RPE_G']
fechas_disp = sorted(df_master['Fecha'].unique(), reverse=True)

# --- DICCIONARIO DE PERIODIZACIÓN ---
def get_target_pct(metrica, tipo_dia, jugo_60):
    t = str(tipo_dia).lower()
    if 'partido' in t: return 100
    is_plus = '+1' in t or '+2' in t
    
    if metrica == 'Dist_Total':
        if '-4' in t: return 50
        if '-3' in t: return 62.5
        if '-2' in t: return 25
        if '-1' in t: return 35
        if is_plus: return 25 if jugo_60 else 60
    elif metrica == 'Dist_18':
        if '-4' in t: return 60
        if '-3' in t: return 57.5
        if '-2' in t or '-1' in t: return 25
        if is_plus: return 40 if jugo_60 else 45
    elif metrica == 'Dist_25':
        if '-4' in t: return 10
        if '-3' in t: return 70
        if '-2' in t: return 10
        if '-1' in t: return 2.5
        if is_plus: return 0 if jugo_60 else 45
    elif metrica in ['Accels', 'Decels']:
        if '-4' in t: return 65
        if '-3' in t: return 57.5
        if '-2' in t: return 30
        if '-1' in t: return 15
        if is_plus: return 30 if jugo_60 else 65 
    elif metrica == 'Player_Load':
        if '-4' in t: return 60
        if '-3' in t: return 57.5
        if '-2' in t: return 30
        if '-1' in t: return 25
        if is_plus: return 25 if jugo_60 else 60
    return 50

df_partidos = df_master[df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido', na=False)]
df_partidos = df_partidos[df_partidos['Valido_Media'] == True]
metricas_todas = ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels', 'Acc_Max', 'Dec_Max', 'Top_Speed', 'Player_Load']

fallbacks_profesionales = {
    'Dist_Total': 10000, 'Dist_18': 800, 'Dist_25': 250, 'Dist_28': 100, 
    'Sprints': 20, 'Accels': 50, 'Decels': 50, 'Acc_Max': 4.5, 'Dec_Max': 4.5, 
    'Top_Speed': 31, 'Player_Load': 1000
}

target_refs_global = {}
if not df_partidos.empty:
    ultimos_4_fechas = sorted(df_partidos['Fecha'].unique(), reverse=True)[:4]
    df_ult_4 = df_partidos[df_partidos['Fecha'].isin(ultimos_4_fechas)]
    for m in metricas_todas: 
        target_refs_global[m] = (df_ult_4[m].mean() + df_ult_4[m].max()) / 2 if not df_ult_4.empty else fallbacks_profesionales[m]
else:
    for m in metricas_todas: target_refs_global[m] = fallbacks_profesionales[m]

for m in metricas_todas:
    if target_refs_global[m] == 0: target_refs_global[m] = fallbacks_profesionales[m]

for m in metricas_todas:
    df_master[f'Target_{m}'] = df_master.apply(lambda r: target_refs_global[m] * (get_target_pct(m, r['Tipo_Dia_Oficial'], r['Jugo_60_Ultimo_Partido']) / 100), axis=1)

# =============================================================================
# 4. INTERFAZ: CABECERA Y FILTROS
# =============================================================================
st.markdown("""
    <div style="margin-bottom: 5px;">
        <h1 style="margin-bottom: 0px; padding-bottom: 0px;">SESSION DASHBOARD (GPS)</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Evolución táctica, referencias de partido y fatiga neuromuscular.</p>
    </div>
""", unsafe_allow_html=True)

col_f1, col_f2 = st.columns(2)
with col_f1: 
    fecha_sel = st.selectbox("📅 Select Date:", fechas_disp)
with col_f2:
    posiciones_validas = [str(p) for p in df_master['Posicion'].unique() if str(p).lower() != 'nan']
    pos_sel = st.selectbox("⚽ Posición:", ["Equipo Completo"] + sorted(posiciones_validas))

if pos_sel == "Equipo Completo": df_sesion = df_master[df_master['Fecha'] == fecha_sel]
else: df_sesion = df_master[(df_master['Fecha'] == fecha_sel) & (df_master['Posicion'] == pos_sel)]

# --- SISTEMA DE ALERTAS INDEPENDIENTES (MICROCICLO 7 DÍAS) ---
fecha_datetime = datetime.strptime(fecha_sel, '%Y-%m-%d').date()
fecha_inicio_sem = fecha_datetime - timedelta(days=6)
df_sem = df_master[(df_master['Fecha'] >= fecha_inicio_sem.strftime('%Y-%m-%d')) & (df_master['Fecha'] <= fecha_sel)]

fecha_inicio_vmax = fecha_datetime - timedelta(days=28)
df_28d = df_master[(df_master['Fecha'] >= fecha_inicio_vmax.strftime('%Y-%m-%d')) & (df_master['Fecha'] <= fecha_sel)]
vmax_hist = df_28d.groupby('Nombre')['Top_Speed'].max().reset_index().rename(columns={'Top_Speed': 'Vmax_4_semanas'})

df_sem = df_sem.merge(vmax_hist, on='Nombre', how='left')
df_sem['Pct_Vmax'] = np.where(df_sem['Vmax_4_semanas'] > 0, (df_sem['Top_Speed'] / df_sem['Vmax_4_semanas']) * 100, 0)
df_sem['Hit_90'] = df_sem['Pct_Vmax'] >= 90

metricas_alerta = {
    'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18 km/h', 'Dist_25': 'Dist. >25 km/h', 
    'Accels': 'Aceleraciones', 'Decels': 'Desaceleraciones', 'Player_Load': 'Player Load'
}

jugadores_vmax_peligro = []
alertas_metricas = {k: [] for k in metricas_alerta.keys()}

for jug in df_sem['Nombre'].unique():
    df_j = df_sem[df_sem['Nombre'] == jug]
    hits_vmax = df_j['Hit_90'].sum()
    if hits_vmax < 2:
        jugadores_vmax_peligro.append((jug, hits_vmax))
        
    for m_key in metricas_alerta.keys():
        target_sum = df_j[f'Target_{m_key}'].sum()
        real_sum = df_j[m_key].sum()
        if target_sum > 0 and (real_sum / target_sum) < 0.90:
            pct_logrado = (real_sum / target_sum) * 100
            alertas_metricas[m_key].append((jug, pct_logrado))

total_avisos = len(jugadores_vmax_peligro) + sum(len(lista) for lista in alertas_metricas.values())

st.markdown("<br>", unsafe_allow_html=True)
with st.expander(f"🚨 ALERTAS MICROCICLO (Últimos 7 días) - {total_avisos} Avisos de Subcarga", expanded=False):
    
    # Fila 1 de Cajas
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        st.markdown("**🏃‍♂️ Riesgo Isquios (Vmax)**")
        if jugadores_vmax_peligro:
            for j, hits in jugadores_vmax_peligro: st.error(f"• {j} ({hits} veces)")
        else: st.success("Todo el equipo OK")
    with col_a2:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Dist_Total']}**")
        if alertas_metricas['Dist_Total']:
            for j, pct in alertas_metricas['Dist_Total']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")
    with col_a3:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Dist_18']}**")
        if alertas_metricas['Dist_18']:
            for j, pct in alertas_metricas['Dist_18']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # Fila 2 de Cajas
    col_a4, col_a5, col_a6 = st.columns(3)
    with col_a4:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Dist_25']}**")
        if alertas_metricas['Dist_25']:
            for j, pct in alertas_metricas['Dist_25']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")
    with col_a5:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Accels']}**")
        if alertas_metricas['Accels']:
            for j, pct in alertas_metricas['Accels']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")
    with col_a6:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Decels']}**")
        if alertas_metricas['Decels']:
            for j, pct in alertas_metricas['Decels']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # Fila 3 de Cajas (Player Load centrado)
    col_a7, col_a8, col_a9 = st.columns(3)
    with col_a7:
        st.markdown(f"**🔋 Subcarga {metricas_alerta['Player_Load']}**")
        if alertas_metricas['Player_Load']:
            for j, pct in alertas_metricas['Player_Load']: st.warning(f"• {j} ({pct:.0f}%)")
        else: st.success("Todo el equipo OK")

st.markdown("---")

tipo_sesion = str(df_master[df_master['Fecha'] == fecha_sel]['Tipo_Dia_Oficial'].iloc[0]).upper()
duracion_sesion = int(df_master[df_master['Fecha'] == fecha_sel]['Duracion_GPS'].max()) if not df_sesion.empty else 0

# --- HISTÓRICO Y VMAX DEL DÍA ---
df_hist_eq = df_28d[df_28d['Valido_Media']==True].groupby('Fecha').agg({'Carga_UA': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()
fig_hist = go.Figure(go.Bar(
    x=df_hist_eq['Fecha'], y=df_hist_eq['Carga_UA'], 
    marker_color=['#FF9F1C' if 'partido' in str(t).lower() else '#555555' for t in df_hist_eq['Tipo_Dia_Oficial']], 
    text=['P' if 'partido' in str(t).lower() else 'Tr' for t in df_hist_eq['Tipo_Dia_Oficial']], textposition='outside', textfont=dict(color="white", size=12)
))
fig_hist.update_layout(template="plotly_dark", height=150, margin=dict(l=0, r=0, t=20, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

df_vmax_hoy = df_sesion.merge(vmax_hist, on='Nombre', how='left')
df_vmax_hoy['Porcentaje_Vmax'] = np.where(df_vmax_hoy['Vmax_4_semanas']>0, (df_vmax_hoy['Top_Speed']/df_vmax_hoy['Vmax_4_semanas'])*100, 0)
media_vmax_sesion = df_vmax_hoy['Porcentaje_Vmax'].mean() if not df_vmax_hoy.empty else 0
alcanzan_90 = df_vmax_hoy[df_vmax_hoy['Porcentaje_Vmax'] >= 90].sort_values(by='Porcentaje_Vmax', ascending=False)

# PINTAR CABECERA
c_dur, c_hist, c_info = st.columns([1.5, 3, 2])
with c_dur:
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Session duration</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color:white; font-size:55px; margin-top:0; margin-bottom:0px; line-height: 1;'>{duracion_sesion} min</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:white; font-size:55px; font-weight:normal; margin-top:-10px; margin-bottom:0px; line-height: 1;'>TIPO: {tipo_sesion}</p>", unsafe_allow_html=True)
with c_hist:
    st.markdown(f"<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Last 28 days training schedule</p>", unsafe_allow_html=True)
    st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
with c_info:
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Velocidad Máxima HOY (>90%)</p>", unsafe_allow_html=True)
    c_vmax = "#2ECC71" if media_vmax_sesion >= 90 else "#F1C40F" if media_vmax_sesion >= 85 else "#E74C3C"
    st.markdown(f"<h2 style='color:{c_vmax}; margin-top:0;'>{media_vmax_sesion:.1f}% <span style='font-size:14px; color:#A0AEC0; font-weight:normal;'>media equipo</span></h2>", unsafe_allow_html=True)
    with st.expander("👁️ Jugadores al 90% hoy"):
        if not alcanzan_90.empty:
            for _, r in alcanzan_90.iterrows(): st.markdown(f"<span style='color:#2ECC71; font-size:14px;'>• {r['Nombre']} ({r['Porcentaje_Vmax']:.1f}%)</span>", unsafe_allow_html=True)
        else: st.caption("Ninguno")

# =============================================================================
# 5. BULLET CHARTS (MEDIA DE SESIÓN VS OBJETIVO PROGRAMADO)
# =============================================================================
st.markdown("### 📊 Session Mean vs Target Programado")

medias_sesion = {m: df_sesion[m].mean() if not df_sesion.empty else 0.0 for m in metricas_todas}
target_programado = {m: df_sesion[f'Target_{m}'].mean() if not df_sesion.empty else 0.0 for m in metricas_todas}

def pintar_bullet(metrica, nombre_mostrar, row_col):
    val = medias_sesion.get(metrica, 0)
    target = target_programado.get(metrica, 0)
    pct_sesion = (val / target * 100) if target > 0 else 0
    texto_val = f"{val:.1f} ({pct_sesion:.0f}%)" if val < 100 else f"{val:.0f} ({pct_sesion:.0f}%)"
    max_range = max(val, target) * 1.2 if max(val, target) > 0 else 10
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[max_range], y=["1"], orientation='h', marker=dict(color="rgba(255,255,255,0.1)"), hoverinfo="none", width=0.6))
    if val > 0: fig.add_trace(go.Bar(x=[val], y=["1"], orientation='h', marker=dict(color="#B35900"), text=[texto_val], textposition='auto', insidetextanchor='end', textfont=dict(color="white", size=18, family="Arial Black"), hoverinfo="x", width=0.6))
    if target > 0: fig.add_shape(type="line", x0=target, x1=target, y0=-0.4, y1=0.4, line=dict(color="red", width=4))
    fig.update_layout(barmode='overlay', height=65, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, xaxis=dict(range=[0, max_range], showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False))
    
    with row_col:
        st.markdown(f"<p style='margin-bottom:5px; font-size:16px; color:white; font-weight:bold;'>{nombre_mostrar}</p>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"bullet_{metrica}")

r1_1, r1_2, r1_3, r1_4 = st.columns(4)
pintar_bullet('Dist_Total', 'Total Distance (m)', r1_1)
pintar_bullet('Dist_18', 'Distance > 18 km/h', r1_2)
pintar_bullet('Dist_25', 'Distance > 25 km/h', r1_3)
pintar_bullet('Dist_28', 'Distance > 28 km/h', r1_4)
r2_1, r2_2, r2_3, r2_4 = st.columns(4)
pintar_bullet('Sprints', 'Total Sprints', r2_1)
pintar_bullet('Accels', 'Accelerations', r2_2)
pintar_bullet('Decels', 'Decelerations', r2_3)
pintar_bullet('Player_Load', 'Player Load', r2_4)

# =============================================================================
# 6. TABLA INDIVIDUAL (OBJETIVOS PERSONALIZADOS)
# =============================================================================
st.markdown("---")
st.markdown("### 🧑‍🤝‍🧑 Análisis Individual vs Objetivo Periodizado")

metricas_tabla = {'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18', 'Dist_25': 'Dist. >25', 'Dist_28': 'Dist. >28', 'Sprints': 'Sprints', 'Accels': 'Acel.', 'Decels': 'Desac.', 'Acc_Max': 'Ac. Máx', 'Dec_Max': 'Dec. Máx', 'Top_Speed': 'V. Máx', 'Player_Load': 'Load'}
df_sesion_tabla = df_master[df_master['Fecha'] == fecha_sel].copy()

orden_tactico = {'defensa central': 1, 'defensa lateral': 2, 'mediocentro': 3, 'mediapunta': 4, 'extremo': 5, 'delantero': 6}
df_sesion_tabla['Peso_Pos'] = df_sesion_tabla['Posicion'].astype(str).str.lower().str.strip().map(orden_tactico).fillna(99)
df_sesion_tabla = df_sesion_tabla.sort_values(['Peso_Pos', 'Nombre'])

if not df_sesion_tabla.empty:
    escalas_max = {m: max(df_sesion_tabla[m].max(), df_sesion_tabla[f'Target_{m}'].max()) * 1.2 if max(df_sesion_tabla[m].max(), df_sesion_tabla[f'Target_{m}'].max()) > 0 else 10 for m in metricas_tabla}

    def dibujar_barra(valor, target, max_val, es_decimal):
        if max_val == 0: max_val = 1
        pct_fill, pct_target = min((valor/max_val)*100, 100), min((target/max_val)*100, 100)
        t_val = f"{valor:.1f}" if es_decimal else f"{valor:.0f}"
        
        c_barra = "#E74C3C" if (target > 0 and valor >= target * 0.90) else "#3498DB"
        c_linea = "#F1C40F" if c_barra == "#E74C3C" else "#E74C3C"
        
        return f"""
        <div style="position:relative; width:100%; min-width:50px; max-width:90px; height:18px; background-color:rgba(255,255,255,0.1); border-radius:2px; margin:0 auto; overflow:visible;">
            <div style="position:absolute; left:0; top:0; height:100%; width:{pct_fill}%; background-color:{c_barra}; border-radius:2px;"></div>
            <div style="position:absolute; left:{pct_target}%; top:-2px; height:22px; width:2px; background-color:{c_linea}; z-index:2;"></div>
            <div style="position:absolute; left:4px; top:1px; font-size:11px; font-weight:bold; color:white; z-index:3; text-shadow:1px 1px 1px black;">{t_val}</div>
        </div>
        """

    html = """
    <div style="overflow-x: auto; padding-bottom: 20px;">
    <table style="border-collapse: collapse; text-align: center; font-family: sans-serif; font-size: 12px; width: 100%;">
        <thead><tr style="background-color: rgba(0,0,0,0.3); border-bottom: 2px solid #555;">
        <th style="padding: 10px;">POSICIÓN</th><th style="padding: 10px; text-align:left;">JUGADOR</th>
    """
    for _, nombre_m in metricas_tabla.items(): html += f"<th colspan='3' style='padding:10px; border-left:1px solid #444;'>{nombre_m}</th>"
    html += "<th style='padding: 10px; border-left: 1px solid #444;'>RPE</th></tr>"
    html += "<tr style='border-bottom: 1px solid #555; font-size: 10px; color: #A0AEC0;'><th></th><th></th>"
    for _ in metricas_tabla: html += "<th style='padding:5px; border-left:1px solid #444;'>Sesión(Ref)</th><th>% Obj</th><th>Z-Score</th>"
    html += "<th></th></tr></thead><tbody>"

    pos_counts = df_sesion_tabla['Posicion'].value_counts(dropna=False).to_dict()
    pos_actual = ""
    
    for _, row in df_sesion_tabla.iterrows():
        jugador, pos, rpe_val = row['Nombre'], row['Posicion'], row['RPE_G']
        df_h = df_master[(df_master['Nombre'] == jugador) & (df_master['Fecha'] <= fecha_sel)].sort_values('Fecha').tail(28)
        html += "<tr style='border-bottom: 1px solid #333;'>"
        
        if pos != pos_actual:
            html += f"<td rowspan='{pos_counts.get(pos,1)}' style='vertical-align:middle; font-weight:bold; color:#E67E22; text-transform:uppercase; border-right:1px solid #444; border-bottom:2px solid #555;'>{pos}</td>"
            pos_actual = pos
        html += f"<td style='padding:8px; text-align:left; white-space:nowrap;'>{jugador}</td>"
        
        for m, _ in metricas_tabla.items():
            val, target = row[m], row[f'Target_{m}']
            pct = (val / target * 100) if target > 0 else 0
            z = (val - df_h[m].mean()) / df_h[m].std() if len(df_h) > 2 and df_h[m].std() > 0 else 0
            
            es_dec = m in ['Dist_18', 'Dist_25', 'Dist_28', 'Acc_Max', 'Dec_Max', 'Top_Speed']
            c_z = "#8B0000" if z > 2 else "#E74C3C" if z > 1.5 else "#1F618D" if z < -2 else "transparent"
            
            html += f"<td style='padding:5px; border-left:1px solid #333;'>{dibujar_barra(val, target, escalas_max[m], es_dec)}</td>"
            html += f"<td style='padding:5px; color:{'#2ECC71' if pct>=100 else '#CCC'};'>{pct:.0f}%</td>"
            html += f"<td style='padding:5px; background-color:{c_z}; border-radius:3px; color:{'white' if c_z!='transparent' else '#CCC'};'>{z:.2f}</td>"
        
        html += f"<td style='padding:5px; border-left:1px solid #444; font-weight:bold; background-color:{'#E74C3C' if rpe_val>=8 else 'transparent'};'>{rpe_val:.1f}</td></tr>"
        
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("No hay datos para esta fecha.")