import streamlit as st
import pandas as pd
import numpy as np
import glob
import requests
import io
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from utils import (quitar_exjugadores, sin_exjugadores, es_exjugador, descargar_sheet, comprobar_descargas, configurar_pagina, exigir_login_staff, controles_sidebar, render_html, tarjetas_kpi,
                   bloque_alerta, chips_html, nombre_bonito, nombre_corto, fecha_es, etiqueta_sesion, estilo_fig,
                   mostrar_fig, barras_jugadores, mostrar_segun_pantalla, nombre_pulsado, ROJO, NARANJA, AZUL, VERDE, ACENTO, NEUTRO, NEUTRO_FUERTE,
                   NEUTRO_TEXTO, TEXTO, BORDE)

# =============================================================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# =============================================================================
configurar_pagina("Carga Externa GPS - Adarve DH")
exigir_login_staff()
movil = controles_sidebar()

# Referencia "100%" de partido por demarcación (últimos 4 partidos con >= 60'):
#   "media"      -> media de los partidos (RECOMENDADO; antes se usaba (media + máximo) / 2,
#                   que sobrestima el partido tipo y hacía que casi todo saliera en subcarga)
#   "media_max"  -> criterio anterior
REF_MODO = "media"

# =============================================================================
# VARIABLES GLOBALES DE SESIÓN (MEMORIA DEL RADAR Y FILTROS)
# =============================================================================
if 'partidos_radar' not in st.session_state:
    st.session_state.partidos_radar = []
if 'grafico_key' not in st.session_state:
    st.session_state.grafico_key = 0
if 'hist_grafico_key' not in st.session_state:
    st.session_state.hist_grafico_key = 0
if 'fecha_hist_pulsada' not in st.session_state:
    st.session_state.fecha_hist_pulsada = None
if 'fecha_maestra' not in st.session_state:
    st.session_state.fecha_maestra = None

# =============================================================================
# 2. MOTOR DE EXTRACCIÓN DE DATOS
# =============================================================================
def descargar_csv_drive(sheet_id, gid=None):
    return descargar_sheet(sheet_id, gid)   # utils.py: tiempo límite + reintento

@st.cache_data(ttl=600)
def obtener_rpe_maestro():
    df_rpe = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if df_rpe.empty: return pd.DataFrame()
    
    try:
        cols = df_rpe.columns
        col_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        col_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        col_t = next((c for c in cols if str(c).lower().strip() == 'tipo de sesión' or 'tipo de sesion' in str(c).lower()), cols[2])
        col_min = next((c for c in cols if 'minuto' in str(c).lower()), cols[3] if len(cols)>3 else None)
        col_c = next((c for c in cols if 'cardio' in str(c).lower()), cols[4] if len(cols)>4 else None)
        col_m = next((c for c in cols if 'muscular' in str(c).lower()), cols[5] if len(cols)>5 else None)

        df_rpe['Fecha'] = pd.to_datetime(df_rpe[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_rpe['Nombre_Cruce'] = df_rpe[col_n].fillna('Anónimo').astype(str).str.strip().str.lower()
        df_rpe['Tipo_Dia_Oficial'] = df_rpe[col_t].fillna('Entreno').astype(str).str.strip()
        
        if col_min: df_rpe['Minutos_RPE'] = pd.to_numeric(df_rpe[col_min], errors='coerce').fillna(0)
        else: df_rpe['Minutos_RPE'] = 0
        
        val_c = pd.to_numeric(df_rpe[col_c], errors='coerce') if col_c else pd.Series(np.nan, index=df_rpe.index)
        val_m = pd.to_numeric(df_rpe[col_m], errors='coerce') if col_m else pd.Series(np.nan, index=df_rpe.index)
        df_rpe['RPE_G'] = pd.concat([val_c, val_m], axis=1).mean(axis=1, skipna=True)
        
        return df_rpe.dropna(subset=['Fecha'])[['Fecha', 'Nombre_Cruce', 'Tipo_Dia_Oficial', 'Minutos_RPE', 'RPE_G']]
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=600)
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
            df_limpio['Posicion'] = df_temp[col_pos].astype(str).str.strip() if col_pos else 'Sin Posición'
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
        # CORRECCIÓN: si el GPS no trae la posición ("nan"), se toma de data/Posiciones.xlsx
        df_final['Posicion'] = df_final['Posicion'].replace({'nan': np.nan, 'None': np.nan, '': np.nan})
        r_pos = os.path.join("data", "Posiciones.xlsx")
        if os.path.exists(r_pos):
            try:
                dp = pd.read_excel(r_pos)
                dp.columns = [str(c).strip() for c in dp.columns]
                c_n = next((c for c in dp.columns if 'jugador' in c.lower() or 'nombre' in c.lower()), dp.columns[0])
                c_p = next((c for c in dp.columns if 'posic' in c.lower()), None)
                if c_p:
                    mapa = {nombre_bonito(n).lower(): str(p).strip() for n, p in zip(dp[c_n], dp[c_p]) if pd.notna(p)}
                    faltan = df_final['Posicion'].isna()
                    df_final.loc[faltan, 'Posicion'] = df_final.loc[faltan, 'Nombre'].apply(lambda n: mapa.get(nombre_bonito(n).lower()))
            except Exception:
                pass
        df_final['Posicion'] = df_final['Posicion'].fillna('Sin posición')
        return df_final
    return pd.DataFrame()

@st.cache_data(ttl=600)
def obtener_calendario_partidos():
    df_cal = descargar_csv_drive("1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5", "1771990969")
    if df_cal.empty: return pd.DataFrame()
    
    try:
        cols = df_cal.columns
        col_f = next((c for c in cols if 'fecha' in str(c).lower()), cols[0])
        col_cf = next((c for c in cols if 'casa' in str(c).lower() or 'fuera' in str(c).lower()), cols[1])
        col_eq = next((c for c in cols if 'equipo' in str(c).lower() or 'rival' in str(c).lower()), cols[2])
        col_esc = next((c for c in cols if 'escudo' in str(c).lower()), cols[3])
        col_res = next((c for c in cols if 'resultado' in str(c).lower()), cols[4] if len(cols)>4 else None)
            
        df_cal['Fecha'] = pd.to_datetime(df_cal[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_cal['Local_Visitante'] = df_cal[col_cf].astype(str).str.strip().str.title()
        df_cal['Rival'] = df_cal[col_eq].astype(str).str.strip()
        df_cal['Escudo'] = df_cal[col_esc].astype(str).str.strip()
        
        if col_res: df_cal['Resultado'] = df_cal[col_res].astype(str).str.strip()
        else: df_cal['Resultado'] = ""
        
        df_cal = df_cal.dropna(subset=['Fecha'])
        
        def parse_resultado(row):
            res = str(row['Resultado']).strip()
            cf = str(row['Local_Visitante']).strip().lower()
            if '-' not in res: return None 
            try:
                home, away = res.split('-')
                home, away = int(home.strip()), int(away.strip())
                if home == away: return 'E'
                if cf == 'casa': return 'G' if home > away else 'P'
                elif cf == 'fuera': return 'G' if away > home else 'P'
                return None
            except: return None
                
        df_cal['Resultado_Codificado'] = df_cal.apply(parse_resultado, axis=1)
        return df_cal[['Fecha', 'Rival', 'Local_Visitante', 'Resultado', 'Resultado_Codificado', 'Escudo']]
    except Exception as e:
        return pd.DataFrame()

# =============================================================================
# HELPER CÁLCULO EWMA RATIO (AGUDO:CRÓNICO PONDERADO 7:21 DÍAS)
# =============================================================================
def calcular_acwr_ewma(df, metrica='Dist_25', dias_agudo=7, dias_cronico=21):
    if df.empty or metrica not in df.columns: return pd.DataFrame()
    
    lista_dfs = []
    fechas_min = pd.to_datetime(df['Fecha'].min())
    fechas_max = pd.to_datetime(df['Fecha'].max())
    fechas_completas = pd.date_range(start=fechas_min, end=fechas_max, freq='D')
    
    alpha_agudo = 2.0 / (dias_agudo + 1)
    alpha_cronico = 2.0 / (dias_cronico + 1)
    
    for jug in df['Nombre'].unique():
        df_j = df[df['Nombre'] == jug].copy()
        df_j['Fecha_dt'] = pd.to_datetime(df_j['Fecha'])
        
        df_full = pd.DataFrame({'Fecha_dt': fechas_completas})
        df_full = df_full.merge(df_j[['Fecha_dt', metrica, 'Nombre', 'Posicion']], on='Fecha_dt', how='left')
        df_full['Nombre'] = jug
        df_full[metrica] = df_full[metrica].fillna(0.0)
        df_full['Fecha'] = df_full['Fecha_dt'].dt.strftime('%Y-%m-%d')
        df_full['Posicion'] = df_full['Posicion'].ffill().bfill().fillna('Sin Posición')
        
        df_full['EWMA_Agudo'] = df_full[metrica].ewm(alpha=alpha_agudo, adjust=False).mean()
        df_full['EWMA_Cronico'] = df_full[metrica].ewm(alpha=alpha_cronico, adjust=False).mean()
        
        df_full['ACWR'] = np.where(df_full['EWMA_Cronico'] > 1.0, df_full['EWMA_Agudo'] / df_full['EWMA_Cronico'], 0.0)
        lista_dfs.append(df_full)
        
    return pd.concat(lista_dfs, ignore_index=True)

# =============================================================================
# 3. PROCESAMIENTO Y MODELO DE JUEGO
# =============================================================================
df_rpe = obtener_rpe_maestro()
df_gps = cargar_archivos_gps()
df_calendario = obtener_calendario_partidos()
comprobar_descargas(obtener_rpe_maestro, obtener_calendario_partidos)

if df_gps.empty:
    st.info("🚧 Aún no hay archivos de GPS en la carpeta `data/GPS`.")
    st.stop()

fechas_partidos_cal = set(df_calendario['Fecha'].unique()) if not df_calendario.empty else set()

if not df_rpe.empty:
    df_sesion_dia = df_rpe.groupby('Fecha')['Tipo_Dia_Oficial'].apply(lambda x: x.mode()[0] if not x.mode().empty else 'Entreno').reset_index()
    df_master = pd.merge(df_gps, df_sesion_dia, on='Fecha', how='left')
    df_master['Tipo_Dia_Oficial'] = df_master['Tipo_Dia_Oficial'].fillna('Entreno')
    
    df_master['Tipo_Dia_Oficial'] = df_master.apply(
        lambda r: 'Partido' if r['Fecha'] in fechas_partidos_cal or 'partido' in str(r['Tipo_Dia_Oficial']).lower() else r['Tipo_Dia_Oficial'], axis=1
    )
    
    df_rpe_jugadores = df_rpe[['Fecha', 'Nombre_Cruce', 'Minutos_RPE', 'RPE_G']].drop_duplicates(subset=['Fecha', 'Nombre_Cruce'], keep='last')
    df_master = pd.merge(df_master, df_rpe_jugadores, on=['Fecha', 'Nombre_Cruce'], how='left')
    
    # CORRECCIÓN: si el jugador no rellenó el RPE se deja vacío (antes se inventaba un 5)
    df_master['Minutos_RPE'] = df_master['Minutos_RPE'].fillna(df_master['Duracion_GPS'])
    df_master['Minutos_RPE'] = np.where(df_master['Minutos_RPE'] > 0, df_master['Minutos_RPE'], df_master['Duracion_GPS'])
else:
    df_master = df_gps.copy()
    df_master['Tipo_Dia_Oficial'] = df_master['Fecha'].apply(lambda f: 'Partido' if f in fechas_partidos_cal else 'Entreno')
    df_master['RPE_G'] = np.nan
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
    elif 'compensatorio' in tipo or '+1' in tipo or '+2' in tipo:
        validez.append(True)
        jugo_mas_60.append(False)
    else:
        validez.append(True)
        jugo_mas_60.append(False)

df_master['Valido_Media'] = validez
df_master['Jugo_60_Ultimo_Partido'] = jugo_mas_60

# CÁLCULO DE CARGA (sRPE) Y MÉTRICAS COMBINADAS
df_master['Acc_Dec'] = df_master['Accels'] + df_master['Decels']
df_master['Carga_UA'] = df_master['Minutos_RPE'] * df_master['RPE_G']

fechas_disp = sorted(df_master['Fecha'].unique(), reverse=True)

if st.session_state.fecha_maestra not in fechas_disp:
    st.session_state.fecha_maestra = fechas_disp[0] if fechas_disp else None

def get_target_range(metrica, tipo_dia, jugo_60):
    t = str(tipo_dia).lower()
    if 'partido' in t: return (100, 100)
    
    if 'compensatorio' in t or (('+1' in t or '+2' in t) and not jugo_60):
        if metrica == 'Dist_Total': return (55, 65)
        elif metrica == 'Dist_18': return (40, 50)
        elif metrica in ['Dist_25', 'Dist_28', 'Sprints']: return (30, 45)
        elif metrica in ['Accels', 'Decels']: return (60, 70)
        elif metrica == 'Player_Load': return (55, 65)
        return (0, 0)

    if ('+1' in t or '+2' in t) and jugo_60:
        if metrica == 'Dist_Total': return (20, 30)
        elif metrica == 'Dist_18': return (0, 30)
        elif metrica in ['Dist_25', 'Dist_28', 'Sprints']: return (0, 10)
        elif metrica in ['Accels', 'Decels']: return (10, 30)
        elif metrica == 'Player_Load': return (20, 30)
        return (0, 0)

    is_4 = '-4' in t or 'md-4' in t or '4' in t
    is_3 = '-3' in t or 'md-3' in t or '3' in t
    is_2 = '-2' in t or 'md-2' in t or '2' in t
    is_1 = '-1' in t or 'md-1' in t or '1' in t
    
    if metrica == 'Dist_Total':
        if is_4: return (45, 55)
        if is_3: return (50, 65)
        if is_2: return (10, 20)
        if is_1: return (20, 30)
    elif metrica == 'Dist_18':
        if is_4: return (25, 40)
        if is_3: return (55, 70)
        if is_2: return (0, 10)
        if is_1: return (15, 25)
    elif metrica in ['Dist_25', 'Dist_28', 'Sprints']:   # >28 km/h y sprints siguen los % de >25 km/h
        if is_4: return (0, 15)
        if is_3: return (40, 75)
        if is_2: return (0, 5)
        if is_1: return (5, 15)
    elif metrica in ['Accels', 'Decels']:
        if is_4: return (60, 75)
        if is_3: return (50, 65)
        if is_2: return (0, 15)
        if is_1: return (15, 30)
    elif metrica == 'Player_Load':
        if is_4: return (55, 65)
        if is_3: return (50, 65)
        if is_2: return (10, 20)
        if is_1: return (20, 30)
        
    return (0, 0) 

df_partidos = df_master[df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido', na=False)]
df_partidos = df_partidos[df_partidos['Valido_Media'] == True]
metricas_todas = ['Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'Sprints', 'Accels', 'Decels', 'Acc_Max', 'Dec_Max', 'Top_Speed', 'Player_Load']

fallbacks_profesionales = {
    'Dist_Total': 10000, 'Dist_18': 800, 'Dist_25': 250, 'Dist_28': 100, 
    'Sprints': 20, 'Accels': 50, 'Decels': 50, 'Acc_Max': 4.5, 'Dec_Max': -4.5, 
    'Top_Speed': 31, 'Player_Load': 1000
}

# =============================================================================
# CÁLCULO DE REFERENCIAS 100% POR DEMARCACIÓN TÁCTICA
# =============================================================================
def referencia_partido(serie, m):
    if REF_MODO == "media":
        return serie.mean()
    extremo = serie.min() if m == 'Dec_Max' else serie.max()
    return (serie.mean() + extremo) / 2

dict_ref_posicion = {}
if not df_partidos.empty:
    ultimos_4_fechas = sorted(df_partidos['Fecha'].unique(), reverse=True)[:4]
    df_ref_partidos = df_partidos[df_partidos['Fecha'].isin(ultimos_4_fechas)]
    
    for pos_tag in df_master['Posicion'].unique():
        df_p_pos = df_ref_partidos[df_ref_partidos['Posicion'] == pos_tag]
        dict_ref_posicion[pos_tag] = {}
        for m in metricas_todas:
            if not df_p_pos.empty and df_p_pos[m].mean() != 0:
                dict_ref_posicion[pos_tag][m] = referencia_partido(df_p_pos[m], m)
            else:
                dict_ref_posicion[pos_tag][m] = fallbacks_profesionales[m]

def calc_target_min(row, m):
    pos = row['Posicion']
    ref_100 = dict_ref_posicion.get(pos, fallbacks_profesionales).get(m, fallbacks_profesionales[m])
    if m in ['Acc_Max', 'Dec_Max', 'Top_Speed']: return 0
    pct_min = get_target_range(m, row['Tipo_Dia_Oficial'], row['Jugo_60_Ultimo_Partido'])[0]
    return ref_100 * (pct_min / 100)

def calc_target_max(row, m):
    pos = row['Posicion']
    ref_100 = dict_ref_posicion.get(pos, fallbacks_profesionales).get(m, fallbacks_profesionales[m])
    if m in ['Acc_Max', 'Dec_Max', 'Top_Speed']: return 0
    pct_max = get_target_range(m, row['Tipo_Dia_Oficial'], row['Jugo_60_Ultimo_Partido'])[1]
    return ref_100 * (pct_max / 100)

for m in metricas_todas:
    df_master[f'Target_Min_{m}'] = df_master.apply(lambda r: calc_target_min(r, m), axis=1)
    df_master[f'Target_Max_{m}'] = df_master.apply(lambda r: calc_target_max(r, m), axis=1)
    df_master[f'Target_{m}'] = (df_master[f'Target_Min_{m}'] + df_master[f'Target_Max_{m}']) / 2

# =============================================================================
# 4. INTERFAZ: CABECERA Y FILTROS INTERACTIVOS
# =============================================================================
st.title("CARGA EXTERNA (GPS)")

def actualizar_fecha_manual():
    st.session_state.fecha_maestra = st.session_state.widget_fecha
    st.session_state.fecha_hist_pulsada = None

# Sincronización bidireccional segura antes de instanciar el selectbox
if 'widget_fecha' in st.session_state:
    if st.session_state.widget_fecha != st.session_state.fecha_maestra:
        st.session_state.widget_fecha = st.session_state.fecha_maestra
else:
    st.session_state.widget_fecha = st.session_state.fecha_maestra

idx_fecha_seleccionada = fechas_disp.index(st.session_state.fecha_maestra) if st.session_state.fecha_maestra in fechas_disp else 0

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: 
    fecha_sel = st.selectbox("📅 Fecha:", fechas_disp, index=idx_fecha_seleccionada, key="widget_fecha", on_change=actualizar_fecha_manual, format_func=fecha_es)
with col_f2:
    posiciones_validas = [str(p) for p in df_master['Posicion'].unique() if str(p).lower() != 'nan']
    pos_sel = st.selectbox("⚽ Posición:", ["Equipo Completo"] + sorted(posiciones_validas))
with col_f3:
    if pos_sel == "Equipo Completo":
        jugadores_validos = sorted([str(j) for j in df_master['Nombre'].unique() if str(j).lower() != 'nan'])
    else:
        jugadores_validos = sorted([str(j) for j in df_master[df_master['Posicion'] == pos_sel]['Nombre'].unique() if str(j).lower() != 'nan'])
    jugadores_validos = sin_exjugadores(jugadores_validos)   # Baja en Posiciones.xlsx
    jug_sel = st.selectbox("🏃 Jugador:", ["Todos"] + jugadores_validos, format_func=lambda x: x if x == "Todos" else nombre_bonito(x))

target_refs_global = {}
if not df_partidos.empty:
    ultimos_4_fechas = sorted(df_partidos['Fecha'].unique(), reverse=True)[:4]
    df_ref_base = df_partidos[df_partidos['Fecha'].isin(ultimos_4_fechas)]
    
    if jug_sel != "Todos":
        df_ref_base = df_ref_base[df_ref_base['Nombre'] == jug_sel]
    elif pos_sel != "Equipo Completo":
        df_ref_base = df_ref_base[df_ref_base['Posicion'] == pos_sel]
        
    for m in metricas_todas:
        if not df_ref_base.empty and df_ref_base[m].mean() != 0:
            target_refs_global[m] = referencia_partido(df_ref_base[m], m)
        else:
            target_refs_global[m] = fallbacks_profesionales[m]
else:
    for m in metricas_todas: target_refs_global[m] = fallbacks_profesionales[m]

df_sesion = df_master[df_master['Fecha'] == fecha_sel]
fecha_datetime = datetime.strptime(fecha_sel, '%Y-%m-%d').date()
df_fechas = pd.to_datetime(df_master['Fecha']).dt.date

# MICROCICLO = del día siguiente al último partido hasta la fecha elegida.
# CORRECCIÓN: los partidos se toman del CALENDARIO del Drive (antes solo contaban los partidos con GPS,
# así que si un partido no se había grabado el microciclo empezaba semanas atrás).
fechas_partido = set(pd.to_datetime(list(fechas_partidos_cal), errors='coerce').dropna().date) if fechas_partidos_cal else set()
fechas_partido |= set(pd.to_datetime(df_master[df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido', na=False)]['Fecha']).dt.date)
partidos_previos = sorted(f for f in fechas_partido if f < fecha_datetime)
if partidos_previos:
    last_match_date = partidos_previos[-1]
    fecha_inicio_sem = last_match_date + timedelta(days=1)
    if len(partidos_previos) >= 2:
        fecha_inicio_sem_prev = partidos_previos[-2] + timedelta(days=1)
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

evaluar_vmax_semana = any(k in str(t).lower() for t in df_sem['Tipo_Dia_Oficial'].unique() for k in ['-3', '3', '-2', '2', '-1', '1', 'partido'])

for jug in sin_exjugadores(df_sem['Nombre'].unique()):
    df_j = df_sem[df_sem['Nombre'] == jug]
    
    if evaluar_vmax_semana:
        hits_vmax = df_j['Hit_90'].sum()
        if hits_vmax < 1:
            jugadores_vmax_peligro.append((jug, hits_vmax))
        
    for m_key in metricas_alerta.keys():
        expected_min = df_j[f'Target_Min_{m_key}'].sum()
        expected_max = df_j[f'Target_Max_{m_key}'].sum()
        actual_abs = df_j[m_key].sum()
        
        pos_jug = df_j['Posicion'].iloc[0] if not df_j.empty else 'Sin Posición'
        ref_partido = dict_ref_posicion.get(pos_jug, fallbacks_profesionales).get(m_key, fallbacks_profesionales[m_key])
        
        if expected_min > 0 and actual_abs < (expected_min * 0.80):
            actual_pct = (actual_abs / ref_partido * 100) if ref_partido > 0 else 0
            exp_pct_min = (expected_min / ref_partido * 100) if ref_partido > 0 else 0
            exp_pct_max = (expected_max / ref_partido * 100) if ref_partido > 0 else 0
            texto_alerta = f"{actual_pct:.0f}% / {exp_pct_min:.0f}-{exp_pct_max:.0f}%"
            alertas_metricas[m_key].append((jug, texto_alerta))

total_avisos_micro = len(jugadores_vmax_peligro) + sum(len(lista) for lista in alertas_metricas.values())

st.markdown("<br>", unsafe_allow_html=True)
str_fechas_micro = f"Desde {fecha_inicio_sem.strftime('%d/%m')} hasta {fecha_datetime.strftime('%d/%m')}"
with st.expander(f"🚨 ALERTAS MICROCICLO ({str_fechas_micro}) · {total_avisos_micro} avisos", expanded=False):
    st.caption("Jugadores por debajo del 80% del mínimo programado acumulado en el microciclo (valor real / rango objetivo, en % del partido).")
    bloque_alerta("🏃 Sin estímulo de velocidad (ningún día ≥ 90% de su Vmax)", [j for j, _ in jugadores_vmax_peligro], ROJO,
                  vacio="✅ Todos han tenido estímulo de velocidad")
    hay_alguna = False
    for m_key, m_tit in [('Dist_Total', 'Dist. total'), ('Dist_18', 'Dist. >18 km/h'), ('Dist_25', 'Dist. >25 km/h'),
                         ('Accels', 'Aceleraciones'), ('Decels', 'Desaceleraciones'), ('Player_Load', 'Player Load')]:
        lista = alertas_metricas[m_key]
        if lista:
            hay_alguna = True
            bloque_alerta(f"🔋 {m_tit} · {len(lista)}", [j for j, _ in lista], AZUL, sufijos=dict(lista))
    if not hay_alguna:
        st.caption("✅ Ninguna métrica de volumen por debajo de lo programado.")

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

with st.expander(f"📅 ALERTAS MESOCICLO (2 microciclos seguidos fuera de rango) · {len(alertas_meso)} avisos", expanded=False):
    if not alertas_meso:
        st.markdown("<div style='font-size: 14px; color: #2ECC71; font-weight: bold;'>✅ El equipo se mantiene estable. Ninguna métrica de carga acumula 2 microciclos seguidos fuera de rango.</div>", unsafe_allow_html=True)
    else:
        for alerta in alertas_meso:
            if "SUBCARGA" in alerta:
                st.markdown(f"<div style='padding:10px; background-color:rgba(52, 152, 219, 0.2); border-left: 4px solid #3498DB; margin-bottom:10px; color:white; font-size:14px;'>{alerta}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='padding:10px; background-color:rgba(231, 76, 60, 0.2); border-left: 4px solid #E74C3C; margin-bottom:10px; color:white; font-size:14px;'>{alerta}</div>", unsafe_allow_html=True)

st.markdown("---")

tipo_sesion = str(df_master[df_master['Fecha'] == fecha_sel]['Tipo_Dia_Oficial'].iloc[0]).upper() if not df_master[df_master['Fecha'] == fecha_sel].empty else "ENTRENO"
duracion_sesion = int(df_master[df_master['Fecha'] == fecha_sel]['Duracion_GPS'].max()) if not df_sesion.empty else 0

# --- HISTÓRICO 28 DÍAS DINÁMICO CON FILTRO POR TIPO DE SESIÓN ---
opciones_grafico = {
    'Carga General (sRPE)': 'Carga_UA',
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

df_hist_eq = df_28d[df_28d['Valido_Media'] == True].copy()

df_vmax_hoy = df_sesion.merge(vmax_hist, on='Nombre', how='left')
df_vmax_hoy['Porcentaje_Vmax'] = np.where(df_vmax_hoy['Vmax_4_semanas']>0, (df_vmax_hoy['Top_Speed']/df_vmax_hoy['Vmax_4_semanas'])*100, 0)
media_vmax_sesion = df_vmax_hoy['Porcentaje_Vmax'].mean() if not df_vmax_hoy.empty else 0
alcanzan_90 = quitar_exjugadores(df_vmax_hoy[df_vmax_hoy['Porcentaje_Vmax'] >= 90], 'Nombre').sort_values(by='Porcentaje_Vmax', ascending=False)

tarjetas_kpi([
    {"titulo": "Tipo de sesión", "valor": etiqueta_sesion(tipo_sesion)},
    {"titulo": "Duración", "valor": f"{duracion_sesion} min"},
    {"titulo": "Vmax media de la sesión", "valor": f"{media_vmax_sesion:.0f}%", "sub": "% de la Vmax de cada jugador (28 días)",
     "color": TEXTO if media_vmax_sesion >= 85 else NARANJA},
    {"titulo": "Jugadores ≥ 90% Vmax", "valor": f"{len(alcanzan_90)}/{len(df_vmax_hoy)}"},
])
c_hist, c_info = st.columns([3.2, 1.3])
with c_hist:
    c_h1, c_h2, c_h3 = st.columns([1.6, 2.2, 2.2]) 
    with c_h1: 
        st.markdown("**Histórico 28 días**")
    with c_h2: 
        metrica_grafico = st.selectbox("Métrica", list(opciones_grafico.keys()), label_visibility="collapsed")
    with c_h3:
        tipos_disp = ["Todos los tipos"] + sorted([str(t) for t in df_28d['Tipo_Dia_Oficial'].dropna().unique() if str(t).strip() != ''])
        filtro_tipo_sesion = st.selectbox("Tipo de Sesión", tipos_disp, label_visibility="collapsed", key="sel_filtro_tipo_sesion_hist")

    if filtro_tipo_sesion != "Todos los tipos":
        df_hist_eq = df_hist_eq[df_hist_eq['Tipo_Dia_Oficial'] == filtro_tipo_sesion]
    
    m_graf = opciones_grafico[metrica_grafico]
    
    if not df_hist_eq.empty:
        if m_graf == 'Carga_UA':
            df_agg = df_hist_eq.groupby('Fecha').agg({'Carga_UA': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()
        elif m_graf in ['Acc_Max', 'Dec_Max', 'Top_Speed']:
            df_agg = df_hist_eq.groupby('Fecha').agg({m_graf: 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()
        else:
            df_agg = df_hist_eq.groupby('Fecha').agg({m_graf: 'mean', f'Target_{m_graf}': 'mean', 'Tipo_Dia_Oficial': 'first'}).reset_index()

        if not df_calendario.empty:
            df_agg = pd.merge(df_agg, df_calendario[['Fecha', 'Escudo']], on='Fecha', how='left')
        else:
            df_agg['Escudo'] = None

        fig_hist = go.Figure()
        colores_barras = ['#FF9F1C' if 'partido' in str(t).lower() else '#555555' for t in df_agg['Tipo_Dia_Oficial']]
        textos_barras = ['' for t in df_agg['Tipo_Dia_Oficial']]
        bordes_barras = ['#00A8E8' if row_f == fecha_sel else 'rgba(0,0,0,0)' for row_f in df_agg['Fecha']]
        anchos_bordes = [3 if row_f == fecha_sel else 0 for row_f in df_agg['Fecha']]

        fig_hist.add_trace(go.Bar(
            x=df_agg['Fecha'], y=df_agg[m_graf],
            customdata=df_agg['Fecha'],
            marker_color=colores_barras,
            marker_line=dict(color=bordes_barras, width=anchos_bordes),
            text=textos_barras, textposition='outside', textfont=dict(color="white", size=10)
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

        max_y_hist = df_agg[m_graf].max() if not df_agg.empty else 1
        if max_y_hist == 0: max_y_hist = 1
        
        hist_images = []
        for _, row in df_agg.iterrows():
            if 'partido' in str(row['Tipo_Dia_Oficial']).lower() and pd.notna(row.get('Escudo')) and str(row.get('Escudo')).startswith('http'):
                hist_images.append(dict(
                    source=row['Escudo'],
                    x=row['Fecha'],
                    y=row[m_graf] / 2,
                    xref="x", yref="y",
                    sizex=0.8,
                    sizey=max_y_hist * 0.35,
                    xanchor="center", yanchor="middle"
                ))

        fig_hist.update_layout(
            images=hist_images,
            template="plotly_dark", height=150, margin=dict(l=0, r=0, t=20, b=0), 
            xaxis=dict(type='category', visible=False), 
            yaxis=dict(visible=False), 
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False
        )

        hist_key = f"hist_chart_{st.session_state.hist_grafico_key}"
        try:
            seleccion_hist = st.plotly_chart(
                fig_hist, 
                width="stretch", 
                config={'displayModeBar': False}, 
                on_select="rerun", 
                selection_mode=["points"], 
                key=hist_key
            )
            if seleccion_hist and hasattr(seleccion_hist, 'selection'):
                puntos_h = getattr(seleccion_hist.selection, 'points', [])
                if puntos_h:
                    p = puntos_h[0]
                    fecha_raw = p.get('x')
                    if not fecha_raw and p.get('customdata'):
                        cd = p.get('customdata')
                        fecha_raw = cd[0] if isinstance(cd, list) else cd
                    
                    if fecha_raw:
                        fecha_click = str(fecha_raw).split(' ')[0].split('T')[0].strip()
                        if fecha_click in fechas_disp:
                            if st.session_state.get('fecha_hist_pulsada') == fecha_click:
                                st.session_state.fecha_hist_pulsada = None
                                nueva_fecha = fechas_disp[0] if fechas_disp else None
                            else:
                                st.session_state.fecha_hist_pulsada = fecha_click
                                nueva_fecha = fecha_click
                            
                            if nueva_fecha != st.session_state.fecha_maestra:
                                st.session_state.fecha_maestra = nueva_fecha
                                st.session_state.hist_grafico_key += 1
                                st.rerun()
        except Exception:
            st.plotly_chart(fig_hist, width="stretch", config={'displayModeBar': False})
    else:
        st.info(f"No hay sesiones de tipo '{filtro_tipo_sesion}' en los últimos 28 días.")

with c_info:
    with st.expander("👁️ Jugadores ≥ 90% Vmax hoy"):
        if not alcanzan_90.empty:
            render_html(chips_html(alcanzan_90['Nombre'].tolist(), VERDE,
                                   {r['Nombre']: f"{r['Porcentaje_Vmax']:.0f}%" for _, r in alcanzan_90.iterrows()}))
        else: st.caption("Ninguno")

# =============================================================================
# 5. BULLET CHARTS
# =============================================================================
df_sesion_validos = df_sesion[df_sesion['Valido_Media'] == True] if not df_sesion.empty else df_sesion
medias_sesion = {m: df_sesion_validos[m].mean() if not df_sesion_validos.empty else 0.0 for m in metricas_todas}
target_programado_min = {m: df_sesion_validos[f'Target_Min_{m}'].mean() if not df_sesion_validos.empty else 0.0 for m in metricas_todas}
target_programado_max = {m: df_sesion_validos[f'Target_Max_{m}'].mean() if not df_sesion_validos.empty else 0.0 for m in metricas_todas}

def pintar_bullet(metrica, nombre_mostrar, row_col):
    val = medias_sesion.get(metrica, 0)
    t_min = target_programado_min.get(metrica, 0)
    t_max = target_programado_max.get(metrica, 0)
    
    texto_val = f"{val:.1f}" if val < 100 else f"{val:.0f}"
    max_range = max(val, t_max) * 1.2 if max(val, t_max) > 0 else 10
    
    color_bar = "rgba(148,163,184,0.55)"          # dentro del rango programado: neutro
    if t_max > 0 and val < t_min: color_bar = AZUL  # por debajo
    elif t_max > 0 and val > t_max: color_bar = ROJO  # por encima
    
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
        st.markdown(f"<p style='margin-bottom:2px; font-size:14px; color:white; font-weight:bold;'>{nombre_mostrar}</p>", unsafe_allow_html=True)
        fig.update_xaxes(fixedrange=True); fig.update_yaxes(fixedrange=True)
        mostrar_fig(fig, key=f"bullet_{metrica}")

st.caption("Media del grupo vs rango programado (franja verde entre líneas amarillas). "
           "Gris = dentro del rango · azul = por debajo · rojo = por encima.")
r1_1, r1_2, r1_3, r1_4 = st.columns(4)
pintar_bullet('Dist_Total', 'Distancia total (m)', r1_1)
pintar_bullet('Dist_18', 'Distancia > 18 km/h', r1_2)
pintar_bullet('Dist_25', 'Distancia > 25 km/h', r1_3)
pintar_bullet('Dist_28', 'Distancia > 28 km/h', r1_4)
r2_1, r2_2, r2_3, r2_4 = st.columns(4)
pintar_bullet('Sprints', 'Sprints', r2_1)
pintar_bullet('Accels', 'Aceleraciones', r2_2)
pintar_bullet('Decels', 'Desaceleraciones', r2_3)
pintar_bullet('Player_Load', 'Player Load', r2_4)

# =============================================================================
# 6. TABLA INDIVIDUAL (ANÁLISIS POR CATEGORÍA TÁCTICA)
# =============================================================================
st.markdown("---")
st.markdown("### Desglose por jugador")

metricas_tabla = {'Dist_Total': 'Dist. Total', 'Dist_18': 'Dist. >18', 'Dist_25': 'Dist. >25', 'Dist_28': 'Dist. >28', 'Sprints': 'Sprints', 'Accels': 'Acel.', 'Decels': 'Desac.', 'Acc_Max': 'Ac. Máx', 'Dec_Max': 'Dec. Máx', 'Top_Speed': 'V. Máx', 'Player_Load': 'Load'}
df_sesion_tabla = df_sesion.copy()

orden_tactico = {'defensa central': 1, 'defensa lateral': 2, 'mediocentro': 3, 'mediapunta': 4, 'extremo': 5, 'delantero': 6}
df_sesion_tabla['Peso_Pos'] = df_sesion_tabla['Posicion'].astype(str).str.lower().str.strip().map(orden_tactico).fillna(99)
df_sesion_tabla = df_sesion_tabla.sort_values(['Peso_Pos', 'Nombre'])

# ---------- Vista (tabla / comparativa) y filtros propios de este bloque ----------
VISTA_TABLA, VISTA_COMP = "📋 Tabla de la sesión", "📊 Comparativa entre jugadores"
vista_desglose = st.segmented_control("Vista", [VISTA_TABLA, VISTA_COMP], default=VISTA_TABLA, key="vista_desglose",
                                      label_visibility="collapsed") or VISTA_TABLA
es_comparativa = vista_desglose == VISTA_COMP

def peso_pos(p):
    return orden_tactico.get(str(p).lower().strip(), 99)
pos_opts = sorted([p for p in df_master['Posicion'].dropna().astype(str).unique() if p.lower() not in ('nan', 'sin posición')],
                  key=lambda p: (peso_pos(p), p))
pos_tabla = st.pills("Posiciones", pos_opts, selection_mode="multi", key="pills_pos_tabla",
                     help="Pulsa una o varias posiciones. Sin selección = todas.") or []
pos_de = df_master.drop_duplicates('Nombre', keep='last').set_index('Nombre')['Posicion'].astype(str).to_dict()
jug_pool = sorted(df_master[df_master['Posicion'].isin(pos_tabla)]['Nombre'].unique() if pos_tabla else df_master['Nombre'].unique(),
                  key=lambda n: (peso_pos(pos_de.get(n, '')), nombre_bonito(n)))
jug_pool = sin_exjugadores(jug_pool)   # jugadores de baja: fuera de la tabla y de las barras (sí cuentan en la media de su posición)

# Casillas de jugadores (todas marcadas por defecto)
def _marcar(valor):
    for n in jug_pool:
        st.session_state[f"chk_jug_{n}"] = valor
for n in jug_pool:
    st.session_state.setdefault(f"chk_jug_{n}", True)
n_marcados = sum(st.session_state[f"chk_jug_{n}"] for n in jug_pool)
with st.expander(f"☑️ Jugadores ({n_marcados}/{len(jug_pool)} seleccionados)"):
    b1, b2, _ = st.columns([1, 1, 3])
    b1.button("Marcar todos", on_click=_marcar, args=(True,), key="chk_todos", width="stretch")
    b2.button("Desmarcar todos", on_click=_marcar, args=(False,), key="chk_ninguno", width="stretch")
    n_cols = 2 if movil else 4
    cols_chk = st.columns(n_cols)
    for i, n in enumerate(jug_pool):
        cols_chk[i % n_cols].checkbox(nombre_bonito(n), key=f"chk_jug_{n}")
jug_tabla = [n for n in jug_pool if st.session_state.get(f"chk_jug_{n}", True)]

if pos_tabla:
    df_sesion_tabla = df_sesion_tabla[df_sesion_tabla['Posicion'].isin(pos_tabla)]
df_sesion_tabla = df_sesion_tabla[df_sesion_tabla['Nombre'].isin(jug_tabla)]

if es_comparativa:
    df_sesion_tabla = df_sesion_tabla.iloc[0:0]   # no se dibuja la tabla
    metricas_comp = {'Distancia total (m)': 'Dist_Total', 'Distancia > 18 km/h (m)': 'Dist_18', 'Distancia > 25 km/h (m)': 'Dist_25',
                     'Distancia > 28 km/h (m)': 'Dist_28', 'Sprints': 'Sprints', 'Aceleraciones': 'Accels', 'Desaceleraciones': 'Decels',
                     'Acel + desacel': 'Acc_Dec', 'V. máx (km/h)': 'Top_Speed', 'Acel. máx (m/s²)': 'Acc_Max',
                     'Decel. máx (m/s²)': 'Dec_Max', 'Player Load': 'Player_Load', 'Carga sRPE (UA)': 'Carga_UA'}
    f_min = pd.to_datetime(df_master['Fecha']).min().date()
    e1, e2 = st.columns([1.4, 1.6], vertical_alignment="bottom")
    with e1:
        metrica_comp_lbl = st.selectbox("Variable", list(metricas_comp.keys()), key="comp_metrica")
    with e2:
        rango_comp = st.date_input("Rango de fechas (media de las sesiones del rango; elige un solo día para ver una sesión)",
                                   value=(max(f_min, fecha_datetime - timedelta(days=56)), fecha_datetime),
                                   min_value=f_min, max_value=fecha_datetime, format="DD/MM/YYYY", key="comp_rango")
    m_comp = metricas_comp[metrica_comp_lbl]
    if isinstance(rango_comp, (list, tuple)) and len(rango_comp) == 2:
        c_desde, c_hasta = rango_comp
    else:
        c_desde = rango_comp[0] if isinstance(rango_comp, (list, tuple)) else rango_comp; c_hasta = c_desde

    dfc = df_master.copy()
    dfc['Dia'] = pd.to_datetime(dfc['Fecha'])
    dfc = dfc[(dfc['Dia'].dt.date >= c_desde) & (dfc['Dia'].dt.date <= c_hasta)]
    dfc['Sesion'] = dfc['Tipo_Dia_Oficial'].apply(etiqueta_sesion)
    tipos_opts = sorted(dfc['Sesion'].dropna().unique(), key=lambda t: (t != 'Partido', t))
    if "comp_tipos" in st.session_state:
        st.session_state["comp_tipos"] = [t for t in (st.session_state["comp_tipos"] or []) if t in tipos_opts]
        tipos_sel = st.pills("Tipo de sesión", tipos_opts, selection_mode="multi", key="comp_tipos") or tipos_opts
    else:
        tipos_sel = st.pills("Tipo de sesión", tipos_opts, selection_mode="multi", default=tipos_opts, key="comp_tipos") or tipos_opts
    dfc = dfc[dfc['Sesion'].isin(tipos_sel)]
    if m_comp == 'Dec_Max':
        dfc[m_comp] = dfc[m_comp].abs()   # frenada: se compara en valor absoluto (más alto = frenada más intensa)

    # Media de la posición: con TODOS los jugadores de esa posición (aunque no estén marcados), para que sea una referencia estable
    medias_pos = dfc.groupby('Posicion')[m_comp].mean().to_dict()
    res = dfc[dfc['Nombre'].isin(jug_tabla)].groupby('Nombre').agg(Valor=(m_comp, 'mean'), N=(m_comp, 'count')).reset_index()
    res['Posicion'] = res['Nombre'].map(pos_de).fillna('Sin posición')
    res = res.dropna(subset=['Valor'])

    if res.empty:
        st.info("No hay sesiones con esos filtros.")
    else:
        res['Media_pos'] = res['Posicion'].map(medias_pos)
        res['Dif'] = (res['Valor'] / res['Media_pos'] - 1) * 100
        res['_p'] = res['Posicion'].apply(peso_pos)
        res = res.sort_values(['_p', 'Posicion', 'Valor'], ascending=[True, True, False]).reset_index(drop=True)
        # Posición en el eje: un hueco entre grupos de posición
        xs, x, previa = [], 0, None
        for pos_j in res['Posicion']:
            if previa is not None and pos_j != previa:
                x += 1
            xs.append(x); x += 1; previa = pos_j
        res['x'] = xs
        UMBRAL = 15  # % respecto a la media de su posición para resaltar
        colores = [NARANJA if d > UMBRAL else AZUL if d < -UMBRAL else "rgba(148,163,184,0.55)" for d in res['Dif'].fillna(0)]
        txt_rango = fecha_es(c_desde) if c_desde == c_hasta else f"{fecha_es(c_desde, corta=True)}–{fecha_es(c_hasta, corta=True)}"
        es_dec = m_comp in ('Acc_Max', 'Dec_Max', 'Top_Speed')
        fmt = ".2f" if es_dec else ".0f"

        def construir(vertical):
            fig = go.Figure()
            # sombreado + línea con la media de cada posición
            for pos_j, g in res.groupby('Posicion', sort=False):
                mp = medias_pos.get(pos_j)
                if mp is None or pd.isna(mp): continue
                a0, a1 = g['x'].min() - 0.45, g['x'].max() + 0.45
                if vertical:
                    fig.add_shape(type="rect", x0=a0, x1=a1, y0=0, y1=mp, fillcolor="rgba(148,163,184,0.10)", line_width=0, layer="below")
                    fig.add_shape(type="line", x0=a0, x1=a1, y0=mp, y1=mp, line=dict(color=TEXTO, width=2, dash="dash"))
                    # nombre de la posición y su media ARRIBA del gráfico, para no pisar las barras
                    fig.add_annotation(x=(a0 + a1) / 2, y=1.0, yref="paper", text=f"<b>{pos_j}</b><br>media {mp:{fmt}}",
                                       showarrow=False, yanchor="bottom", font=dict(size=10, color=NEUTRO_TEXTO))
                else:
                    fig.add_shape(type="rect", y0=a0, y1=a1, x0=0, x1=mp, fillcolor="rgba(148,163,184,0.10)", line_width=0, layer="below")
                    fig.add_shape(type="line", y0=a0, y1=a1, x0=mp, x1=mp, line=dict(color=TEXTO, width=2, dash="dash"))
                    # etiqueta en el hueco que hay encima de cada grupo
                    fig.add_annotation(y=g['x'].min() - 1, x=0, text=f"<b>{pos_j}</b> · media {mp:{fmt}}", showarrow=False,
                                       xanchor="left", yanchor="middle", font=dict(size=10, color=NEUTRO_TEXTO))
            hover = [f"<b>{nombre_bonito(n)}</b> ({p})<br>{metrica_comp_lbl}: {v:{fmt}}<br>Media {p}: {mp:{fmt}} ({d:+.0f}%)<br>{k} sesiones"
                     for n, p, v, mp, d, k in zip(res['Nombre'], res['Posicion'], res['Valor'], res['Media_pos'], res['Dif'].fillna(0), res['N'])]
            # valor escrito solo en las barras resaltadas (el resto, al pasar el cursor)
            textos = [f"{v:{fmt}}" if c != "rgba(148,163,184,0.55)" else "" for v, c in zip(res['Valor'], colores)]
            if vertical:
                fig.add_trace(go.Bar(x=res['x'], y=res['Valor'], marker_color=colores, text=textos, textposition="outside",
                                     textfont=dict(size=10, color=TEXTO), hovertext=hover, hoverinfo="text", width=0.75))
                estilo_fig(fig, height=500, leyenda_abajo=False, titulo=f"{metrica_comp_lbl} · media {txt_rango}")
                fig.update_layout(margin=dict(t=90))
                fig.update_xaxes(tickvals=res['x'], ticktext=[nombre_corto(n) for n in res['Nombre']], tickangle=-45)
                fig.update_yaxes(range=[0, max(res['Valor'].max(), max(medias_pos.values()) if medias_pos else 0) * 1.12])
            else:
                fig.add_trace(go.Bar(y=res['x'], x=res['Valor'], orientation="h", marker_color=colores, text=textos,
                                     textposition="outside", textfont=dict(size=10, color=TEXTO), hovertext=hover, hoverinfo="text", width=0.75))
                estilo_fig(fig, height=max(320, 22 * (res['x'].max() + 3) + 90), leyenda_abajo=False,
                           titulo=f"{metrica_comp_lbl} · media {txt_rango}")
                fig.update_yaxes(tickvals=res['x'], ticktext=[nombre_corto(n) for n in res['Nombre']],
                                 range=[res['x'].max() + 0.7, -1.6], tickfont=dict(size=10))
                fig.update_xaxes(range=[0, res['Valor'].max() * 1.25])
            fig.update_layout(showlegend=False, bargap=0.2)
            return fig

        st.caption(f"Cada barra = media del jugador en las sesiones del rango. Sombreado y línea discontinua = media de su posición. "
                   f"Naranja = más de un {UMBRAL}% por encima de la media de su posición · azul = más de un {UMBRAL}% por debajo.")
        mostrar_segun_pantalla(construir(True), construir(False), key="comp_barras", movil=movil)
        if m_comp == 'Dec_Max':
            st.caption("Decel. máx se muestra en valor absoluto: más alto = frenada más intensa.")

# La tabla compacta se ve automáticamente en el móvil; la completa en pantallas anchas.
# Con "Vista móvil" activada en el lateral, se muestra solo la compacta en cualquier pantalla.
if not df_sesion_tabla.empty:
    clase_compacta = "" if movil else "solo-movil"
    render_html(f"<div class='{clase_compacta}' style='color:{NEUTRO_TEXTO}; font-size:.8rem'>Azul = por debajo del rango programado · "
                "rojo = por encima · gris = dentro. %Vmax respecto a su máximo de 28 días.</div>")
    cols_c = [('Dist_Total', 'Dist', 0), ('Dist_18', '>18', 0), ('Dist_25', '>25', 0), ('Accels', 'Acel', 0), ('Decels', 'Dec', 0)]
    filas = ""
    for _, row in df_sesion_tabla.iterrows():
        celdas = ""
        for m, _, dec in cols_c:
            v, tmin, tmax = row[m], row[f'Target_Min_{m}'], row[f'Target_Max_{m}']
            col = AZUL if v < tmin else (ROJO if (tmax > 0 and v > tmax) else NEUTRO_TEXTO)
            peso = "800" if col != NEUTRO_TEXTO else "400"
            celdas += f"<td style='padding:6px 4px; text-align:right; color:{col}; font-weight:{peso}'>{v:.{dec}f}</td>"
        vm = df_master[(df_master['Nombre'] == row['Nombre']) & (df_master['Fecha'] >= fecha_inicio_vmax.strftime('%Y-%m-%d')) & (df_master['Fecha'] <= fecha_sel)]['Top_Speed'].max()
        pv = (row['Top_Speed'] / vm * 100) if vm and vm > 0 else np.nan
        col_v = VERDE if pd.notna(pv) and pv >= 90 else NEUTRO_TEXTO
        celdas += f"<td style='padding:6px 4px; text-align:right; color:{col_v}'>{'' if pd.isna(pv) else f'{pv:.0f}%'}</td>"
        rpe = row['RPE_G']
        celdas += f"<td style='padding:6px 4px; text-align:right; color:{ROJO if pd.notna(rpe) and rpe >= 8 else NEUTRO_TEXTO}'>{'–' if pd.isna(rpe) else f'{rpe:.1f}'}</td>"
        filas += (f"<tr style='border-bottom:1px solid {BORDE}'><td class='col-jug' style='padding:6px 4px; white-space:nowrap; color:{TEXTO}'>"
                  f"{nombre_corto(row['Nombre'])}<div style='font-size:10px; color:{NEUTRO_TEXTO}'>{row['Posicion']}</div></td>{celdas}</tr>")
    cab = "".join([f"<th style='padding:6px 4px; text-align:right'>{t}</th>" for _, t, _ in cols_c]) + \
          "<th style='padding:6px 4px; text-align:right'>%Vmax</th><th style='padding:6px 4px; text-align:right'>RPE</th>"
    render_html(f"""<style>.tabla-compacta td.col-jug {{ position: sticky; left: 0; background: #0E1117; }}</style>
        <div class="{clase_compacta}" style="overflow-x:auto"><table class="tabla-compacta" style="border-collapse:collapse; width:100%; font-size:12px">
        <thead><tr style="color:{NEUTRO_TEXTO}; border-bottom:2px solid {BORDE}"><th style="text-align:left; padding:6px 4px">Jugador</th>{cab}</tr></thead>
        <tbody>{filas}</tbody></table></div>""")

if not df_sesion_tabla.empty and not movil:
    
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
        if valor < t_min: c_barra = AZUL
        elif valor > t_max and t_max > 0: c_barra = ROJO
        else: c_barra = "rgba(148,163,184,0.55)"
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
        color_target_achieved = "#2ECC71" if target_90 > 0 and valor_abs >= target_90 else "#A0AEC0"
        return f"""
        <div style="position:relative; width:100%; min-width:50px; max-width:90px; height:18px; background-color:rgba(255,255,255,0.1); border-radius:2px; margin:0 auto; overflow:visible;">
            <div style="position:absolute; left:0; top:0; height:100%; width:{pct_fill}%; background-color:{color_target_achieved}; border-radius:2px; z-index:2;"></div>
            <div style="position:absolute; left:{pct_target}%; top:-2px; height:22px; width:2px; background-color:#F1C40F; z-index:3;"></div>
            <div style="position:absolute; left:4px; top:1px; font-size:11px; font-weight:bold; color:white; z-index:4; text-shadow:1px 1px 1px black;">{t_val}</div>
        </div>
        """

    html = """
    <style>
    .tabla-jugadores tbody tr { transition: background-color 0.2s ease; }
    .tabla-jugadores tbody tr:hover { background-color: rgba(255, 255, 255, 0.08) !important; }
    .tabla-jugadores td.col-jug { position: sticky; left: 0; background: #0E1117; z-index: 5; }
    </style>
    <div class="solo-pc" style="overflow-x: auto; padding-bottom: 20px;">
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
        html += f"<td class='col-jug' style='padding:8px; text-align:left; white-space:nowrap;'>{nombre_bonito(jugador)}</td>"
        
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
                color_pct = "#2ECC71" if pct_max >= 90 else "#A0AEC0"
                html += f"<td style='padding:5px; background-color:transparent; color:{color_pct}; font-weight:bold; font-size:11px;'>{pct_max:.0f}%</td>"
            
            elif False:   # (antes Dist_28/Sprints usaban el 100% de partido todos los días)
                pos_jug = pos
                t_ref = dict_ref_posicion.get(pos_jug, fallbacks_profesionales).get(m, fallbacks_profesionales[m])
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
        
        rpe_txt = f"{rpe_val:.1f}" if pd.notna(rpe_val) else "–"
        html += f"<td style='padding:5px; border-left:1px solid #444; font-weight:bold; background-color:{'#E74C3C' if pd.notna(rpe_val) and rpe_val>=8 else 'transparent'};'>{rpe_txt}</td></tr>"
        
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
if df_sesion_tabla.empty and not es_comparativa:
    st.info("No hay datos para esta fecha con esos filtros.")

# =============================================================================
# 6.B RATIO AGUDO:CRÓNICO PONDERADO (ACWR EWMA 7:21 DÍAS)
# =============================================================================
st.markdown("---")
st.markdown("### Ratio Agudo:Crónico PONDERADO (EWMA 7:21 Días)")
st.caption("Carga Aguda (7d) vs Carga Crónica (21d) con ponderación exponencial. Los días recientes tienen mayor peso fisiológico.")

opciones_metrica_acwr = {
    'Distancia > 25 km/h (m)': 'Dist_25',
    'Player Load': 'Player_Load',
    'Distancia Total (m)': 'Dist_Total',
    'Distancia > 18 km/h (m)': 'Dist_18',
    'Aceleraciones + Desaceleraciones': 'Acc_Dec'
}

# El jugador se elige PULSANDO SU BARRA; para volver, botón "Ver toda la plantilla"
if "acwr_jug" not in st.session_state:
    st.session_state["acwr_jug"] = "Toda la plantilla"
    st.session_state["acwr_n"] = 0
jugador_acwr_sel = st.session_state["acwr_jug"]
col_ac1, col_ac2 = st.columns([2, 1], vertical_alignment="bottom")
with col_ac1:
    metrica_acwr_lbl = st.selectbox("🎯 Métrica para Ratio ACWR:", list(opciones_metrica_acwr.keys()), index=0, key="sel_metrica_acwr")
with col_ac2:
    if jugador_acwr_sel != "Toda la plantilla" and st.button("👥 Ver toda la plantilla", key="acwr_volver", width="stretch"):
        st.session_state["acwr_jug"] = "Toda la plantilla"
        st.session_state["acwr_n"] += 1
        st.rerun()

metrica_acwr_key = opciones_metrica_acwr[metrica_acwr_lbl]
df_acwr_total = quitar_exjugadores(calcular_acwr_ewma(df_master, metrica=metrica_acwr_key, dias_agudo=7, dias_cronico=21), 'Nombre')

if not df_acwr_total.empty:
    if jugador_acwr_sel == "Toda la plantilla":
        df_acwr_fecha = df_acwr_total[df_acwr_total['Fecha'] == fecha_sel].copy()
        # Jugadores sin carga crónica (lesionados largos, altas recientes): no se dibujan como "0.00"
        sin_datos = df_acwr_fecha[df_acwr_fecha['EWMA_Cronico'] <= 1.0]['Nombre'].tolist()
        df_acwr_fecha = df_acwr_fecha[df_acwr_fecha['EWMA_Cronico'] > 1.0]

        def c_acwr(r):
            if r > 1.5: return ROJO
            if r > 1.3: return NARANJA
            if r < 0.8: return AZUL
            return NEUTRO
        colores = [c_acwr(r) for r in df_acwr_fecha['ACWR']]
        textos = [f"{r:.2f}" if c != NEUTRO else "" for r, c in zip(df_acwr_fecha['ACWR'], colores)]
        args_acwr = dict(
            textos=textos, orden="desc",
            hover=[f"{nombre_bonito(n)}: {r:.2f}<br>(pulsa para ver su evolución)" for n, r in zip(df_acwr_fecha['Nombre'], df_acwr_fecha['ACWR'])],
            ids=df_acwr_fecha['Nombre'].tolist(),
            eje_titulo=f"ACWR EWMA 7:21 · {metrica_acwr_lbl}",
            lineas=[{"x": 0.8, "color": AZUL, "texto": "0.8"}, {"x": 1.3, "color": NARANJA, "texto": "1.3"},
                    {"x": 1.5, "color": ROJO, "texto": "1.5"}],
            rango=[0, max(1.9, float(df_acwr_fecha['ACWR'].max() or 0) * 1.15)])
        fig_team_acwr = barras_jugadores(df_acwr_fecha['Nombre'], df_acwr_fecha['ACWR'], colores, **args_acwr)
        fig_team_acwr_pc = barras_jugadores(df_acwr_fecha['Nombre'], df_acwr_fecha['ACWR'], colores, vertical=True, **args_acwr)
        st.caption(f"{fecha_es(fecha_sel)} · gris = rango 0.8-1.3 · naranja 1.3-1.5 · rojo > 1.5 · azul < 0.8 · "
                   "**pulsa la barra de un jugador para ver su evolución**")
        evs = mostrar_segun_pantalla(fig_team_acwr_pc, fig_team_acwr, key=f"acwr_plantilla_{st.session_state['acwr_n']}",
                                     movil=movil, on_select="rerun", selection_mode="points")
        pulsado = nombre_pulsado(evs)
        if pulsado:
            st.session_state["acwr_jug"] = pulsado
            st.session_state["acwr_n"] += 1
            st.rerun()
        if sin_datos:
            st.caption("Sin carga crónica suficiente (no se calcula): " + ", ".join(nombre_bonito(n) for n in sin_datos))

    else:
        df_p_acwr = df_acwr_total[df_acwr_total['Nombre'] == jugador_acwr_sel].sort_values(by='Fecha_dt')
        
        fig_p_timeline = go.Figure()

        fig_p_timeline.add_trace(go.Bar(
            x=df_p_acwr['Fecha'],
            y=df_p_acwr[metrica_acwr_key],
            name='Carga Diaria',
            marker_color='#3498DB',
            opacity=0.6,
            yaxis='y1'
        ))

        fig_p_timeline.add_trace(go.Scatter(
            x=df_p_acwr['Fecha'],
            y=df_p_acwr['EWMA_Cronico'],
            name='Carga Crónica (EWMA 21d)',
            fill='tozeroy',
            fillcolor='rgba(155, 89, 182, 0.2)',
            line=dict(color='#9B59B6', width=2),
            yaxis='y1'
        ))

        colors_acwr_points = []
        for r in df_p_acwr['ACWR']:
            if 0.8 <= r <= 1.3: colors_acwr_points.append('#2ECC71')
            elif 1.3 < r <= 1.5: colors_acwr_points.append('#F1C40F')
            elif r > 1.5: colors_acwr_points.append('#E74C3C')
            else: colors_acwr_points.append('#3498DB')

        fig_p_timeline.add_trace(go.Scatter(
            x=df_p_acwr['Fecha'],
            y=df_p_acwr['ACWR'],
            name='Ratio ACWR (EWMA 7:21)',
            mode='lines+markers',
            line=dict(color='#E74C3C', width=2.5),
            marker=dict(size=7, color=colors_acwr_points, line=dict(width=1, color='white')),
            yaxis='y2'
        ))

        max_acwr_p = df_p_acwr['ACWR'].max() if not df_p_acwr.empty else 1.5
        fig_p_timeline.update_layout(
            title=f"Evolución ACWR EWMA 7:21 · {nombre_bonito(jugador_acwr_sel)} ({metrica_acwr_lbl})",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title="Fecha", showgrid=False, tickangle=-45),
            yaxis=dict(title=f"Carga Diaria / Crónica ({metrica_acwr_lbl})", showgrid=True, gridcolor='rgba(255,255,255,0.1)', side='left'),
            yaxis2=dict(title="Ratio ACWR", overlaying='y', side='right', range=[0, max(max_acwr_p * 1.25, 2.0)], showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=480
        )
        st.plotly_chart(fig_p_timeline, width="stretch")

# =============================================================================
# 7. ANÁLISIS DE EXIGENCIA COMPETITIVA (PARTIDOS) CON INTERACCIÓN DIRECTA
# =============================================================================
st.markdown("---")
st.markdown("### Análisis de partidos")

df_partidos_analisis = df_master[(df_master['Tipo_Dia_Oficial'].str.lower().str.contains('partido')) & (df_master['Valido_Media'] == True)]

if not df_partidos_analisis.empty and not df_calendario.empty:
    df_partidos_agg = df_partidos_analisis.groupby('Fecha')[metricas_todas].mean().reset_index()
    df_scatter = pd.merge(df_partidos_agg, df_calendario, on='Fecha', how='inner')
    
    col_sc1, col_sc2 = st.columns([1.8, 1.2])

    with col_sc1:
        f1, f2 = st.columns(2)
        # Pulsar un botón = ver SOLO esos partidos. Sin ningún botón pulsado = todos.
        with f1:
            sel_res = st.pills("Resultado", ["Ganados", "Empatados", "Perdidos"], selection_mode="multi", key="pills_res_v2")
        with f2:
            sel_loc = st.pills("Campo", ["Casa", "Fuera"], selection_mode="multi", key="pills_loc_v2")
        valid_results = [{"Ganados": "G", "Empatados": "E", "Perdidos": "P"}[x] for x in (sel_res or ["Ganados", "Empatados", "Perdidos"])]
        valid_locs = list(sel_loc or ["Casa", "Fuera"])

        df_scatter_filt = df_scatter[
            (df_scatter['Resultado_Codificado'].isin(valid_results)) & 
            (df_scatter['Local_Visitante'].isin(valid_locs))
        ].reset_index(drop=True)
        
        if not df_scatter_filt.empty:
            st.markdown("<p style='font-size:14px; color:#A0AEC0; margin-bottom: 0px;'>Pincha en los escudos para cargar el partido arriba, o añadir/quitar del radar 👉</p>", unsafe_allow_html=True)
            st.caption("Las líneas discontinuas son la media de TODOS los partidos y no cambian al filtrar.")
            
            # Ejes y medias con TODOS los partidos: no se mueven al filtrar, para comparar contra la referencia global
            x_min, x_max = df_scatter['Dist_Total'].min(), df_scatter['Dist_Total'].max()
            y_min, y_max = df_scatter['Dist_18'].min(), df_scatter['Dist_18'].max()
            
            if (x_max - x_min) < 1000:
                x_center = (x_max + x_min) / 2
                x_min, x_max = x_center - 500, x_center + 500
            if (y_max - y_min) < 100:
                y_center = (y_max + y_min) / 2
                y_min, y_max = y_center - 50, y_center + 50
                
            r_x = x_max - x_min
            r_y = y_max - y_min
            
            fig_sc = go.Figure()
            hover_text = df_scatter_filt['Rival'] + '<br>' + df_scatter_filt['Fecha'] + ' (' + df_scatter_filt['Local_Visitante'] + ')<br>Resultado: ' + df_scatter_filt['Resultado']
            
            fig_sc.add_trace(go.Scatter(
                x=df_scatter_filt['Dist_Total'], y=df_scatter_filt['Dist_18'],
                customdata=df_scatter_filt['Fecha'], 
                mode='markers', marker=dict(size=40, color='rgba(0,0,0,0)'),
                text=hover_text, hoverinfo='text', hoverlabel=dict(bgcolor="#2C3E50", font_size=14)
            ))
            
            images = []
            for _, row in df_scatter_filt.iterrows():
                images.append(dict(
                    source=row['Escudo'],
                    x=row['Dist_Total'], y=row['Dist_18'],
                    xref="x", yref="y",
                    sizex=r_x * 0.15, sizey=r_y * 0.15, 
                    xanchor="center", yanchor="middle"
                ))
            
            mean_x = df_scatter['Dist_Total'].mean()
            mean_y = df_scatter['Dist_18'].mean()
            fig_sc.add_vline(x=mean_x, line=dict(color='white', width=1, dash='dash'), opacity=0.5)
            fig_sc.add_hline(y=mean_y, line=dict(color='white', width=1, dash='dash'), opacity=0.5)
            
            fig_sc.update_layout(
                images=images, template="plotly_dark", height=580,
                xaxis=dict(title="Distancia Total (m)", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[x_min - r_x*0.1, x_max + r_x*0.1]),
                yaxis=dict(title="Distancia > 18 km/h (m)", showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[y_min - r_y*0.1, y_max + r_y*0.1]),
                plot_bgcolor='rgba(0,0,0,0.2)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0)
            )
            
            scatter_key = f"scatter_{st.session_state.grafico_key}"
            try:
                seleccion = st.plotly_chart(fig_sc, width="stretch", config={'displayModeBar': False}, on_select="rerun", selection_mode=["points", "box", "lasso"], key=scatter_key)
                if seleccion and hasattr(seleccion, 'selection'):
                    puntos = getattr(seleccion.selection, 'points', [])
                    hubo_cambios = False
                    for p in puntos:
                        cd = p.get('customdata')
                        if cd:
                            val = cd[0] if isinstance(cd, list) else cd
                            if val in st.session_state.partidos_radar:
                                st.session_state.partidos_radar.remove(val)
                                if st.session_state.partidos_radar:
                                    st.session_state.fecha_maestra = st.session_state.partidos_radar[-1]
                                hubo_cambios = True
                            else:
                                st.session_state.partidos_radar.append(val)
                                st.session_state.fecha_maestra = val
                                hubo_cambios = True
                    if hubo_cambios:
                        st.session_state.grafico_key += 1
                        st.rerun()
            except Exception:
                st.plotly_chart(fig_sc, width="stretch", config={'displayModeBar': False})
        else:
            st.info("No hay partidos con el resultado y localización seleccionados.")

    with col_sc2:
        if not df_scatter_filt.empty:
            c_tit1, c_tit2 = st.columns([3, 1.2])
            with c_tit1:
                st.markdown("<p style='font-size:14px; color:#A0AEC0; font-weight:bold; margin-bottom:10px; margin-top:5px;'>Radar de Exigencia Relativa (0-100%)</p>", unsafe_allow_html=True)
            with c_tit2:
                if st.button("🧹 Limpiar", width="stretch"):
                    st.session_state.partidos_radar = []
                    st.session_state.grafico_key += 1
                    st.rerun()
            
            fechas_radar = st.session_state.partidos_radar
            
            if len(fechas_radar) > 0:
                df_radar = df_scatter_filt[df_scatter_filt['Fecha'].isin(fechas_radar)]
                df_maximos = df_scatter[metricas_todas].max().replace(0, 1) 
                nombres_metricas_radar = [metricas_tabla[m] for m in metricas_todas]
                
                colores_radar = ['#3498DB', '#E74C3C', '#2ECC71', '#F1C40F', '#9B59B6', '#E67E22', '#1ABC9C']
                fig_radar = go.Figure()
                
                for i, (_, row) in enumerate(df_radar.iterrows()):
                    vals = (row[metricas_todas] / df_maximos * 100).tolist()
                    color_r = colores_radar[i % len(colores_radar)]
                    color_r_fill = color_r.replace(')', ', 0.4)').replace('rgb', 'rgba') if 'rgb' in color_r else color_r
                    
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=nombres_metricas_radar + [nombres_metricas_radar[0]],
                        fill='toself', name=row['Rival'], marker=dict(color=color_r), fillcolor=color_r_fill, opacity=0.8
                    ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False), angularaxis=dict(tickfont=dict(size=11, color="white"))),
                    showlegend=True, 
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                    template="plotly_dark", height=580, margin=dict(l=40, r=40, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_radar, width="stretch", config={'displayModeBar': False})
            else:
                st.info("👆 Selecciona uno o varios escudos en el gráfico para ver la comparativa aquí.")
else:
    st.info("Aún no hay partidos validados de 60 mins para generar la gráfica comparativa.")