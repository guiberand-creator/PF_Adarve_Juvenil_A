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
# 3. PROCESAMIENTO Y MODELO DE JUEGO (PERIODIZACIÓN POR RANGOS)
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

def get_target_range(metrica, tipo_dia, jugo_60):
    t = str(tipo_dia).lower()
    if 'partido' in t: return (100, 100)
    is_plus = '+1' in t or '+2' in t
    is_minus = '-4' in t or '-3' in t or '-2' in t or '-1' in t
    
    if not (is_plus or is_minus): return (0, 0)
    
    if metrica == 'Dist_Total':
        if '-4' in t: return (45, 55)
        if '-3' in t: return (55, 70)
        if '-2' in t: return (20, 30)
        if '-1' in t: return (30, 40)
        if is_plus: return (20, 30) if jugo_60 else (55, 65)
    elif metrica == 'Dist_18':
        if '-4' in t: return (55, 65)
        if '-3' in t: return (50, 65)
        if '-2' in t or '-1' in t: return (20, 30)
        if is_plus: return (0, 40) if jugo_60 else (40, 50)
    elif metrica == 'Dist_25':
        if '-4' in t: return (0, 20)
        if '-3' in t: return (50, 90)
        if '-2' in t: return (5, 15)
        if '-1' in t: return (0, 5)
        if is_plus: return (0, 10) if jugo_60 else (40, 50)
    elif metrica in ['Accels', 'Decels']:
        if '-4' in t: return (60, 70)
        if '-3' in t: return (50, 65)
        if '-2' in t: return (20, 40)
        if '-1' in t: return (10, 20)
        if is_plus: return (10, 30) if jugo_60 else (60, 70) 
    elif metrica == 'Player_Load':
        if '-4' in t: return (55, 65)
        if '-3' in t: return (50, 65)
        if '-2' in t: return (20, 40)
        if '-1' in t: return (20, 30)
        if is_plus: return (20, 30) if jugo_60 else (55, 65)
    return (0, 0) 

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
    if m in ['Dist_28', 'Sprints']:
        df_master[f'Target_Min_Pct_{m}'] = 100
        df_master[f'Target_Max_Pct_{m}'] = 100
        df_master[f'Target_Min_{m}'] = target_refs_global[m]
        df_master[f'Target_Max_{m}'] = target_refs_global[m]
        df_master[f'Target_{m}'] = target_refs_global[m]
    elif m in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
        df_master[f'Target_Min_Pct_{m}'] = 0
        df_master[f'Target_Max_Pct_{m}'] = 0
        df_master[f'Target_Min_{m}'] = 0
        df_master[f'Target_Max_{m}'] = 0
        df_master[f'Target_{m}'] = 0
    else:
        df_master[f'Target_Min_Pct_{m}'] = df_master.apply(lambda r: get_target_range(m, r['Tipo_Dia_Oficial'], r['Jugo_60_Ultimo_Partido'])[0], axis=1)
        df_master[f'Target_Max_Pct_{m}'] = df_master.apply(lambda r: get_target_range(m, r['Tipo_Dia_Oficial'], r['Jugo_60_Ultimo_Partido'])[1], axis=1)
        df_master[f'Target_Min_{m}'] = df_master.apply(lambda r: target_refs_global[m] * (r[f'Target_Min_Pct_{m}'] / 100), axis=1)
        df_master[f'Target_Max_{m}'] = df_master.apply(lambda r: target_refs_global[m] * (r[f'Target_Max_Pct_{m}'] / 100), axis=1)
        df_master[f'Target_{m}'] = df_master.apply(lambda r: target_refs_global[m] * (sum(get_target_range(m, r['Tipo_Dia_Oficial'], r['Jugo_60_Ultimo_Partido'])) / 200), axis=1)

# =============================================================================
# 4. INTERFAZ: CABECERA Y FILTROS INTERACTIVOS
# =============================================================================
st.markdown("""
    <div style="margin-bottom: 5px;">
        <h1 style="margin-bottom: 0px; padding-bottom: 0px;">SESSION DASHBOARD (GPS)</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Evolución táctica, referencias de partido y fatiga neuromuscular.</p>
    </div>
""", unsafe_allow_html=True)

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: 
    fecha_sel = st.selectbox("📅 Select Date:", fechas_disp)
with col_f2:
    posiciones_validas = [str(p) for p in df_master['Posicion'].unique() if str(p).lower() != 'nan']
    pos_sel = st.selectbox("⚽ Posición:", ["Equipo Completo"] + sorted(posiciones_validas))
with col_f3:
    if pos_sel == "Equipo Completo":
        jugadores_validos = sorted([str(j) for j in df_master['Nombre'].unique() if str(j).lower() != 'nan'])
    else:
        jugadores_validos = sorted([str(j) for j in df_master[df_master['Posicion'] == pos_sel]['Nombre'].unique() if str(j).lower() != 'nan'])
    jug_sel = st.selectbox("🏃 Jugador:", ["Todos"] + jugadores_validos)

# APLICAR FILTROS GLOBALES
df_sesion = df_master[df_master['Fecha'] == fecha_sel]
fecha_datetime = datetime.strptime(fecha_sel, '%Y-%m-%d').date()
df_fechas = pd.to_datetime(df_master['Fecha']).dt.date

# CÁLCULO DE MICROCICLO ACTUAL Y ANTERIOR
df_partidos_prev = df_master[(df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido')) & (df_fechas < fecha_datetime)]
if not df_partidos_prev.empty:
    last_match_date = pd.to_datetime(df_partidos_prev['Fecha']).dt.date.max()
    fecha_inicio_sem = last_match_date + timedelta(days=1)
    
    df_partidos_prev2 = df_partidos_prev[pd.to_datetime(df_partidos_prev['Fecha']).dt.date < last_match_date]
    if not df_partidos_prev2.empty:
        prev_match_date = pd.to_datetime(df_partidos_prev2['Fecha']).dt.date.max()
        fecha_inicio_sem_prev = prev_match_date + timedelta(days=1)
    else:
        fecha_inicio_sem_prev = last_match_date - timedelta(days=6)
    fecha_fin_sem_prev = last_match_date
else:
    fecha_inicio_sem = fecha_datetime - timedelta(days=6)
    fecha_inicio_sem_prev = fecha_inicio_sem - timedelta(days=7)
    fecha_fin_sem_prev = fecha_inicio_sem - timedelta(days=1)

df_sem = df_master[(df_fechas >= fecha_inicio_sem) & (df_fechas <= fecha_datetime)]
df_sem_prev = df_master[(df_fechas >= fecha_inicio_sem_prev) & (df_fechas <= fecha_fin_sem_prev)]

fecha_inicio_vmax = fecha_datetime - timedelta(days=28)
df_28d = df_master[(df_fechas >= fecha_inicio_vmax) & (df_fechas <= fecha_datetime)]

if pos_sel != "Equipo Completo":
    df_sesion = df_sesion[df_sesion['Posicion'] == pos_sel]
    df_sem = df_sem[df_sem['Posicion'] == pos_sel]
    df_sem_prev = df_sem_prev[df_sem_prev['Posicion'] == pos_sel]
    df_28d = df_28d[df_28d['Posicion'] == pos_sel]

if jug_sel != "Todos":
    df_sesion = df_sesion[df_sesion['Nombre'] == jug_sel]
    df_sem = df_sem[df_sem['Nombre'] == jug_sel]
    df_sem_prev = df_sem_prev[df_sem_prev['Nombre'] == jug_sel]
    df_28d = df_28d[df_28d['Nombre'] == jug_sel]

# --- 1. ALERTAS MICROCICLO ---
vmax_hist = df_28d.groupby('Nombre')['Top_Speed'].max().reset_index().rename(columns={'Top_Speed': 'Vmax_4_semanas'})
df_sem = df_sem.merge(vmax_hist, on='Nombre', how='left')
df_sem['Pct_Vmax'] = np.where(df_sem['Vmax_4_semanas'] > 0, (df_sem['Top_Speed'] / df_sem['Vmax_4_semanas']) * 100, 0)
df_sem['Hit_90'] = df_sem['Pct_Vmax'] >= 90

metricas_alerta = {
    'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18 km/h', 'Dist_25': 'Dist. >25 km/h', 
    'Accels': 'Aceleraciones', 'Decels': 'Desacel.', 'Player_Load': 'Player Load'
}

jugadores_vmax_peligro = []
alertas_metricas = {k: [] for k in metricas_alerta.keys()}

for jug in df_sem['Nombre'].unique():
    df_j = df_sem[df_sem['Nombre'] == jug]
    hits_vmax = df_j['Hit_90'].sum()
    if hits_vmax < 2:
        jugadores_vmax_peligro.append((jug, hits_vmax))
        
    for m_key in metricas_alerta.keys():
        expected_min = df_j[f'Target_Min_Pct_{m_key}'].sum()
        expected_max = df_j[f'Target_Max_Pct_{m_key}'].sum()
        actual_abs = df_j[m_key].sum()
        ref_partido = target_refs_global[m_key]
        actual_pct = (actual_abs / ref_partido * 100) if ref_partido > 0 else 0
        
        if expected_min > 0 and actual_pct < expected_min:
            texto_alerta = f"{actual_pct:.0f}% / {expected_min:.0f}-{expected_max:.0f}%"
            alertas_metricas[m_key].append((jug, texto_alerta))

total_avisos_micro = len(jugadores_vmax_peligro) + sum(len(lista) for lista in alertas_metricas.values())

st.markdown("<br>", unsafe_allow_html=True)
str_fechas_micro = f"Desde {fecha_inicio_sem.strftime('%d/%m')} hasta {fecha_datetime.strftime('%d/%m')}"
with st.expander(f"🚨 ALERTAS MICROCICLO ({str_fechas_micro}) - {total_avisos_micro} Avisos", expanded=False):
    cols_alertas = st.columns(7)
    def generar_lista_html(titulo, lista, es_vmax=False):
        html = f"<div style='font-size: 16px; margin-bottom: 8px; font-weight: bold; border-bottom: 1px solid #555; padding-bottom: 4px; color: white;'>{titulo}</div>"
        if not lista: html += "<div style='font-size: 15px; color: #2ECC71;'>✅ Todo OK</div>"
        else:
            color_texto = "#E74C3C" if es_vmax else "#F39C12"
            for item in lista:
                val_str = f"{item[1]}v" if es_vmax else item[1]
                html += f"<div style='font-size: 15px; color: {color_texto}; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{item[0]}'>• {item[0]} ({val_str})</div>"
        return html

    with cols_alertas[0]: st.markdown(generar_lista_html("🏃 Riesgo Vmax", jugadores_vmax_peligro, True), unsafe_allow_html=True)
    with cols_alertas[1]: st.markdown(generar_lista_html("🔋 Dist. Total", alertas_metricas['Dist_Total']), unsafe_allow_html=True)
    with cols_alertas[2]: st.markdown(generar_lista_html("🔋 Dist. >18", alertas_metricas['Dist_18']), unsafe_allow_html=True)
    with cols_alertas[3]: st.markdown(generar_lista_html("🔋 Dist. >25", alertas_metricas['Dist_25']), unsafe_allow_html=True)
    with cols_alertas[4]: st.markdown(generar_lista_html("🔋 Acel.", alertas_metricas['Accels']), unsafe_allow_html=True)
    with cols_alertas[5]: st.markdown(generar_lista_html("🔋 Desac.", alertas_metricas['Decels']), unsafe_allow_html=True)
    with cols_alertas[6]: st.markdown(generar_lista_html("🔋 Load", alertas_metricas['Player_Load']), unsafe_allow_html=True)

# --- 2. ALERTAS MESOCICLO ---
alertas_meso = []
metricas_meso = {
    'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18 km/h', 'Dist_25': 'Dist. >25 km/h', 'Dist_28': 'Dist. >28 km/h',
    'Sprints': 'Sprints', 'Accels': 'Aceleraciones', 'Decels': 'Desacel.', 'Player_Load': 'Player Load'
}

for m_key, m_name in metricas_meso.items():
    m0_actual = df_sem[m_key].sum()
    m0_tmin = df_sem[f'Target_Min_{m_key}'].sum()
    m0_tmax = df_sem[f'Target_Max_{m_key}'].sum()
    
    m1_actual = df_sem_prev[m_key].sum()
    m1_tmin = df_sem_prev[f'Target_Min_{m_key}'].sum()
    m1_tmax = df_sem_prev[f'Target_Max_{m_key}'].sum()
    
    if m0_tmin > 0 and m1_tmin > 0:
        if (m0_actual < m0_tmin) and (m1_actual < m1_tmin):
            alertas_meso.append(f"📉 <b>SUBCARGA en {m_name}:</b> El acumulado se ha quedado por debajo del mínimo programado durante 2 microciclos consecutivos.")
            
    if m0_tmax > 0 and m1_tmax > 0:
        if (m0_actual > m0_tmax) and (m1_actual > m1_tmax):
            alertas_meso.append(f"📈 <b>SOBRECARGA en {m_name}:</b> El acumulado ha superado el máximo programado durante 2 microciclos consecutivos.")

with st.expander(f"📅 ALERTAS MESOCICLO (Tendencia 2 Microciclos Consecutivos) - {len(alertas_meso)} Avisos", expanded=False):
    if not alertas_meso:
        st.markdown("<div style='font-size: 14px; color: #2ECC71; font-weight: bold;'>✅ El equipo se mantiene estable. Ninguna métrica de carga acumula 2 microciclos seguidos fuera de rango.</div>", unsafe_allow_html=True)
    else:
        for alerta in alertas_meso:
            if "SUBCARGA" in alerta:
                st.markdown(f"<div style='padding:10px; background-color:rgba(52, 152, 219, 0.2); border-left: 4px solid #3498DB; margin-bottom:10px; color:white; font-size:14px;'>{alerta}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='padding:10px; background-color:rgba(231, 76, 60, 0.2); border-left: 4px solid #E74C3C; margin-bottom:10px; color:white; font-size:14px;'>{alerta}</div>", unsafe_allow_html=True)

st.markdown("---")

tipo_sesion = str(df_master[df_master['Fecha'] == fecha_sel]['Tipo_Dia_Oficial'].iloc[0]).upper()
duracion_sesion = int(df_master[df_master['Fecha'] == fecha_sel]['Duracion_GPS'].max()) if not df_sesion.empty else 0

# --- HISTÓRICO 28 DÍAS DINÁMICO ---
opciones_grafico = {
    'Carga General (UA)': 'Carga_UA',
    'Dist. Total': 'Dist_Total',
    'Dist. >18': 'Dist_18',
    'Dist. >25': 'Dist_25',
    'Dist. >28': 'Dist_28',
    'Sprints': 'Sprints',
    'Aceleraciones': 'Accels',
    'Desaceleraciones': 'Decels',
    'Ac. Máx': 'Acc_Max',
    'Dec. Máx': 'Dec_Max',
    'V. Máx': 'Top_Speed',
    'Player Load': 'Player_Load'
}

if pos_sel == "Equipo Completo" and jug_sel == "Todos":
    df_hist_eq = df_28d[df_28d['Valido_Media']==True].copy()
else:
    df_hist_eq = df_28d.copy()

df_vmax_hoy = df_sesion.merge(vmax_hist, on='Nombre', how='left')
df_vmax_hoy['Porcentaje_Vmax'] = np.where(df_vmax_hoy['Vmax_4_semanas']>0, (df_vmax_hoy['Top_Speed']/df_vmax_hoy['Vmax_4_semanas'])*100, 0)
media_vmax_sesion = df_vmax_hoy['Porcentaje_Vmax'].mean() if not df_vmax_hoy.empty else 0
alcanzan_90 = df_vmax_hoy[df_vmax_hoy['Porcentaje_Vmax'] >= 90].sort_values(by='Porcentaje_Vmax', ascending=False)

c_dur, c_hist, c_info = st.columns([1.5, 3, 2])
with c_dur:
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Session duration</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color:white; font-size:55px; margin-top:0; margin-bottom:0px; line-height: 1;'>{duracion_sesion} min</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:white; font-size:55px; font-weight:normal; margin-top:-10px; margin-bottom:0px; line-height: 1;'>TIPO: {tipo_sesion}</p>", unsafe_allow_html=True)
with c_hist:
    c_h1, c_h2, c_h3 = st.columns([1.8, 2.2, 3]) 
    with c_h1: 
        st.markdown("<div style='padding-top: 4px;'><p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Training Schedule (28d)</p></div>", unsafe_allow_html=True)
    with c_h2: 
        metrica_grafico = st.selectbox("Métrica", list(opciones_grafico.keys()), label_visibility="collapsed")
    
    m_graf = opciones_grafico[metrica_grafico]
    
    if not df_hist_eq.empty:
        if m_graf == 'Carga_UA':
            df_agg = df_hist_eq.groupby('Fecha').agg({'Carga_UA': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()
        elif m_graf in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
            df_agg = df_hist_eq.groupby('Fecha').agg({m_graf: 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()
        else:
            df_agg = df_hist_eq.groupby('Fecha').agg({m_graf: 'mean', f'Target_{m_graf}': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()

        fig_hist = go.Figure()
        colores_barras = ['#FF9F1C' if 'partido' in str(t).lower() else '#555555' for t in df_agg['Tipo_Dia_Oficial']]
        textos_barras = ['P' if 'partido' in str(t).lower() else '' for t in df_agg['Tipo_Dia_Oficial']]

        fig_hist.add_trace(go.Bar(
            x=df_agg['Fecha'], y=df_agg[m_graf],
            marker_color=colores_barras, text=textos_barras, textposition='outside', textfont=dict(color="white", size=10)
        ))

        if m_graf != 'Carga_UA':
            if m_graf in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
                if m_graf == 'Dec_Max': target_y = [df_agg[m_graf].min() * 0.90] * len(df_agg)
                else: target_y = [df_agg[m_graf].max() * 0.90] * len(df_agg)
            else:
                target_y = df_agg[f'Target_{m_graf}']

            fig_hist.add_trace(go.Scatter(
                x=df_agg['Fecha'], y=target_y,
                mode='markers', marker=dict(color='#F1C40F', symbol='line-ew', size=25, line=dict(width=3, color='#F1C40F')),
                hoverinfo='skip'
            ))

        fig_hist.update_layout(template="plotly_dark", height=150, margin=dict(l=0, r=0, t=20, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})

with c_info:
    st.markdown("<p style='color:white; font-size:16px; font-weight:bold; margin-bottom:0;'>Velocidad Máxima HOY (>90%)</p>", unsafe_allow_html=True)
    c_vmax = "#2ECC71" if media_vmax_sesion >= 90 else "#F1C40F" if media_vmax_sesion >= 85 else "#E74C3C"
    st.markdown(f"<h2 style='color:{c_vmax}; margin-top:0;'>{media_vmax_sesion:.1f}% <span style='font-size:14px; color:#A0AEC0; font-weight:normal;'>media</span></h2>", unsafe_allow_html=True)
    with st.expander("👁️ Jugadores al 90% hoy"):
        if not alcanzan_90.empty:
            for _, r in alcanzan_90.iterrows(): st.markdown(f"<span style='color:#2ECC71; font-size:14px;'>• {r['Nombre']} ({r['Porcentaje_Vmax']:.1f}%)</span>", unsafe_allow_html=True)
        else: st.caption("Ninguno")

# =============================================================================
# 5. BULLET CHARTS (MEDIA DE SESIÓN VS RANGO PROGRAMADO)
# =============================================================================
st.markdown("### 📊 Session Mean vs Target Programado")

medias_sesion = {m: df_sesion[m].mean() if not df_sesion.empty else 0.0 for m in metricas_todas}
target_programado_min = {m: df_sesion[f'Target_Min_{m}'].mean() if not df_sesion.empty else 0.0 for m in metricas_todas}
target_programado_max = {m: df_sesion[f'Target_Max_{m}'].mean() if not df_sesion.empty else 0.0 for m in metricas_todas}

def pintar_bullet(metrica, nombre_mostrar, row_col):
    val = medias_sesion.get(metrica, 0)
    t_min = target_programado_min.get(metrica, 0)
    t_max = target_programado_max.get(metrica, 0)
    
    texto_val = f"{val:.1f}" if val < 100 else f"{val:.0f}"
    max_range = max(val, t_max) * 1.2 if max(val, t_max) > 0 else 10
    
    color_bar = "#2ECC71"
    if val < t_min: color_bar = "#3498DB"
    elif val > t_max: color_bar = "#E74C3C"
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[max_range], y=[0], orientation='h', marker=dict(color="rgba(255,255,255,0.1)"), hoverinfo="none", width=0.8))
    
    if val > 0: 
        fig.add_trace(go.Bar(x=[val], y=[0], orientation='h', marker=dict(color=color_bar), text=[texto_val], textposition='auto', insidetextanchor='end', textfont=dict(color="white", size=18, family="Arial Black"), hoverinfo="x", width=0.8))
    
    if t_max > 0:
        if t_min == t_max:
            fig.add_shape(type="line", x0=t_min, x1=t_min, y0=-0.45, y1=0.45, line=dict(color="#F1C40F", width=3))
        else:
            fig.add_shape(type="rect", x0=t_min, y0=-0.4, x1=t_max, y1=0.4, fillcolor="rgba(46, 204, 113, 0.3)", line=dict(width=0))
            fig.add_shape(type="line", x0=t_min, x1=t_min, y0=-0.45, y1=0.45, line=dict(color="#F1C40F", width=2))
            fig.add_shape(type="line", x0=t_max, x1=t_max, y0=-0.45, y1=0.45, line=dict(color="#F1C40F", width=2))
        
    fig.update_layout(
        barmode='overlay', height=65, margin=dict(t=0, b=0, l=0, r=0), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, 
        xaxis=dict(range=[0, max_range], showgrid=False, showticklabels=False), 
        yaxis=dict(range=[-0.5, 0.5], showgrid=False, showticklabels=False)
    )
    
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
# 6. TABLA INDIVIDUAL (ANÁLISIS POR CATEGORÍA TÁCTICA) CON HOVER
# =============================================================================
st.markdown("---")
st.markdown("### 🧑‍🤝‍🧑 Análisis Individual vs Objetivo Periodizado")

metricas_tabla = {'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18', 'Dist_25': 'Dist. >25', 'Dist_28': 'Dist. >28', 'Sprints': 'Sprints', 'Accels': 'Acel.', 'Decels': 'Desac.', 'Acc_Max': 'Ac. Máx', 'Dec_Max': 'Dec. Máx', 'Top_Speed': 'V. Máx', 'Player_Load': 'Load'}
df_sesion_tabla = df_sesion.copy()

orden_tactico = {'defensa central': 1, 'defensa lateral': 2, 'mediocentro': 3, 'mediapunta': 4, 'extremo': 5, 'delantero': 6}
df_sesion_tabla['Peso_Pos'] = df_sesion_tabla['Posicion'].astype(str).str.lower().str.strip().map(orden_tactico).fillna(99)
df_sesion_tabla = df_sesion_tabla.sort_values(['Peso_Pos', 'Nombre'])

if not df_sesion_tabla.empty:
    
    escalas_max = {}
    for m in metricas_tabla:
        max_sesion = df_sesion_tabla[m].max() if not df_sesion_tabla.empty else 0
        if m in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
            ref_max = df_master[m].max() if not df_master.empty else 0
            escalas_max[m] = max(max_sesion, ref_max) * 1.2
        elif m in ['Dist_28', 'Sprints']:
            escalas_max[m] = max(max_sesion, target_refs_global.get(m, 0)) * 1.2
        else:
            t_max_val = df_sesion_tabla[f'Target_Max_{m}'].max() if not df_sesion_tabla.empty else 0
            escalas_max[m] = max(max_sesion, t_max_val) * 1.2
        if escalas_max[m] == 0: escalas_max[m] = 10

    def dibujar_barra_rango(valor, t_min, t_max, max_val, es_decimal):
        if max_val == 0: max_val = 1
        pct_fill = min((valor/max_val)*100, 100)
        pct_t_min = min((t_min/max_val)*100, 100)
        pct_t_max = min((t_max/max_val)*100, 100)
        width_target = max(pct_t_max - pct_t_min, 1)
        
        t_val = f"{valor:.1f}" if es_decimal else f"{valor:.0f}"
        
        if valor < t_min: c_barra = "#3498DB" 
        elif valor > t_max: c_barra = "#E74C3C" 
        else: c_barra = "#2ECC71" 
        
        return f"""
        <div style="position:relative; width:100%; min-width:50px; max-width:90px; height:18px; background-color:rgba(255,255,255,0.1); border-radius:2px; margin:0 auto; overflow:visible;">
            <div style="position:absolute; left:{pct_t_min}%; top:0; height:100%; width:{width_target}%; background-color:rgba(46, 204, 113, 0.2); z-index:1;"></div>
            <div style="position:absolute; left:0; top:0; height:100%; width:{pct_fill}%; background-color:{c_barra}; border-radius:2px; z-index:2;"></div>
            <div style="position:absolute; left:{pct_t_min}%; top:-2px; height:22px; width:2px; background-color:#F1C40F; z-index:3;"></div>
            <div style="position:absolute; left:{pct_t_max}%; top:-2px; height:22px; width:2px; background-color:#F1C40F; z-index:3;"></div>
            <div style="position:absolute; left:4px; top:1px; font-size:11px; font-weight:bold; color:white; z-index:4; text-shadow:1px 1px 1px black;">{t_val}</div>
        </div>
        """
        
    def dibujar_barra_umbral(valor, target, max_val, es_decimal):
        if max_val == 0: max_val = 1
        pct_fill = min((valor/max_val)*100, 100)
        pct_target = min((target/max_val)*100, 100)
        t_val = f"{valor:.1f}" if es_decimal else f"{valor:.0f}"
        c_barra = "#E74C3C" if valor > target and target > 0 else "#3498DB"
        
        return f"""
        <div style="position:relative; width:100%; min-width:50px; max-width:90px; height:18px; background-color:rgba(255,255,255,0.1); border-radius:2px; margin:0 auto; overflow:visible;">
            <div style="position:absolute; left:0; top:0; height:100%; width:{pct_fill}%; background-color:{c_barra}; border-radius:2px; z-index:2;"></div>
            <div style="position:absolute; left:{pct_target}%; top:-2px; height:22px; width:2px; background-color:#F1C40F; z-index:3;"></div>
            <div style="position:absolute; left:4px; top:1px; font-size:11px; font-weight:bold; color:white; z-index:4; text-shadow:1px 1px 1px black;">{t_val}</div>
        </div>
        """

    def dibujar_barra_pico(valor_real, valor_abs, target_90, max_hist, es_decimal):
        max_escala = max(max_hist, valor_abs) * 1.1 if max(max_hist, valor_abs) > 0 else 10
        pct_fill = min((valor_abs / max_escala) * 100, 100)
        pct_target = min((target_90 / max_escala) * 100, 100)
        t_val = f"{valor_real:.1f}" if es_decimal else f"{valor_real:.0f}"
        c_barra = "#E74C3C" if valor_abs >= target_90 and target_90 > 0 else "#2ECC71"
        
        return f"""
        <div style="position:relative; width:100%; min-width:50px; max-width:90px; height:18px; background-color:rgba(255,255,255,0.1); border-radius:2px; margin:0 auto; overflow:visible;">
            <div style="position:absolute; left:0; top:0; height:100%; width:{pct_fill}%; background-color:{c_barra}; border-radius:2px; z-index:2;"></div>
            <div style="position:absolute; left:{pct_target}%; top:-2px; height:22px; width:2px; background-color:#F1C40F; z-index:3;"></div>
            <div style="position:absolute; left:4px; top:1px; font-size:11px; font-weight:bold; color:white; z-index:4; text-shadow:1px 1px 1px black;">{t_val}</div>
        </div>
        """

    # --- INYECCIÓN DE CSS PARA EL HOVER DE LA FILA ---
    html = """
    <style>
    .tabla-jugadores tbody tr {
        transition: background-color 0.2s ease;
    }
    .tabla-jugadores tbody tr:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
    }
    </style>
    <div style="overflow-x: auto; padding-bottom: 20px;">
    <table class="tabla-jugadores" style="border-collapse: collapse; text-align: center; font-family: sans-serif; font-size: 12px; width: 100%;">
        <thead><tr style="background-color: rgba(0,0,0,0.3); border-bottom: 2px solid #555;">
        <th style="padding: 10px;">POSICIÓN</th><th style="padding: 10px; text-align:left;">JUGADOR</th>
    """
    for m_key, nombre_m in metricas_tabla.items(): 
        if m_key in ['Acc_Max', 'Dec_Max', 'Top_Speed']: html += f"<th colspan='2' style='padding:10px; border-left:1px solid #444;'>{nombre_m}</th>"
        else: html += f"<th colspan='3' style='padding:10px; border-left:1px solid #444;'>{nombre_m}</th>"
            
    html += "<th style='padding: 10px; border-left: 1px solid #444;'>RPE</th></tr>"
    html += "<tr style='border-bottom: 1px solid #555; font-size: 10px; color: #A0AEC0;'><th></th><th></th>"
    
    for m_key in metricas_tabla: 
        if m_key in ['Acc_Max', 'Dec_Max', 'Top_Speed']: html += "<th style='padding:5px; border-left:1px solid #444;'>Sesión(Ref)</th><th>% Max</th>"
        else: html += "<th style='padding:5px; border-left:1px solid #444;'>Sesión(Ref)</th><th>Obj</th><th>Z-Score</th>"
            
    html += "<th></th></tr></thead><tbody>"

    pos_counts = df_sesion_tabla['Posicion'].value_counts(dropna=False).to_dict()
    pos_actual = ""
    
    for _, row in df_sesion_tabla.iterrows():
        jugador, pos, rpe_val = row['Nombre'], row['Posicion'], row['RPE_G']
        df_h = df_master[(df_master['Nombre'] == jugador) & (df_master['Fecha'] <= fecha_sel)].sort_values('Fecha').tail(28)
        df_28_player = df_master[(df_master['Nombre'] == jugador) & (df_master['Fecha'] >= fecha_inicio_vmax.strftime('%Y-%m-%d')) & (df_master['Fecha'] <= fecha_sel)]
        
        html += "<tr style='border-bottom: 1px solid #333;'>"
        if pos != pos_actual:
            html += f"<td rowspan='{pos_counts.get(pos,1)}' style='vertical-align:middle; font-weight:bold; color:#E67E22; text-transform:uppercase; border-right:1px solid #444; border-bottom:2px solid #555;'>{pos}</td>"
            pos_actual = pos
        html += f"<td style='padding:8px; text-align:left; white-space:nowrap;'>{jugador}</td>"
        
        for m, _ in metricas_tabla.items():
            val = row[m]
            es_dec = m in ['Dist_18', 'Dist_25', 'Dist_28', 'Acc_Max', 'Dec_Max', 'Top_Speed']
            
            if m in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
                if m == 'Dec_Max':
                    max_h = abs(df_28_player[m].min()) if not df_28_player.empty else 0
                    v_abs = abs(val)
                else:
                    max_h = df_28_player[m].max() if not df_28_player.empty else 0
                    v_abs = val
                    
                t_90 = max_h * 0.90
                pct_max = (v_abs / max_h * 100) if max_h > 0 else 0
                
                html += f"<td style='padding:5px; border-left:1px solid #333;'>{dibujar_barra_pico(val, v_abs, t_90, max_h, es_dec)}</td>"
                color_pct = "#E74C3C" if pct_max >= 90 else "#2ECC71"
                html += f"<td style='padding:5px; background-color:transparent; color:{color_pct}; font-weight:bold; font-size:11px;'>{pct_max:.0f}%</td>"
            
            elif m in ['Dist_28', 'Sprints']:
                t_ref = target_refs_global[m]
                diff_text = ""
                if val < t_ref:
                    diff = t_ref - val
                    diff_text = f"-{diff:.1f}" if es_dec else f"-{diff:.0f}"
                elif val > t_ref and t_ref > 0:
                    diff = val - t_ref
                    diff_text = f"+{diff:.1f}" if es_dec else f"+{diff:.0f}"
                else:
                    diff_text = "<span style='color:#2ECC71; font-size:14px;'>✔</span>"
                    
                html += f"<td style='padding:5px; border-left:1px solid #333;'>{dibujar_barra_umbral(val, t_ref, escalas_max[m], es_dec)}</td>"
                html += f"<td style='padding:5px; background-color:transparent; color:#E2E8F0; font-weight:bold; font-size:11px;'>{diff_text}</td>"
                
                z = (val - df_h[m].mean()) / df_h[m].std() if len(df_h) > 2 and df_h[m].std() > 0 else 0
                c_z = "#8B0000" if z > 2 else "#E74C3C" if z > 1.5 else "#1F618D" if z < -2 else "transparent"
                html += f"<td style='padding:5px; background-color:{c_z}; border-radius:3px; color:{'white' if c_z!='transparent' else '#CCC'};'>{z:.2f}</td>"

            else:
                t_min = row[f'Target_Min_{m}']
                t_max = row[f'Target_Max_{m}']
                
                diff_text = ""
                if val < t_min:
                    diff = t_min - val
                    diff_text = f"-{diff:.1f}" if es_dec else f"-{diff:.0f}"
                elif val > t_max and t_max > 0:
                    diff = val - t_max
                    diff_text = f"+{diff:.1f}" if es_dec else f"+{diff:.0f}"
                else:
                    diff_text = "<span style='color:#2ECC71; font-size:14px;'>✔</span>"

                html += f"<td style='padding:5px; border-left:1px solid #333;'>{dibujar_barra_rango(val, t_min, t_max, escalas_max[m], es_dec)}</td>"
                html += f"<td style='padding:5px; background-color:transparent; color:#E2E8F0; font-weight:bold; font-size:11px;'>{diff_text}</td>"
                
                z = (val - df_h[m].mean()) / df_h[m].std() if len(df_h) > 2 and df_h[m].std() > 0 else 0
                c_z = "#8B0000" if z > 2 else "#E74C3C" if z > 1.5 else "#1F618D" if z < -2 else "transparent"
                html += f"<td style='padding:5px; background-color:{c_z}; border-radius:3px; color:{'white' if c_z!='transparent' else '#CCC'};'>{z:.2f}</td>"
        
        html += f"<td style='padding:5px; border-left:1px solid #444; font-weight:bold; background-color:{'#E74C3C' if rpe_val>=8 else 'transparent'};'>{rpe_val:.1f}</td></tr>"
        
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("No hay datos para esta fecha.")