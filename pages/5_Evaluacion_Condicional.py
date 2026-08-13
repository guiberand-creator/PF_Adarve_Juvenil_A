import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
import glob
import requests
import io
import base64
from datetime import datetime
from utils import aplicar_diseno_responsive

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS CSS GLASSMORPHISM
# =============================================================================
aplicar_diseno_responsive()

st.set_page_config(
    page_title="Informe Pro Scouting | Adarve DH",
    page_icon="⚡",
    layout="wide"
)

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.error("⚠️ Acceso no autorizado. Por favor, inicia sesión en la página principal.")
    st.stop()

# FUNCIÓN NORMALIZADORA DE NOMBRES
def norm_nom(texto):
    if pd.isna(texto): return ""
    return " ".join(str(texto).replace('_', ' ').strip().lower().split())

# SELLO FIJO EN SIDEBAR
_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
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

# CSS HUD ESTILO PRO SCOUTING
st.markdown("""
    <style>
    /* FOTO DE CUERPO ENTERO */
    .photo-full-body {
        max-height: 380px;
        width: auto;
        object-fit: contain;
        display: block;
        margin: 0 auto;
        filter: drop-shadow(0px 10px 15px rgba(0, 229, 255, 0.25));
    }
    .photo-placeholder-full {
        height: 380px;
        width: 100%;
        border-radius: 14px;
        background-color: rgba(30, 41, 59, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px dashed rgba(255, 255, 255, 0.15);
    }
    
    /* TARJETAS CUADRADAS KPI EN FILA */
    .kpi-tile-header {
        background: rgba(30, 41, 59, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 22px 12px;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .kpi-label-header {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin-bottom: 6px;
    }
    .kpi-value-header {
        font-size: 24px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
    }
    .kpi-value-cyan { color: #00E5FF !important; }
    .kpi-value-gold { color: #FFC107 !important; }
    .kpi-value-green { color: #00E676 !important; }

    .tag-division {
        text-align: center;
        font-size: 10px !important;
        font-weight: 800 !important;
        letter-spacing: 1.2px !important;
        color: #00E5FF !important;
        margin-top: 2px !important;
        margin-bottom: 6px !important;
        text-transform: uppercase !important;
    }
    
    .hud-card {
        background: rgba(15, 23, 42, 0.75) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 18px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CARGA DE DATOS MULTIFUENTE
# =============================================================================
def descargar_csv_drive(sheet_id, gid="0"):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200: return pd.read_csv(io.StringIO(res.text))
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=30)
def cargar_todo_informes():
    # A) Posiciones (Local)
    r_pos = os.path.join("data", "Posiciones.xlsx")
    df_pos = pd.read_excel(r_pos) if os.path.exists(r_pos) else pd.DataFrame()
    if not df_pos.empty:
        c_n = next((c for c in df_pos.columns if 'jugador' in str(c).lower() or 'nombre' in str(c).lower()), df_pos.columns[0])
        c_p = next((c for c in df_pos.columns if 'posic' in str(c).lower()), df_pos.columns[1])
        c_foto = next((c for c in df_pos.columns if 'foto' in str(c).lower() or 'url' in str(c).lower()), None)
        df_pos = df_pos.rename(columns={c_n: 'Nombre', c_p: 'Posicion'})
        if c_foto: df_pos = df_pos.rename(columns={c_foto: 'Foto_URL'})
        df_pos['Nombre_Norm'] = df_pos['Nombre'].apply(norm_nom)

    # B) Cuestionario Inicial (Google Sheet)
    df_cuest = descargar_csv_drive("1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI", "0")
    if not df_cuest.empty:
        df_cuest.columns = df_cuest.columns.str.strip()
        c_n = next((c for c in df_cuest.columns if 'nombre' in str(c).lower()), df_cuest.columns[0])
        c_fn = next((c for c in df_cuest.columns if 'nacimiento' in str(c).lower()), None)
        c_pos = next((c for c in df_cuest.columns if 'posición' in str(c).lower() or 'posicion' in str(c).lower()), None)
        c_pierna = next((c for c in df_cuest.columns if 'pierna' in str(c).lower()), None)
        
        ren = {c_n: 'Nombre'}
        if c_fn: ren[c_fn] = 'Fecha_Nacimiento'
        if c_pos: ren[c_pos] = 'Posicion_Habitual'
        if c_pierna: ren[c_pierna] = 'Pierna_Dominante'
        df_cuest = df_cuest.rename(columns=ren)
        df_cuest['Nombre_Norm'] = df_cuest['Nombre'].apply(norm_nom)

    # C) Peso (Necesario para Fuerzas Relativas)
    r_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    df_peso = pd.read_excel(r_peso) if os.path.exists(r_peso) else pd.DataFrame()
    if not df_peso.empty:
        df_peso['Nombre_Norm'] = df_peso.iloc[:, 0].apply(norm_nom)
        df_peso['Fecha_dt'] = pd.to_datetime(df_peso.iloc[:, 1], dayfirst=True, errors='coerce')
        df_peso.rename(columns={df_peso.columns[2]: 'Peso'}, inplace=True)

    # D) RPE (Minutos Jugados Oficiales)
    df_rpe = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if not df_rpe.empty:
        cols = df_rpe.columns
        c_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        c_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        c_t = next((c for c in cols if 'tipo' in str(c).lower()), cols[2])
        c_m = next((c for c in cols if 'minuto' in str(c).lower()), cols[3])
        c_cardio = next((c for c in cols if 'cardio' in str(c).lower()), None)
        c_musc = next((c for c in cols if 'muscular' in str(c).lower()), None)
        
        df_rpe['Fecha_dt'] = pd.to_datetime(df_rpe[c_f], dayfirst=True, errors='coerce')
        df_rpe['Fecha'] = df_rpe['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_rpe['Nombre'] = df_rpe[c_n].astype(str).str.strip()
        df_rpe['Nombre_Norm'] = df_rpe['Nombre'].apply(norm_nom)
        df_rpe['Tipo_Sesion'] = df_rpe[c_t].astype(str).str.strip()
        df_rpe['Minutos'] = pd.to_numeric(df_rpe[c_m], errors='coerce').fillna(0)
        
        v_c = pd.to_numeric(df_rpe[c_cardio], errors='coerce').fillna(0) if c_cardio else 0
        v_m = pd.to_numeric(df_rpe[c_musc], errors='coerce').fillna(0) if c_musc else 0
        df_rpe['RPE_G'] = (v_c + v_m) / 2.0

    # E) GPS
    ruta_gps = os.path.join("data", "GPS")
    df_gps_all = pd.DataFrame()
    if os.path.exists(ruta_gps):
        archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
        l_dfs = []
        for f in archivos:
            if "~$" in f: continue
            try:
                dt = pd.read_excel(f, sheet_name=1)
                dt.columns = [str(c).lower().strip() for c in dt.columns]
                def b_c(keys): return next((c for c in dt.columns if any(k in c for k in keys)), None)
                cf, cn = b_c(['fecha', 'date']), b_c(['nombre', 'player'])
                if not cf or not cn: continue
                
                def fn(v):
                    try: return float(str(v).replace(',', '.'))
                    except: return 0.0

                dl = pd.DataFrame()
                dl['Fecha_dt'] = pd.to_datetime(dt[cf], dayfirst=True, errors='coerce')
                dl['Fecha'] = dl['Fecha_dt'].dt.strftime('%d/%m/%Y')
                dl['Nombre'] = dt[cn].astype(str).str.strip()
                dl['Nombre_Norm'] = dl['Nombre'].apply(norm_nom)
                dl['Dist_Total'] = dt[b_c(['distancia total', 'distance'])].apply(fn) if b_c(['distancia total', 'distance']) else 0.0
                dl['Dist_18'] = dt[b_c(['> 18', '>18'])].apply(fn) if b_c(['> 18', '>18']) else 0.0
                dl['Dist_25'] = dt[b_c(['> 25', '>25'])].apply(fn) if b_c(['> 25', '>25']) else 0.0
                accs = dt[b_c(['aceleraciones', 'accel'])].apply(fn) if b_c(['aceleraciones', 'accel']) else 0.0
                decs = dt[b_c(['desaceleraciones', 'decel'])].apply(fn) if b_c(['desaceleraciones', 'decel']) else 0.0
                dl['Acc_Dec'] = accs + decs
                dl['V_MAX'] = dt[b_c(['v. max', 'v.max', 'top speed'])].apply(fn) if b_c(['v. max', 'v.max', 'top speed']) else 0.0
                dl['AC_MAX'] = dt[b_c(['ac. max', 'acc. max'])].apply(fn) if b_c(['ac. max', 'acc. max']) else 0.0
                dl['DEC_MAX'] = dt[b_c(['dec. max', 'desac. max'])].apply(fn) if b_c(['dec. max', 'desac. max']) else 0.0
                l_dfs.append(dl.dropna(subset=['Fecha_dt']))
            except: continue
        if l_dfs:
            df_gps_all = pd.concat(l_dfs, ignore_index=True)
            if df_gps_all['Dist_Total'].max() < 25:
                df_gps_all['Dist_Total'] *= 1000
                df_gps_all['Dist_18'] *= 1000
                df_gps_all['Dist_25'] *= 1000

    # F) Baterías Históricas de Pruebas Condicionales
    df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo = None, None, None, None, None, None, None
    
    r_mov = os.path.join("data", "EVALUACIONES", "MOVILIDAD", "MOVILIDAD.xlsx")
    if os.path.exists(r_mov):
        df_mov = pd.read_excel(r_mov)
        df_mov['Fecha_dt'] = pd.to_datetime(df_mov['Fecha'], dayfirst=True, errors='coerce')
        df_mov['Fecha'] = df_mov['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_mov['Nombre_Norm'] = df_mov['Nombre'].apply(norm_nom)

    r_vam = os.path.join("data", "EVALUACIONES", "AEROBICO", "AEROBICO_5MIN.xlsx")
    if os.path.exists(r_vam):
        df_vam = pd.read_excel(r_vam)
        ren_v = {c: 'Fecha' for c in df_vam.columns if 'fecha' in str(c).lower()}
        ren_v.update({c: 'Nombre' for c in df_vam.columns if 'nombre' in str(c).lower() or 'jugador' in str(c).lower()})
        ren_v.update({c: 'VAM' for c in df_vam.columns if 'vam' in str(c).lower()})
        df_vam.rename(columns=ren_v, inplace=True)
        df_vam['Fecha_dt'] = pd.to_datetime(df_vam['Fecha'], dayfirst=True, errors='coerce')
        df_vam['Fecha'] = df_vam['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_vam['Nombre_Norm'] = df_vam['Nombre'].apply(norm_nom)

    dir_dina = os.path.join("data", "EVALUACIONES", "FUERZA ANALITICA")
    archivo_encontrado = None
    if os.path.exists(os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.xlsx")):
        archivo_encontrado = os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.xlsx")
    elif os.path.exists(os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.csv")):
        archivo_encontrado = os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.csv")
    elif os.path.exists(dir_dina):
        for arch in os.listdir(dir_dina):
            if 'dinamometria' in arch.lower():
                archivo_encontrado = os.path.join(dir_dina, arch)
                break

    if archivo_encontrado:
        if archivo_encontrado.endswith('.xlsx') or archivo_encontrado.endswith('.xls'):
            df_dina = pd.read_excel(archivo_encontrado)
        else:
            try: df_dina = pd.read_csv(archivo_encontrado, sep=';', encoding='utf-8')
            except: df_dina = pd.read_csv(archivo_encontrado, sep=',', encoding='utf-8')

        if df_dina is not None and not df_dina.empty:
            renomb_d = {'Name': 'Nombre', 'Date': 'Fecha', 'Exercise': 'Exercise', 'MaxForce (raw)': 'Fmax_Abs'}
            df_dina.rename(columns=renomb_d, inplace=True)
            df_dina['Fmax_Abs'] = pd.to_numeric(df_dina['Fmax_Abs'].astype(str).str.replace(',', '.'), errors='coerce')
            df_dina['Exercise'] = df_dina['Exercise'].astype(str).str.replace(r'\\u00BA', '', regex=True).str.replace('°', '', regex=False).str.strip()
            df_dina['Fecha_dt'] = pd.to_datetime(df_dina['Fecha'], dayfirst=True, errors='coerce')
            df_dina['Fecha'] = df_dina['Fecha_dt'].dt.strftime('%d/%m/%Y')
            df_dina['Nombre_Norm'] = df_dina['Nombre'].apply(norm_nom)

    r_saltos = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
    if os.path.exists(r_saltos):
        df_saltos = pd.read_excel(r_saltos)
        ren_s = {c: 'Nombre' for c in df_saltos.columns if 'nombre' in str(c).lower() or 'atlet' in str(c).lower()}
        ren_s.update({c: 'Tipo' for c in df_saltos.columns if 'tipo' in str(c).lower()})
        ren_s.update({c: 'Altura' for c in df_saltos.columns if 'altura' in str(c).lower()})
        ren_s.update({c: 'Fecha_Hora' for c in df_saltos.columns if 'fecha' in str(c).lower()})
        df_saltos.rename(columns=ren_s, inplace=True)
        df_saltos['Fecha_dt'] = pd.to_datetime(df_saltos['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_saltos['Fecha'] = df_saltos['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_saltos['Nombre_Norm'] = df_saltos['Nombre'].apply(norm_nom)

    try:
        url_dri = "https://docs.google.com/spreadsheets/d/1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y/export?format=csv"
        df_dri = pd.read_csv(url_dri)
        renomb_dri = {}
        for col in df_dri.columns:
            c_l = str(col).strip().lower()
            if 'nombre' in c_l or 'atlet' in c_l: renomb_dri[col] = 'Nombre'
            elif c_l in ['tc', 'tiempo de contacto']: renomb_dri[col] = 'TC'
            elif 'caida' in c_l or 'caída' in c_l: renomb_dri[col] = 'Caida'
            elif 'altura' in c_l: renomb_dri[col] = 'Altura'
            elif 'fecha' in c_l: renomb_dri[col] = 'Fecha_Hora'
            elif 'tipo' in c_l: renomb_dri[col] = 'Tipo'

        df_dri.rename(columns=renomb_dri, inplace=True)
        df_dri['Fecha_dt'] = pd.to_datetime(df_dri['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_dri['Fecha'] = df_dri['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_dri['Nombre_Norm'] = df_dri['Nombre'].apply(norm_nom)
        
        df_dri['TC'] = pd.to_numeric(df_dri['TC'].astype(str).str.replace(',', '.'), errors='coerce')
        df_dri['Altura'] = pd.to_numeric(df_dri['Altura'].astype(str).str.replace(',', '.'), errors='coerce')
        df_dri['Caida'] = pd.to_numeric(df_dri['Caida'].astype(str).str.replace(',', '.'), errors='coerce').fillna(50)
        
        df_dri['DRI'] = ((df_dri['Altura']/100.0) + (df_dri['Caida']/100.0)) / (9.81 * (df_dri['TC'] ** 2))
        df_dri = df_dri.dropna(subset=['DRI'])
    except: pass

    r_fts = os.path.join("data", "EVALUACIONES", "FUERZA TREN SUPERIOR", "FUERZA_TS.xlsx")
    if os.path.exists(r_fts):
        df_fts = pd.read_excel(r_fts)
        ren_fts = {c: 'Fecha' for c in df_fts.columns if 'fecha' in str(c).lower()}
        ren_fts.update({c: 'Nombre' for c in df_fts.columns if 'nombre' in str(c).lower()})
        ren_fts.update({c: 'Press_Banca' for c in df_fts.columns if 'press' in str(c).lower() or 'banca' in str(c).lower()})
        ren_fts.update({c: 'Dominada' for c in df_fts.columns if 'dominad' in str(c).lower()})
        df_fts.rename(columns=ren_fts, inplace=True)
        df_fts['Fecha_dt'] = pd.to_datetime(df_fts['Fecha'], dayfirst=True, errors='coerce')
        df_fts['Fecha'] = df_fts['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_fts['Nombre_Norm'] = df_fts['Nombre'].apply(norm_nom)

    r_campo = os.path.join("data", "EVALUACIONES", "CAMPO", "CAMPO.xlsx")
    if os.path.exists(r_campo):
        df_campo = pd.read_excel(r_campo)
        ren_c = {c: 'Fecha' for c in df_campo.columns if 'fecha' in str(c).lower()}
        ren_c.update({c: 'Nombre' for c in df_campo.columns if 'nombre' in str(c).lower()})
        ren_c.update({c: 'V_MAX' for c in df_campo.columns if str(c).strip().lower() == 'v_max'})
        ren_c.update({c: 'AC_MAX' for c in df_campo.columns if str(c).strip().lower() == 'ac_max'})
        ren_c.update({c: 'DEC_MAX' for c in df_campo.columns if str(c).strip().lower() == 'dec_max'})
        df_campo.rename(columns=ren_c, inplace=True)
        df_campo['Fecha_dt'] = pd.to_datetime(df_campo['Fecha'], dayfirst=True, errors='coerce')
        df_campo['Fecha'] = df_campo['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_campo['Nombre_Norm'] = df_campo['Nombre'].apply(norm_nom)
        for num_col in ['V_MAX', 'AC_MAX', 'DEC_MAX']:
            if num_col in df_campo.columns: df_campo[num_col] = pd.to_numeric(df_campo[num_col].astype(str).str.replace(',', '.'), errors='coerce')

    return df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo

df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo = cargar_todo_informes()

# =============================================================================
# 3. SELECCIÓN DE JUGADOR (PARA STAFF)
# =============================================================================
st.title("INFORMES INDIVIDUALES DE PLANTILLA")

lista_jugadores = sorted(df_pos['Nombre'].dropna().unique()) if not df_pos.empty else []
if not lista_jugadores and not df_cuest.empty:
    lista_jugadores = sorted(df_cuest['Nombre'].dropna().unique())

if not lista_jugadores:
    st.warning("⚠️ No se encontraron jugadores registrados en el sistema.")
    st.stop()

c_sel, _ = st.columns([1.8, 2.2])
with c_sel:
    jugador_sel = st.selectbox("⚽ Selecciona Jugador:", lista_jugadores)

st.markdown("---")

# =============================================================================
# 4. EXTRACCIÓN Y NORMALIZACIÓN DE DATOS DEL JUGADOR
# =============================================================================
jug_norm = norm_nom(jugador_sel)

match_pos = df_pos[df_pos['Nombre_Norm'] == jug_norm] if not df_pos.empty else pd.DataFrame()
match_cuest = df_cuest[df_cuest['Nombre_Norm'] == jug_norm] if not df_cuest.empty else pd.DataFrame()

url_foto_jugador = match_pos.iloc[0].get('Foto_URL', None) if not match_pos.empty and 'Foto_URL' in match_pos.columns else None

# Fecha de nacimiento
fecha_nac_str = "Por definir"
if not match_cuest.empty and 'Fecha_Nacimiento' in match_cuest.columns:
    val_fn = match_cuest.iloc[0]['Fecha_Nacimiento']
    if pd.notna(val_fn) and str(val_fn).strip() != "":
        fecha_nac_str = str(val_fn).strip()

# Posición
posicion_str = "Por definir"
if not match_cuest.empty and 'Posicion_Habitual' in match_cuest.columns:
    val_p = match_cuest.iloc[0]['Posicion_Habitual']
    if pd.notna(val_p) and str(val_p).strip() != "":
        posicion_str = str(val_p).strip()
elif not match_pos.empty:
    posicion_str = str(match_pos.iloc[0].get('Posicion', 'Por definir')).strip()

# Pierna Dominante
pierna_str = "Por definir"
if not match_cuest.empty and 'Pierna_Dominante' in match_cuest.columns:
    val_pierna = match_cuest.iloc[0]['Pierna_Dominante']
    if pd.notna(val_pierna) and str(val_pierna).strip() != "":
        pierna_str = str(val_pierna).strip()

# Minutos Jugados Oficiales desde inicio de liga (06/09/2026)
minutos_oficiales = 0
rpe_medio = 0.0
if not df_rpe.empty:
    fecha_inicio_liga = pd.to_datetime("2026-09-06")
    df_m = df_rpe[(df_rpe['Nombre_Norm'] == jug_norm) & 
                  (df_rpe['Tipo_Sesion'].str.lower().str.contains('partido')) & 
                  (df_rpe['Fecha_dt'] >= fecha_inicio_liga)]
    minutos_oficiales = int(df_m['Minutos'].sum())
    
    df_j_rpe = df_rpe[df_rpe['Nombre_Norm'] == jug_norm]
    if not df_j_rpe.empty:
        rpe_medio = float(df_j_rpe['RPE_G'].mean())

url_escudo_oficial = "https://cdn.resfu.com/img_data/equipos/2585.png?size=120x&lossy=1"
nombre_mostrar = jugador_sel.replace('_', ' ').upper()

# =============================================================================
# 5. ENCABEZADO SUPERIOR: FOTO -> ESCUDO+CAMPOGRAMA -> FICHA KPI
# =============================================================================

col_foto, col_vis, col_kpis = st.columns([1.0, 1.2, 2.8], gap="medium")

# 1. Foto (Extremo Izquierdo)
with col_foto:
    if url_foto_jugador and pd.notna(url_foto_jugador):
        st.markdown(f'<img src="{url_foto_jugador}" class="photo-full-body">', unsafe_allow_html=True)
    else:
        st.markdown('<div class="photo-placeholder-full"><span style="font-size:65px; color:#64748B;">👤</span></div>', unsafe_allow_html=True)

# 2. Escudo + Tag + Campograma (Rellenando la altura vertical)
with col_vis:
    st.markdown(f'<div style="text-align:center; margin-bottom:2px;"><img src="{url_escudo_oficial}" style="width:58px; height:auto;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="tag-division">JUVENIL DIVISIÓN DE HONOR</div>', unsafe_allow_html=True)
    
    pos_low = posicion_str.lower()
    if 'porter' in pos_low: x_target, y_target = 34, 95
    elif 'central' in pos_low: x_target, y_target = 34, 80
    elif 'lateral' in pos_low:
        if 'zurdo' in pierna_str.lower() or 'izq' in pos_low: x_target, y_target = 58, 75
        else: x_target, y_target = 10, 75
    elif 'medio' in pos_low or 'pivote' in pos_low or 'mediocentro' in pos_low: x_target, y_target = 34, 55
    elif 'interior' in pos_low or 'mediapunta' in pos_low:
        if 'zurdo' in pierna_str.lower() or 'izq' in pos_low: x_target, y_target = 46, 40
        else: x_target, y_target = 22, 40
    elif 'extremo' in pos_low or 'carrilero' in pos_low:
        if 'zurdo' in pierna_str.lower() or 'izq' in pos_low: x_target, y_target = 58, 25
        else: x_target, y_target = 10, 25
    elif 'delantero' in pos_low or 'punta' in pos_low or 'atacante' in pos_low: x_target, y_target = 34, 15
    else: x_target, y_target = 34, 52.5

    fig_pitch = go.Figure()
    lineas_campo = [
        dict(type="rect", x0=0, y0=0, x1=68, y1=105, line=dict(color="rgba(255,255,255,0.4)", width=2)),
        dict(type="line", x0=0, y0=52.5, x1=68, y1=52.5, line=dict(color="rgba(255,255,255,0.4)", width=2)),
        dict(type="circle", x0=24.85, y0=43.35, x1=43.15, y1=61.65, line=dict(color="rgba(255,255,255,0.4)", width=2)),
        dict(type="rect", x0=13.84, y0=0, x1=54.16, y1=16.5, line=dict(color="rgba(255,255,255,0.4)", width=1.5)),
        dict(type="rect", x0=13.84, y0=88.5, x1=54.16, y1=105, line=dict(color="rgba(255,255,255,0.4)", width=1.5)),
        dict(type="rect", x0=24.84, y0=0, x1=43.16, y1=5.5, line=dict(color="rgba(255,255,255,0.3)", width=1)),
        dict(type="rect", x0=24.84, y0=99.5, x1=43.16, y1=105, line=dict(color="rgba(255,255,255,0.3)", width=1))
    ]

    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=42, color='rgba(0, 229, 255, 0.25)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=26, color='rgba(0, 229, 255, 0.55)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=12, color='rgba(0, 229, 255, 0.95)'), showlegend=False))

    fig_pitch.update_layout(
        shapes=lineas_campo, template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(range=[-2, 70], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[-2, 107], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True, scaleanchor="x", scaleratio=1),
        height=320, margin=dict(l=2, r=2, t=2, b=2)
    )
    st.plotly_chart(fig_pitch, use_container_width=True, config={'staticPlot': True})

# 3. Ficha KPI del Jugador (Todo en UNA SOLA FILA de 4 bloques)
with col_kpis:
    st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)
    k_col1, k_col2, k_col3, k_col4 = st.columns(4, gap="small")
    
    with k_col1:
        st.markdown(f"""
            <div class="kpi-tile-header">
                <div class="kpi-label-header">📅 NACIMIENTO</div>
                <div class="kpi-value-header">{fecha_nac_str}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with k_col2:
        st.markdown(f"""
            <div class="kpi-tile-header">
                <div class="kpi-label-header">🦶 PIERNA HÁBIL</div>
                <div class="kpi-value-header kpi-value-cyan">{pierna_str.upper()}</div>
            </div>
        """, unsafe_allow_html=True)

    with k_col3:
        st.markdown(f"""
            <div class="kpi-tile-header">
                <div class="kpi-label-header">⏱️ MINUTOS LIGA</div>
                <div class="kpi-value-header kpi-value-gold">{minutos_oficiales}′</div>
            </div>
        """, unsafe_allow_html=True)

    with k_col4:
        st.markdown(f"""
            <div class="kpi-tile-header">
                <div class="kpi-label-header">🏆 RANKING PERFIL</div>
                <div class="kpi-value-header kpi-value-green">#4</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# 6. SECCIÓN INFERIOR: RADAR LIBRE + CONTROLES ALINEADOS AL BAJO
# =============================================================================

c_radar, c_controls = st.columns([1.5, 1.0], gap="large")

with c_radar:
    st.markdown('<div style="text-align:center; font-size:12px; font-weight:800; color:#94A3B8; letter-spacing:1px; margin-bottom:2px;">PERFIL TÁCTICO CONDICIONAL</div>', unsafe_allow_html=True)
    
    categories = ['Movilidad', 'VAM', 'Dinamometría', 'CMJ', 'DRI', 'Tren Sup.']
    values_jugador = [78, 85, 62, 92, 70, 75]
    values_media_pos = [65, 70, 60, 72, 65, 68]
    
    categories_closed = categories + [categories[0]]
    values_jug_closed = values_jugador + [values_jugador[0]]
    values_med_closed = values_media_pos + [values_media_pos[0]]

    fig_radar = go.Figure()
    
    fig_radar.add_trace(go.Scatterpolar(
        r=values_med_closed, theta=categories_closed,
        fill='toself', name='Media Demarcación',
        fillcolor='rgba(241, 196, 15, 0.12)',
        line=dict(color='#F1C40F', width=1.5, dash='dash'),
        marker=dict(size=4, color='#F1C40F')
    ))

    fig_radar.add_trace(go.Scatterpolar(
        r=values_jug_closed, theta=categories_closed,
        fill='toself', name=nombre_mostrar,
        fillcolor='rgba(0, 229, 255, 0.35)',
        line=dict(color='#00E5FF', width=3, shape='spline'),
        marker=dict(size=6, color='#FFFFFF', line=dict(color='#00E5FF', width=2))
    ))

    fig_radar.update_layout(
        polar=dict(
            bgcolor='rgba(15, 23, 42, 0.6)',
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255,255,255,0.12)', tickfont=dict(size=9, color='#8E9BAE')),
            angularaxis=dict(gridcolor='rgba(255,255,255,0.12)', tickfont=dict(size=11, color='#FFFFFF', family="Arial Black"))
        ),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
        height=290, margin=dict(l=25, r=25, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with c_controls:
    st.markdown('<div style="height:235px;"></div>', unsafe_allow_html=True)
    c_ctrl1, c_ctrl2 = st.columns(2, gap="small")
    with c_ctrl1:
        modo_analisis = st.radio("📊 Módulo:", ["Pruebas Físicas", "Rendimiento en Campo"], horizontal=True)
    with c_ctrl2:
        filtro_comparacion = st.selectbox("⚖️ Comparar Percentil vs:", ["Toda la Plantilla", "Misma Demarcación"])

st.markdown("---")

# =============================================================================
# 7. EVOLUCIÓN HISTÓRICA MULTI-PRUEBA (GRÁFICOS DE LÍNEA)
# =============================================================================

if modo_analisis == "Pruebas Físicas":
    st.markdown("### 📈 EVOLUCIÓN HISTÓRICA DE EVALUACIONES CONDICIONALES")
    st.caption("Selecciona una prueba para inspeccionar la progresión del jugador con sus umbrales de referencia oficiales.")

    test_categoria = st.radio(
        "🎯 Selecciona Batería de Tests:",
        ["🩺 Movilidad", "🫁 VAM Aeróbico", "⚙️ Dinamometría", "🚀 Saltos & DRI", "🏋️ Tren Superior", "⚡ Velocidad & COD"],
        horizontal=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- MOVILIDAD ---
    if test_categoria == "🩺 Movilidad":
        if df_mov is not None and not df_mov.empty:
            df_j_mov = df_mov[df_mov['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_mov.empty:
                st.info(f"No hay evaluaciones de Movilidad registradas para {jugador_sel}.")
            else:
                articulacion_sel = st.selectbox("Selec. Articulación:", ["Dorsiflexión Tobillo", "Rotación Interna Cadera", "Flexión Cadera", "Movilidad Lumbar"])
                
                fig_mov_line = go.Figure()
                fechas_str = df_j_mov['Fecha'].tolist()
                
                if articulacion_sel == "Dorsiflexión Tobillo":
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['DORSIFLEX_D'], mode='lines+markers', name='Derecha (D)', line=dict(color='#00A8E8', width=3, shape='spline')))
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['DORSIFLEX_I'], mode='lines+markers', name='Izquierda (I)', line=dict(color='#FF9F1C', width=3, shape='spline')))
                    ref_val, unidad_m = 12, "cm"
                elif articulacion_sel == "Rotación Interna Cadera":
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['ROT_INT_D'], mode='lines+markers', name='Derecha (D)', line=dict(color='#00A8E8', width=3, shape='spline')))
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['ROT_INT_I'], mode='lines+markers', name='Izquierda (I)', line=dict(color='#FF9F1C', width=3, shape='spline')))
                    ref_val, unidad_m = 35, "°"
                elif articulacion_sel == "Flexión Cadera":
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['FLEX_CAD_D'], mode='lines+markers', name='Derecha (D)', line=dict(color='#00A8E8', width=3, shape='spline')))
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['FLEX_CAD_I'], mode='lines+markers', name='Izquierda (I)', line=dict(color='#FF9F1C', width=3, shape='spline')))
                    ref_val, unidad_m = 45, "°"
                else:
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['LUMBAR'], mode='lines+markers', name='Lumbar', line=dict(color='#2ECC71', width=3, shape='spline')))
                    ref_val, unidad_m = 80, "°"

                fig_mov_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=ref_val, y1=ref_val, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                fig_mov_line.add_annotation(x=len(fechas_str)-1, y=ref_val, text=f"Ref. Óptima (≥{ref_val} {unidad_m})", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                fig_mov_line.update_layout(
                    title=f"Evolución: {articulacion_sel} - {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title=f"Valor ({unidad_m})"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_mov_line, use_container_width=True)

    # --- VAM AERÓBICO ---
    elif test_categoria == "🫁 VAM Aeróbico":
        if df_vam is not None and not df_vam.empty:
            df_j_vam = df_vam[df_vam['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_vam.empty:
                st.info(f"No hay evaluaciones de VAM registradas para {jugador_sel}.")
            else:
                fechas_str = df_j_vam['Fecha'].tolist()
                fig_vam_line = go.Figure()
                fig_vam_line.add_trace(go.Scatter(x=fechas_str, y=df_j_vam['VAM'], mode='lines+markers', name='VAM (km/h)', line=dict(color='#00E5FF', width=3, shape='spline'), marker=dict(size=8)))
                
                ref_vam_val = 15.5
                fig_vam_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=ref_vam_val, y1=ref_vam_val, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                fig_vam_line.add_annotation(x=len(fechas_str)-1, y=ref_vam_val, text=f"Ref. {posicion_str} ({ref_vam_val:.1f} km/h)", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                fig_vam_line.update_layout(
                    title=f"Evolución VAM Aeróbico: {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title="VAM (km/h)"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_vam_line, use_container_width=True)

    # --- DINAMOMETRÍA ---
    elif test_categoria == "⚙️ Dinamometría":
        if df_dina is not None and not df_dina.empty:
            df_j_dina = df_dina[df_dina['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_dina.empty:
                st.info(f"No hay evaluaciones de Dinamometría registradas para {jugador_sel}.")
            else:
                sub_dina = st.radio("Selec. Métrica de Fuerza:", ["Picos de Fuerza Relativa (N/kg)", "Asimetría % Monopodal", "Ratios Funcionales"], horizontal=True)
                
                piv_dina = df_j_dina.pivot_table(index=['Fecha', 'Fecha_dt'], columns='Exercise', values='Fmax_Abs', aggfunc='mean').reset_index().sort_values('Fecha_dt')
                fechas_str = piv_dina['Fecha'].tolist()
                peso_j = 70.0
                if df_peso is not None and not df_peso.empty:
                    df_pj = df_peso[df_peso['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                    if not df_pj.empty: peso_j = float(df_pj.iloc[-1]['Peso'])

                fig_dina_line = go.Figure()

                if sub_dina == "Picos de Fuerza Relativa (N/kg)":
                    for col_e, color_c, ref_u in [('Extension_rodilla_90_Derecha', '#00A8E8', 6.0), ('Extension_rodilla_90_Izquierda', '#FF9F1C', 6.0)]:
                        if col_e in piv_dina.columns:
                            fig_dina_line.add_trace(go.Scatter(x=fechas_str, y=piv_dina[col_e]/peso_j, mode='lines+markers', name=col_e.replace('_', ' '), line=dict(color=color_c, width=2.5, shape='spline')))
                    
                    fig_dina_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=6.0, y1=6.0, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                    fig_dina_line.add_annotation(x=len(fechas_str)-1, y=6.0, text="Ref. Óptima Ext. Rodilla (>6.0 N/kg)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)

                elif sub_dina == "Asimetría % Monopodal":
                    if 'Extension_rodilla_90_Derecha' in piv_dina.columns and 'Extension_rodilla_90_Izquierda' in piv_dina.columns:
                        asim_val = (abs(piv_dina['Extension_rodilla_90_Derecha'] - piv_dina['Extension_rodilla_90_Izquierda']) / piv_dina[['Extension_rodilla_90_Derecha', 'Extension_rodilla_90_Izquierda']].max(axis=1)) * 100
                        fig_dina_line.add_trace(go.Scatter(x=fechas_str, y=asim_val, mode='lines+markers', name='Asimetría Ext. Rodilla %', line=dict(color='#FF2E93', width=3, shape='spline')))
                    
                    fig_dina_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=10.0, y1=10.0, line=dict(color="#E74C3C", width=2.5, dash="dash"))
                    fig_dina_line.add_annotation(x=len(fechas_str)-1, y=10.0, text="Umbral Alerta Asimetría (>10%)", showarrow=False, font=dict(color="#E74C3C", size=11), align="right", yshift=12)

                else:
                    if 'ADD_Cadera_De_Pie_Derecha' in piv_dina.columns and 'ABD_Cadera_De_Pie_Derecha' in piv_dina.columns:
                        m_add = piv_dina[['ADD_Cadera_De_Pie_Derecha', 'ADD_Cadera_De_Pie_Izquierda']].mean(axis=1) if 'ADD_Cadera_De_Pie_Izquierda' in piv_dina.columns else piv_dina['ADD_Cadera_De_Pie_Derecha']
                        m_abd = piv_dina[['ABD_Cadera_De_Pie_Derecha', 'ABD_Cadera_De_Pie_Izquierda']].mean(axis=1) if 'ABD_Cadera_De_Pie_Izquierda' in piv_dina.columns else piv_dina['ABD_Cadera_De_Pie_Derecha']
                        ratio_aa = m_add / m_abd
                        fig_dina_line.add_trace(go.Scatter(x=fechas_str, y=ratio_aa, mode='lines+markers', name='Ratio ADD/ABD Cadera', line=dict(color='#00E5FF', width=3, shape='spline')))

                    fig_dina_line.add_shape(type="rect", x0=-0.5, x1=len(fechas_str)-0.5, y0=1.05, y1=1.20, fillcolor="rgba(46, 204, 113, 0.18)", line=dict(width=0))
                    fig_dina_line.add_annotation(x=len(fechas_str)-1, y=1.20, text="Rango Saludable ADD/ABD (1.05 - 1.20)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)

                fig_dina_line.update_layout(
                    title=f"Evolución Dinamometría: {sub_dina} - {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title="Valor Métrica"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_dina_line, use_container_width=True)

    # --- SALTOS & DRI ---
    elif test_categoria == "🚀 Saltos & DRI":
        if df_saltos is not None and not df_saltos.empty:
            df_j_s = df_saltos[df_saltos['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_s.empty:
                st.info(f"No hay evaluaciones de Saltos registradas para {jugador_sel}.")
            else:
                sub_salto = st.radio("Selec. Métrica de Salto:", ["CMJ & slCMJ (cm)", "Asimetría Monopodal %", "Índice DRI (Drop Jump)"], horizontal=True)
                
                fig_salto_line = go.Figure()
                
                if sub_salto == "CMJ & slCMJ (cm)":
                    piv_s = df_j_s.pivot_table(index=['Fecha', 'Fecha_dt'], columns='Tipo', values='Altura', aggfunc='mean').reset_index().sort_values('Fecha_dt')
                    fechas_str = piv_s['Fecha'].tolist()
                    
                    for t_col, color_c in [('CMJ', '#00A8E8'), ('slCMJright', '#FF9F1C'), ('slCMJleft', '#2ECC71')]:
                        if t_col in piv_s.columns:
                            fig_salto_line.add_trace(go.Scatter(x=fechas_str, y=piv_s[t_col], mode='lines+markers', name=t_col, line=dict(color=color_c, width=2.5, shape='spline')))
                    
                    ref_cmj = 38.0
                    fig_salto_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=ref_cmj, y1=ref_cmj, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                    fig_salto_line.add_annotation(x=len(fechas_str)-1, y=ref_cmj, text=f"Ref. CMJ {posicion_str} ({ref_cmj:.1f} cm)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)

                elif sub_salto == "Asimetría Monopodal %":
                    piv_s = df_j_s.pivot_table(index=['Fecha', 'Fecha_dt'], columns='Tipo', values='Altura', aggfunc='mean').reset_index().sort_values('Fecha_dt')
                    fechas_str = piv_s['Fecha'].tolist()
                    if 'slCMJright' in piv_s.columns and 'slCMJleft' in piv_s.columns:
                        asim_s = (abs(piv_s['slCMJright'] - piv_s['slCMJleft']) / piv_s[['slCMJright', 'slCMJleft']].max(axis=1)) * 100
                        fig_salto_line.add_trace(go.Scatter(x=fechas_str, y=asim_s, mode='lines+markers', name='Asimetría slCMJ %', line=dict(color='#FF2E93', width=3, shape='spline')))
                    
                    fig_salto_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=10.0, y1=10.0, line=dict(color="#E74C3C", width=2.5, dash="dash"))
                    fig_salto_line.add_annotation(x=len(fechas_str)-1, y=10.0, text="Umbral Alerta Asimetría (>10%)", showarrow=False, font=dict(color="#E74C3C", size=11), align="right", yshift=12)

                else:
                    if df_dri is not None and not df_dri.empty:
                        df_j_dri = df_dri[df_dri['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                        if not df_j_dri.empty:
                            fechas_str = df_j_dri['Fecha'].tolist()
                            fig_salto_line.add_trace(go.Scatter(x=fechas_str, y=df_j_dri['DRI'], mode='lines+markers', name='Índice DRI', line=dict(color='#00E5FF', width=3, shape='spline')))
                            fig_salto_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=2.00, y1=2.00, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                            fig_salto_line.add_annotation(x=len(fechas_str)-1, y=2.00, text="Ref. Óptima DRI (>2.00)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)
                        else: st.info("No hay datos de DRI para este jugador.")

                fig_salto_line.update_layout(
                    title=f"Evolución Saltos: {sub_salto} - {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title="Valor Métrica"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_salto_line, use_container_width=True)

    # --- TREN SUPERIOR ---
    elif test_categoria == "🏋️ Tren Superior":
        if df_fts is not None and not df_fts.empty:
            df_j_ts = df_fts[df_fts['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_ts.empty:
                st.info(f"No hay evaluaciones de Tren Superior registradas para {jugador_sel}.")
            else:
                fechas_str = df_j_ts['Fecha'].tolist()
                fig_ts_line = go.Figure()
                fig_ts_line.add_trace(go.Scatter(x=fechas_str, y=df_j_ts['Press_Banca'], mode='lines+markers', name='Press Banca (reps)', line=dict(color='#00A8E8', width=3, shape='spline')))
                fig_ts_line.add_trace(go.Scatter(x=fechas_str, y=df_j_ts['Dominada'], mode='lines+markers', name='Dominadas (reps)', line=dict(color='#2ECC71', width=3, shape='spline')))

                fig_ts_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=20.0, y1=20.0, line=dict(color="#00A8E8", width=2, dash="dash"))
                fig_ts_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=10.0, y1=10.0, line=dict(color="#2ECC71", width=2, dash="dash"))
                fig_ts_line.add_annotation(x=len(fechas_str)-1, y=20.0, text="Ref. Press Banca (≥20 reps)", showarrow=False, font=dict(color="#00A8E8", size=11), align="right", yshift=12)
                fig_ts_line.add_annotation(x=len(fechas_str)-1, y=10.0, text="Ref. Dominadas (≥10 reps)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)

                fig_ts_line.update_layout(
                    title=f"Evolución Tren Superior: {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title="Repeticiones"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_ts_line, use_container_width=True)

    # --- CINEMÁTICA CAMPO ---
    else:
        if df_campo is not None and not df_campo.empty:
            df_j_c = df_campo[df_campo['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
            if df_j_c.empty:
                st.info(f"No hay evaluaciones de Campo registradas para {jugador_sel}.")
            else:
                fechas_str = df_j_c['Fecha'].tolist()
                fig_c_line = go.Figure()
                
                fig_c_line.add_trace(go.Scatter(x=fechas_str, y=df_j_c['V_MAX'], mode='lines+markers', name='V_MAX (km/h)', line=dict(color='#00E5FF', width=3, shape='spline')))
                fig_c_line.add_trace(go.Scatter(x=fechas_str, y=df_j_c['AC_MAX'], mode='lines+markers', name='AC_MAX (m/s²)', line=dict(color='#FFC107', width=2.5, shape='spline')))
                fig_c_line.add_trace(go.Scatter(x=fechas_str, y=df_j_c['DEC_MAX'], mode='lines+markers', name='DEC_MAX (m/s²)', line=dict(color='#FF2E93', width=2.5, shape='spline')))

                ref_vmax_val = 31.0
                fig_c_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=ref_vmax_val, y1=ref_vmax_val, line=dict(color="#00E5FF", width=2, dash="dash"))
                fig_c_line.add_annotation(x=len(fechas_str)-1, y=ref_vmax_val, text=f"Ref. V_MAX {posicion_str} ({ref_vmax_val:.1f} km/h)", showarrow=False, font=dict(color="#00E5FF", size=11), align="right", yshift=12)

                fig_c_line.update_layout(
                    title=f"Evolución CINEMÁTICA EN CAMPO: {jugador_sel}", template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
                    xaxis=dict(tickangle=-30), yaxis=dict(title="Valor Métrica"),
                    height=380, margin=dict(l=20, r=20, t=50, b=50)
                )
                st.plotly_chart(fig_c_line, use_container_width=True)

# -----------------------------------------------------------------------------
# GPS PARTIDOS Y DISPERSIÓN (MODO: RENDIMIENTO EN CAMPO)
# -----------------------------------------------------------------------------
else:
    st.markdown("### ⚽ REGISTRO GPS PARTIDO A PARTIDO")
    
    df_p_jug = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt', ascending=False) if not df_gps_all.empty else pd.DataFrame()
    
    if df_p_jug.empty:
        st.info("No hay registros GPS disponibles para este jugador.")
    else:
        st.dataframe(df_p_jug[['Fecha', 'Dist_Total', 'Dist_18', 'Dist_25', 'Acc_Dec', 'V_MAX', 'AC_MAX', 'DEC_MAX']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 📈 DISPERSIÓN: VOLUMEN VS ALTA INTENSIDAD")
        
        fig_sc = px.scatter(
            df_p_jug, x="Dist_Total", y="Dist_18", size="Dist_25",
            hover_data=["Fecha"], labels={"Dist_Total": "Distancia Total (m)", "Dist_18": "Distancia >18 km/h (m)"},
            title=f"Evolución Intensidad vs Volumen - {jugador_sel}", template="plotly_dark"
        )
        fig_sc.update_traces(marker=dict(color='#00A8E8', line=dict(width=1, color='White')))
        fig_sc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', height=400)
        st.plotly_chart(fig_sc, use_container_width=True)