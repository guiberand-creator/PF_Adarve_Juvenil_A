import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
import glob
import requests
import io
import base64
import re
from datetime import datetime
from utils import aplicar_diseno_responsive

# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y TEMAS V0
# =============================================================================
aplicar_diseno_responsive()

st.set_page_config(
    page_title="Player Performance Dashboard | Adarve DH",
    page_icon="⚡",
    layout="wide"
)

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.error("⚠️ Acceso no autorizado. Por favor, inicia sesión en la página principal.")
    st.stop()

# PALETA V0 DESIGN SYSTEM
BG = "#0d1117"
SURFACE = "#161b22"
SURFACE_2 = "#1c2530"
BORDER = "#26303b"
TEXT = "#e6edf3"
MUTED = "#8b949e"
PRIMARY = "#e11d48"          # Crimson Accent
PRIMARY_SOFT = "rgba(225, 29, 72, 0.15)"
TEAM = "#38bdf8"             # Cool Blue
GOOD = "#22c55e"
WARNING = "#f59e0b"

def inject_v0_css():
    st.markdown(f"""
        <style>
        .stApp {{ background: {BG}; }}
        .block-container {{ padding-top: 1.2rem !important; padding-bottom: 3rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100% !important; }}
        div[data-testid="column"] {{ display: flex; flex-direction: column; justify-content: flex-start; }}
        .pd-hero {{
            background: radial-gradient(1200px 240px at 12% -40%, {PRIMARY_SOFT}, transparent 60%), linear-gradient(180deg, {SURFACE_2} 0%, {SURFACE} 100%);
            border: 1px solid {BORDER}; border-radius: 18px; padding: 1.5rem 1.75rem; width: 100%; height: 330px;
            box-sizing: border-box; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45); display: flex; flex-direction: column; justify-content: space-between; margin-top: 0px !important;
        }}
        .pd-name {{ font-size: 2.3rem; font-weight: 800; line-height: 1.05; margin: 0; letter-spacing: -0.02em; color: {TEXT}; }}
        .pd-club {{ color: {MUTED}; font-size: 0.95rem; margin-top: 0.6rem; margin-bottom: 1.5rem; }}
        .pd-badge {{
            display: inline-flex; align-items: center; gap: 0.4rem; background: {PRIMARY_SOFT}; color: {PRIMARY};
            border: 1px solid rgba(225,29,72,0.35); padding: 0.25rem 0.8rem; border-radius: 999px; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em;
        }}
        .pd-facts {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }}
        .pd-fact {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 0.85rem 1rem; text-align: center; }}
        .pd-fact .k {{ color: {MUTED}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }}
        .pd-fact .v {{ font-size: 1.3rem; font-weight: 800; margin-top: 0.25rem; color: {TEXT}; }}
        .pd-fact .v-cyan {{ color: #38bdf8 !important; }}
        .pd-fact .v-gold {{ color: #f59e0b !important; }}
        .pd-fact .v-green {{ color: #22c55e !important; }}
        .photo-v0 {{ height: 330px !important; width: 100% !important; max-width: 260px !important; object-fit: contain !important; display: block; margin: 0 auto; filter: drop-shadow(0px 10px 20px rgba(225, 29, 72, 0.25)); }}
        .photo-placeholder-v0 {{ height: 330px !important; width: 100% !important; max-width: 260px !important; border-radius: 16px; background: radial-gradient(120% 120% at 30% 20%, {SURFACE_2}, {SURFACE}); display: flex; align-items: center; justify-content: center; border: 1px solid {BORDER}; margin: 0 auto; }}
        .pd-section-title {{ font-size: 0.85rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: {MUTED}; margin: 0.25rem 0 0.75rem; }}
        [data-testid="stMetricDelta"] svg {{ display: none; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
        .stTabs [data-baseweb="tab"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px 10px 0 0; padding: 0.6rem 1.4rem; font-weight: 700; color: {MUTED}; }}
        .stTabs [aria-selected="true"] {{ background: {SURFACE_2}; color: {TEXT}; border-bottom: 2px solid {PRIMARY}; }}
        
        /* SHADCN CAROUSEL STYLE */
        .carousel-card {{
            background-color: {SURFACE_2};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0.5rem 0;
        }}
        .metric-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.45rem 0.75rem; border-bottom: 1px solid {BORDER}; font-size: 0.85rem;
        }}
        .metric-label {{ color: {MUTED}; font-weight: 600; }}
        .metric-val {{ color: {TEXT}; font-weight: 800; }}
        </style>
    """, unsafe_allow_html=True)

inject_v0_css()

def norm_nom(texto):
    if pd.isna(texto): return ""
    return " ".join(str(texto).replace('_', ' ').strip().lower().split())

_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo_sidebar = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))
if os.path.exists(_ruta_logo_sidebar):
    with open(_ruta_logo_sidebar, "rb") as _f:
        b64_sidebar = base64.b64encode(_f.read()).decode()
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{ position: fixed; bottom: 20px; left: 10px; width: 260px; text-align: center; z-index: 999; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.15); }}
        .footer-sello-unico img {{ width: 195px; height: auto; margin-bottom: 8px; }}
        .footer-sello-unico p {{ font-size: 11px !important; color: #CCCCCC !important; margin: 2px 0 0 0 !important; letter-spacing: 0.5px; }}
        </style>
        <div class="footer-sello-unico"><img src="data:image/png;base64,{b64_sidebar}"><p>© 2026 All Rights Reserved</p></div>
    """, unsafe_allow_html=True)

_ruta_escudo_oficial = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "Imagen2.png"))
url_escudo_oficial = ""
if os.path.exists(_ruta_escudo_oficial):
    with open(_ruta_escudo_oficial, "rb") as _f:
        url_escudo_oficial = f"data:image/png;base64,{base64.b64encode(_f.read()).decode()}"

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
    r_pos = os.path.join("data", "Posiciones.xlsx")
    df_pos = pd.read_excel(r_pos) if os.path.exists(r_pos) else pd.DataFrame()
    if not df_pos.empty:
        df_pos.columns = [str(c).strip() for c in df_pos.columns]
        c_n = next((c for c in df_pos.columns if 'jugador' in c.lower() or 'nombre' in c.lower()), df_pos.columns[0])
        c_p = next((c for c in df_pos.columns if 'posic' in c.lower()), None)
        c_lado = next((c for c in df_pos.columns if any(k in c.lower() for k in ['lateralidad', 'lado', 'perfil'])), None)
        c_foto = next((c for c in df_pos.columns if any(k in c.lower() for k in ['foto', 'url'])), None)
        c_nac = next((c for c in df_pos.columns if 'nacimiento' in c.lower()), None)
        c_pierna = next((c for c in df_pos.columns if 'pierna' in c.lower()), None)

        renomb_dict = {c_n: 'Nombre'}
        if c_p: renomb_dict[c_p] = 'Posicion'
        if c_lado: renomb_dict[c_lado] = 'Lado'
        if c_foto: renomb_dict[c_foto] = 'Foto_URL'
        if c_nac: renomb_dict[c_nac] = 'Fecha_Nacimiento_Pos'
        if c_pierna: renomb_dict[c_pierna] = 'Pierna_Pos'
        df_pos = df_pos.rename(columns=renomb_dict)
        df_pos['Nombre_Norm'] = df_pos['Nombre'].apply(norm_nom)

        if 'Fecha_Nacimiento_Pos' in df_pos.columns:
            def safe_format_date(x):
                if pd.isna(x): return ""
                if hasattr(x, 'strftime'): return x.strftime('%d/%m/%Y')
                return str(x).replace('00:00:00', '').strip()
            df_pos['Fecha_Nacimiento_Pos'] = df_pos['Fecha_Nacimiento_Pos'].apply(safe_format_date)

    df_cuest = descargar_csv_drive("1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI", "0")
    if not df_cuest.empty:
        df_cuest.columns = [str(c).strip().lower() for c in df_cuest.columns]
        c_n, c_fn, c_pos, c_pierna = None, None, None, None
        for col in df_cuest.columns:
            if any(k in col for k in ['nombre', 'jugador', 'apellidos']): c_n = col
            elif any(k in col for k in ['nacimiento', 'nacim', 'dob', 'cumple']): c_fn = col
            elif any(k in col for k in ['posici', 'pos', 'demarc']): c_pos = col
            elif any(k in col for k in ['pierna', 'pie', 'habil', 'hábil']): c_pierna = col

        ren = {}
        if c_n: ren[c_n] = 'Nombre'
        if c_fn: ren[c_fn] = 'Fecha_Nacimiento'
        if c_pos: ren[c_pos] = 'Posicion_Habitual'
        if c_pierna: ren[c_pierna] = 'Pierna_Dominante'
        df_cuest = df_cuest.rename(columns=ren)
        if 'Nombre' in df_cuest.columns: df_cuest['Nombre_Norm'] = df_cuest['Nombre'].apply(norm_nom)

    r_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    df_peso = pd.read_excel(r_peso) if os.path.exists(r_peso) else pd.DataFrame()
    if not df_peso.empty:
        df_peso['Nombre_Norm'] = df_peso.iloc[:, 0].apply(norm_nom)
        df_peso['Fecha_dt'] = pd.to_datetime(df_peso.iloc[:, 1], dayfirst=True, errors='coerce')
        df_peso.rename(columns={df_peso.columns[2]: 'Peso'}, inplace=True)

    df_rpe = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if not df_rpe.empty:
        cols = df_rpe.columns
        c_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        c_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        c_t = next((c for c in cols if 'tipo' in str(c).lower() or 'sesion' in str(c).lower()), cols[2])
        c_m = next((c for c in cols if 'minuto' in str(c).lower() or 'tiempo' in str(c).lower()), cols[3])
        c_rpe = next((c for c in cols if 'rpe' in str(c).lower() or 'esfuerzo' in str(c).lower() or 'puntuacion' in str(c).lower()), None)
        
        df_rpe['Fecha_dt'] = pd.to_datetime(df_rpe[c_f], dayfirst=True, errors='coerce')
        df_rpe['Fecha'] = df_rpe['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_rpe['Nombre'] = df_rpe[c_n].astype(str).str.strip()
        df_rpe['Nombre_Norm'] = df_rpe['Nombre'].apply(norm_nom)
        df_rpe['Tipo_Sesion'] = df_rpe[c_t].astype(str).str.strip()
        df_rpe['Minutos'] = pd.to_numeric(df_rpe[c_m], errors='coerce').fillna(0)
        df_rpe['RPE_Score'] = pd.to_numeric(df_rpe[c_rpe], errors='coerce').fillna(0) if c_rpe else 0

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
                
                dl['Duracion'] = dt[b_c(['duracion', 'duración', 'time', 'tiempo'])].apply(fn) if b_c(['duracion', 'duración', 'time', 'tiempo']) else 0.0
                dl['Dist_Total'] = dt[b_c(['distancia total', 'distance'])].apply(fn) if b_c(['distancia total', 'distance']) else 0.0
                dl['Dist_18'] = dt[b_c(['> 18', '>18'])].apply(fn) if b_c(['> 18', '>18']) else 0.0
                dl['Dist_25'] = dt[b_c(['> 25', '>25'])].apply(fn) if b_c(['> 25', '>25']) else 0.0
                dl['Dist_28'] = dt[b_c(['> 28', '>28', '28.8', '28,8'])].apply(fn) if b_c(['> 28', '>28', '28.8', '28,8']) else 0.0
                dl['N_Sprints'] = dt[b_c(['sprints', 'nº sprints'])].apply(fn) if b_c(['sprints', 'nº sprints']) else 0.0
                
                accs = dt[b_c(['nº aceleraciones', 'nº acel', 'aceleraciones', 'accel'])].apply(fn) if b_c(['nº aceleraciones', 'nº acel', 'aceleraciones', 'accel']) else 0.0
                decs = dt[b_c(['nº desaceleraciones', 'nº decel', 'desaceleraciones', 'decel'])].apply(fn) if b_c(['nº desaceleraciones', 'nº decel', 'desaceleraciones', 'decel']) else 0.0
                dl['N_Acc'] = accs
                dl['N_Dec'] = decs
                dl['Acc_Dec'] = accs + decs
                
                dl['V_MAX'] = dt[b_c(['v. max', 'v.max', 'top speed'])].apply(fn) if b_c(['v. max', 'v.max', 'top speed']) else 0.0
                dl['AC_MAX'] = dt[b_c(['ac. max', 'acc. max', 'ac maxima', 'ac. maxima'])].apply(fn) if b_c(['ac. max', 'acc. max', 'ac maxima', 'ac. maxima']) else 0.0
                dl['DEC_MAX'] = dt[b_c(['dec. max', 'desac. max', 'dec maxima', 'dec. maxima'])].apply(fn) if b_c(['dec. max', 'desac. max', 'dec maxima', 'dec. maxima']) else 0.0
                dl['Player_Load'] = dt[b_c(['player load', 'playerload'])].apply(fn) if b_c(['player load', 'playerload']) else 0.0
                
                l_dfs.append(dl.dropna(subset=['Fecha_dt']))
            except: continue
        if l_dfs:
            df_gps_all = pd.concat(l_dfs, ignore_index=True)
            if df_gps_all['Dist_Total'].max() < 25:
                df_gps_all['Dist_Total'] *= 1000
                df_gps_all['Dist_18'] *= 1000
                df_gps_all['Dist_25'] *= 1000
                df_gps_all['Dist_28'] *= 1000

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
    if os.path.exists(os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.xlsx")): archivo_encontrado = os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.xlsx")
    elif os.path.exists(os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.csv")): archivo_encontrado = os.path.join(dir_dina, "DINAMOMETRIA_ANALITICO.csv")
    elif os.path.exists(dir_dina):
        for arch in os.listdir(dir_dina):
            if 'dinamometria' in arch.lower(): archivo_encontrado = os.path.join(dir_dina, arch); break

    if archivo_encontrado:
        try:
            df_dina = pd.read_excel(archivo_encontrado) if archivo_encontrado.endswith('.xlsx') else pd.read_csv(archivo_encontrado, sep=';', encoding='utf-8')
            if df_dina is not None and not df_dina.empty:
                df_dina.rename(columns={'Name': 'Nombre', 'Date': 'Fecha', 'Exercise': 'Exercise', 'MaxForce (raw)': 'Fmax_Abs'}, inplace=True)
                df_dina['Fmax_Abs'] = pd.to_numeric(df_dina['Fmax_Abs'].astype(str).str.replace(',', '.'), errors='coerce')
                df_dina['Exercise'] = df_dina['Exercise'].astype(str).str.replace(r'\\u00BA', '', regex=True).str.replace('°', '', regex=False).str.strip()
                df_dina['Fecha_dt'] = pd.to_datetime(df_dina['Fecha'], dayfirst=True, errors='coerce')
                df_dina['Fecha'] = df_dina['Fecha_dt'].dt.strftime('%d/%m/%Y')
                df_dina['Nombre_Norm'] = df_dina['Nombre'].apply(norm_nom)
        except: pass

    r_saltos = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
    if os.path.exists(r_saltos):
        df_saltos = pd.read_excel(r_saltos)
        ren_s = {c: 'Nombre' for c in df_saltos.columns if 'nombre' in str(c).lower() or 'atlet' in str(c).lower()}
        ren_s.update({c: 'Tipo' for c in df_saltos.columns if 'tipo' in str(c).lower()})
        ren_s.update({c: 'Altura' for c in df_saltos.columns if 'altura' in str(c).lower()})
        ren_s.update({c: 'Fecha_Hora' for c in df_saltos.columns if 'fecha' in str(c).lower()})
        df_saltos.rename(columns=ren_s, inplace=True)
        df_saltos['Fecha_dt'] = pd.to_datetime(df_saltos['Fecha_Hora'].astype(str).str.split(' ').str[0], dayfirst=True, errors='coerce')
        df_saltos['Fecha'] = df_saltos['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_saltos['Nombre_Norm'] = df_saltos['Nombre'].apply(norm_nom)
        
        def map_salto_type(t):
            t_up = str(t).upper()
            if 'CMJ' in t_up:
                if any(x in t_up for x in ['DER', 'RIGHT', ' D', '_D']): return 'CMJ_D'
                if any(x in t_up for x in ['IZQ', 'LEFT', ' I', '_I']): return 'CMJ_I'
                return 'CMJ'
            return t_up
            
        if 'Tipo' in df_saltos.columns:
            df_saltos['Tipo_Norm'] = df_saltos['Tipo'].apply(map_salto_type)
        else:
            df_saltos['Tipo_Norm'] = 'CMJ'

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

    dict_rankings_reales = {}
    if not df_pos.empty:
        df_rank_base = df_pos[['Nombre', 'Nombre_Norm']].copy()
        
        def merge_ult(df_base, df_src, col_src, col_dst):
            if df_src is not None and not df_src.empty and col_src in df_src.columns:
                df_u = df_src.sort_values('Fecha_dt').groupby('Nombre_Norm', as_index=False)[col_src].last()
                df_u.rename(columns={col_src: col_dst}, inplace=True)
                return pd.merge(df_base, df_u, on='Nombre_Norm', how='left')
            return df_base

        if df_mov is not None and not df_mov.empty:
            df_m_last = df_mov.sort_values('Fecha_dt').copy()
            mov_cols = [c for c in ['DORSIFLEX_D', 'DORSIFLEX_I', 'ROT_INT_D', 'ROT_INT_I', 'FLEX_CAD_D', 'FLEX_CAD_I'] if c in df_m_last.columns]
            if mov_cols:
                df_m_last['Movilidad_Score'] = df_m_last[mov_cols].mean(axis=1)
                df_rank_base = merge_ult(df_rank_base, df_m_last, 'Movilidad_Score', 'Movilidad_Score')

        df_rank_base = merge_ult(df_rank_base, df_vam, 'VAM', 'VAM')

        dict_pesos = {}
        if df_peso is not None and not df_peso.empty:
            for nom_n in df_peso['Nombre_Norm'].unique():
                df_p_j = df_peso[df_peso['Nombre_Norm'] == nom_n].sort_values('Fecha_dt')
                dict_pesos[nom_n] = float(df_p_j.iloc[-1]['Peso'])

        if df_dina is not None and not df_dina.empty:
            df_d_last = df_dina.sort_values('Fecha_dt').copy()
            df_d_last['Peso_Jug'] = df_d_last['Nombre_Norm'].map(dict_pesos).fillna(70.0)
            df_d_last['Fmax_Rel'] = df_d_last['Fmax_Abs'] / df_d_last['Peso_Jug']
            df_d_agg = df_d_last.groupby('Nombre_Norm', as_index=False)['Fmax_Rel'].mean()
            df_rank_base = pd.merge(df_rank_base, df_d_agg[['Nombre_Norm', 'Fmax_Rel']], on='Nombre_Norm', how='left')

        if df_saltos is not None and not df_saltos.empty:
            df_cmj = df_saltos[df_saltos['Tipo_Norm'] == 'CMJ'].copy()
            df_rank_base = merge_ult(df_rank_base, df_cmj, 'Altura', 'CMJ_Altura')

        df_rank_base = merge_ult(df_rank_base, df_dri, 'DRI', 'DRI')

        if df_fts is not None and not df_fts.empty:
            df_ts_l = df_fts.sort_values('Fecha_dt').copy()
            df_ts_l['Tren_Superior_Reps'] = df_ts_l['Press_Banca'].fillna(0) + df_ts_l['Dominada'].fillna(0)
            df_rank_base = merge_ult(df_rank_base, df_ts_l, 'Tren_Superior_Reps', 'Tren_Superior_Reps')

        if df_campo is not None and not df_campo.empty:
            df_rank_base = merge_ult(df_rank_base, df_campo, 'V_MAX', 'V_MAX')
            df_rank_base = merge_ult(df_rank_base, df_campo, 'AC_MAX', 'AC_MAX')

        columnas_pruebas = {'Movilidad_Score': True, 'VAM': True, 'Fmax_Rel': True, 'CMJ_Altura': True, 'DRI': True, 'Tren_Superior_Reps': True, 'V_MAX': True, 'AC_MAX': True}
        cols_puntos = []
        for col_raw, mayor_es_mejor in columnas_pruebas.items():
            if col_raw in df_rank_base.columns:
                col_rank_name = f"P_{col_raw}"
                df_rank_base[col_rank_name] = df_rank_base[col_raw].rank(ascending=not mayor_es_mejor, method='min', na_option='bottom').astype(int)
                cols_puntos.append(col_rank_name)

        if cols_puntos:
            df_rank_base['PUNTOS_TOTALES'] = df_rank_base[cols_puntos].sum(axis=1)
            df_rank_base = df_rank_base.sort_values('PUNTOS_TOTALES', ascending=True).reset_index(drop=True)
            df_rank_base['POSICION_GLOBAL'] = df_rank_base.index + 1
            for _, r_rank in df_rank_base.iterrows():
                dict_rankings_reales[r_rank['Nombre_Norm']] = f"#{r_rank['POSICION_GLOBAL']}"

    r_ref_vam = os.path.join("data", "EVALUACIONES", "AEROBICO", "Referencia por posiciones.xlsx")
    df_ref_vam = pd.read_excel(r_ref_vam) if os.path.exists(r_ref_vam) else pd.DataFrame()
    
    df_ref_campo = pd.DataFrame()
    r_ref_campo_files = glob.glob(os.path.join("data", "EVALUACIONES", "CAMPO", "Referencia campo*.xlsx"))
    if r_ref_campo_files:
        df_ref_campo = pd.read_excel(r_ref_campo_files[0])

    # CALENDARIO OFICIAL Y ESCUDOS
    df_calendario = descargar_csv_drive("1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5", "1771990969")
    dict_escudos = {}
    dict_calendario = {}
    if not df_calendario.empty:
        df_calendario.columns = [str(c).strip().lower() for c in df_calendario.columns]
        c_f = next((c for c in df_calendario.columns if 'fecha' in c), None)
        c_loc = next((c for c in df_calendario.columns if 'casa' in c or 'fuera' in c or 'local' in c), None)
        c_eq = next((c for c in df_calendario.columns if 'equipo' in c or 'rival' in c), None)
        c_esc = next((c for c in df_calendario.columns if 'escudo' in c or 'url' in c), None)
        
        if c_f:
            df_calendario['Fecha_dt'] = pd.to_datetime(df_calendario[c_f], dayfirst=True, errors='coerce')
            df_calendario['Fecha_Date'] = df_calendario['Fecha_dt'].dt.date
            
            for _, row in df_calendario.dropna(subset=['Fecha_Date']).iterrows():
                f_date = row['Fecha_Date']
                rival = str(row[c_eq]).strip() if c_eq else ''
                loc = str(row[c_loc]).strip() if c_loc else ''
                escudo = str(row[c_esc]).strip() if c_esc else ''
                
                dict_calendario[f_date] = {
                    'Rival': rival,
                    'Localizacion': loc,
                    'Escudo': escudo
                }
                
                if rival and escudo and escudo != 'nan':
                    dict_escudos[rival.lower()] = escudo

    return df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo, dict_rankings_reales, df_rank_base, df_ref_vam, df_ref_campo, dict_escudos, dict_calendario

df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo, dict_rankings_reales, df_rank_base, df_ref_vam, df_ref_campo, dict_escudos, dict_calendario = cargar_todo_informes()

def calc_mean_std(df, date_col, val_col):
    if df is None or df.empty or val_col not in df.columns: return pd.DataFrame()
    dff = df.dropna(subset=[val_col]).copy()
    if dff.empty: return pd.DataFrame()
    dff[val_col] = pd.to_numeric(dff[val_col], errors='coerce')
    agg = dff.groupby(date_col).agg(Fecha=('Fecha', 'first'), Mean=(val_col, 'mean'), Std=(val_col, 'std')).reset_index().sort_values(date_col)
    agg['Std'] = agg['Std'].fillna(0)
    return agg

def get_logo(rival_str):
    if not rival_str or rival_str.lower() in ['nan', 'none', '']: return "https://cdn-icons-png.flaticon.com/512/53/53283.png"
    r_low = rival_str.lower()
    if r_low in dict_escudos: return dict_escudos[r_low]
    for k, v in dict_escudos.items():
        if k in r_low or r_low in k:
            return v
    return "https://cdn-icons-png.flaticon.com/512/53/53283.png"

# =============================================================================
# 3. SELECTOR DE JUGADOR
# =============================================================================
lista_jugadores = sorted(df_pos['Nombre'].dropna().unique()) if not df_pos.empty else []
if not lista_jugadores and not df_cuest.empty:
    lista_jugadores = sorted(df_cuest['Nombre'].dropna().unique())

if not lista_jugadores:
    st.warning("⚠️ No se encontraron jugadores registrados en el sistema.")
    st.stop()

col_filtro, _ = st.columns([1.0, 3.9], gap="medium")
with col_filtro:
    jugador_sel = st.selectbox("Selector oculto:", lista_jugadores, label_visibility="collapsed")

st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
jug_norm = norm_nom(jugador_sel)
match_pos = df_pos[df_pos['Nombre_Norm'] == jug_norm] if not df_pos.empty else pd.DataFrame()
match_cuest = df_cuest[df_cuest['Nombre_Norm'] == jug_norm] if not df_cuest.empty else pd.DataFrame()
if match_cuest.empty and not df_cuest.empty and 'Nombre_Norm' in df_cuest.columns:
    def fuzzy_match(n):
        if pd.isna(n): return False
        n_str, j_str = str(n).lower(), jug_norm.lower()
        if n_str in j_str or j_str in n_str: return True
        return len(set(n_str.split()) & set(j_str.split())) >= 2
    match_cuest = df_cuest[df_cuest['Nombre_Norm'].apply(fuzzy_match)]

url_foto_jugador = match_pos.iloc[0].get('Foto_URL', None) if not match_pos.empty and 'Foto_URL' in match_pos.columns else None

fecha_nac_str = "Por definir"
if not match_pos.empty and 'Fecha_Nacimiento_Pos' in match_pos.columns:
    val = str(match_pos.iloc[0]['Fecha_Nacimiento_Pos']).replace('00:00:00', '').strip()
    if val.lower() not in ['nan', 'none', 'por definir', '0', '', 'nat']: fecha_nac_str = val
elif not match_cuest.empty and 'Fecha_Nacimiento' in match_cuest.columns:
    val = str(match_cuest.iloc[-1]['Fecha_Nacimiento']).strip()
    if val.lower() not in ['nan', 'none', 'por definir', '0', '']: fecha_nac_str = val

posicion_str = "Por definir"
if not match_pos.empty and 'Posicion' in match_pos.columns:
    posicion_str = str(match_pos.iloc[0]['Posicion']).strip()
elif not match_cuest.empty and 'Posicion_Habitual' in match_cuest.columns:
    val_p = str(match_cuest.iloc[-1]['Posicion_Habitual']).strip()
    if val_p.lower() not in ['nan', 'none', 'por definir', '0', '']: posicion_str = val_p

lado_str = ""
if not match_pos.empty and 'Lado' in match_pos.columns:
    val_l = match_pos.iloc[0]['Lado']
    if pd.notna(val_l) and str(val_l).strip().lower() not in ['nan', 'none', '']:
        lado_str = str(val_l).strip()

pierna_str = "Por definir"
if not match_pos.empty and 'Pierna_Pos' in match_pos.columns:
    val = str(match_pos.iloc[0]['Pierna_Pos']).strip()
    if val.lower() not in ['nan', 'none', 'por definir', '0', '']: pierna_str = val
elif not match_cuest.empty and 'Pierna_Dominante' in match_cuest.columns:
    val = str(match_cuest.iloc[-1]['Pierna_Dominante']).strip()
    if val.lower() not in ['nan', 'none', 'por definir', '0', '']: pierna_str = val

ranking_real_str = dict_rankings_reales.get(jug_norm, "#--")
nombre_mostrar = jugador_sel.replace('_', ' ').upper()

# =============================================================================
# 4. PREPARACIÓN DE DATOS GPS Y MATCH OUTPUT
# =============================================================================
df_p_jug = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm].copy() if not df_gps_all.empty else pd.DataFrame()

if not df_p_jug.empty:
    df_p_jug['Fecha_Date'] = df_p_jug['Fecha_dt'].dt.date
    
    if not df_rpe.empty:
        df_rpe_jug = df_rpe[df_rpe['Nombre_Norm'] == jug_norm].copy()
        df_rpe_jug['Fecha_Date'] = df_rpe_jug['Fecha_dt'].dt.date
        df_rpe_jug = df_rpe_jug.sort_values('Fecha_dt', ascending=False).drop_duplicates(subset=['Fecha_Date'])
        rpe_cols = ['Fecha_Date', 'Tipo_Sesion', 'Minutos', 'RPE_Score']
        df_p_jug = pd.merge(df_p_jug, df_rpe_jug[[c for c in rpe_cols if c in df_rpe_jug.columns]], on='Fecha_Date', how='left')
    
    def get_cal_data(f_date, key):
        if f_date in dict_calendario: return dict_calendario[f_date].get(key, '')
        return ''
        
    df_p_jug['Rival'] = df_p_jug['Fecha_Date'].apply(lambda d: get_cal_data(d, 'Rival'))
    df_p_jug['Localizacion'] = df_p_jug['Fecha_Date'].apply(lambda d: get_cal_data(d, 'Localizacion'))
    df_p_jug['Is_Partido'] = df_p_jug['Rival'] != ''

    if 'Tipo_Sesion' not in df_p_jug.columns: df_p_jug['Tipo_Sesion'] = ''
    if 'RPE_Score' not in df_p_jug.columns: df_p_jug['RPE_Score'] = 0
    if 'Minutos' not in df_p_jug.columns: df_p_jug['Minutos'] = 0
        
    df_p_jug['Tipo_Sesion'] = df_p_jug['Tipo_Sesion'].fillna('')
    df_p_jug['Minutos'] = df_p_jug['Minutos'].fillna(0)
    
    labels = []
    for idx, r in df_p_jug.iterrows():
        ts = str(r['Tipo_Sesion']).strip()
        if r['Is_Partido']:
            riv = str(r['Rival']).strip()
            loc = str(r['Localizacion']).strip()
            l_str = f"{riv} ({loc})" if loc else riv
            labels.append(l_str)
            if ts == '' or str(ts).lower() == 'nan' or 'entrenamiento' in ts.lower(): 
                df_p_jug.at[idx, 'Tipo_Sesion'] = 'Partido'
        else:
            labels.append(ts if ts and str(ts).lower() != 'nan' else 'Entrenamiento')
            if ts == '' or str(ts).lower() == 'nan': df_p_jug.at[idx, 'Tipo_Sesion'] = 'Entrenamiento'
            
    df_p_jug['Label'] = labels

minutos_totales_partido = 0
if not df_p_jug.empty:
    df_m = df_p_jug[df_p_jug['Is_Partido'] == True]
    minutos_totales_partido = int(df_m['Minutos'].sum())

# =============================================================================
# 5. CAMPOGRAMA
# =============================================================================
def _campograma_v0(pos_str, pierna_s, lado_s="", nombre_mostrar="PLAYER"):
    fig = go.Figure()
    line = dict(color=BORDER, width=1.5)
    pitch = "#0f1c14"
    fig.add_shape(type="rect", x0=0, y0=0, x1=68, y1=105, line=line, fillcolor=pitch, layer="below")
    fig.add_shape(type="line", x0=0, y0=52.5, x1=68, y1=52.5, line=line)
    fig.add_shape(type="circle", x0=24.85, y0=43.35, x1=43.15, y1=61.65, line=line)
    fig.add_shape(type="circle", x0=33.5, y0=52, x1=34.5, y1=53, line=dict(color=BORDER, width=1), fillcolor=BORDER)
    for y0, y1 in [(0, 16.5), (88.5, 105)]: fig.add_shape(type="rect", x0=13.84, y0=y0, x1=54.16, y1=y1, line=line)
    for y0, y1 in [(0, 5.5), (99.5, 105)]: fig.add_shape(type="rect", x0=24.84, y0=y0, x1=43.16, y1=y1, line=line)

    pos_low = (str(pos_str) + " " + str(lado_s)).lower()
    pierna_low = str(pierna_s).lower()
    es_izq = any(k in pos_low for k in ['izq', 'zurd', 'left']) or ('zurd' in pierna_low)
    es_der = any(k in pos_low for k in ['der', 'dext', 'right', 'diest']) or ('diest' in pierna_low or 'dext' in pierna_low)

    if 'porter' in pos_low or 'gk' in pos_low: px, py, code_text = 34, 8, "POR"
    elif 'central' in pos_low or 'cb' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 24, 20, "CI"
        elif 'der' in pos_low: px, py, code_text = 44, 20, "CD"
        else: px, py, code_text = 34, 20, "CEN"
    elif 'lateral' in pos_low or 'cad' in pos_low or 'carril' in pos_low:
        if 'izq' in pos_low or (es_izq and not 'der' in pos_low): px, py, code_text = 8, 25, "LI"
        else: px, py, code_text = 60, 25, "LD"
    elif 'medio' in pos_low or 'pivote' in pos_low or 'mediocentro' in pos_low or 'cm' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 24, 45, "MCI"
        elif 'der' in pos_low: px, py, code_text = 44, 45, "MCD"
        else: px, py, code_text = 34, 45, "MC"
    elif 'interior' in pos_low or 'mediapunta' in pos_low or 'cam' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 24, 65, "INT"
        elif 'der' in pos_low: px, py, code_text = 44, 65, "INT"
        else: px, py, code_text = 34, 65, "MP"
    elif 'extremo' in pos_low or 'banda' in pos_low or 'wing' in pos_low:
        if 'izq' in pos_low or (es_izq and not 'der' in pos_low): px, py, code_text = 10, 80, "EI"
        else: px, py, code_text = 58, 80, "ED"
    elif 'delantero' in pos_low or 'punta' in pos_low or 'atacante' in pos_low or 'st' in pos_low: px, py, code_text = 34, 92, "DC"
    else: px, py, code_text = 34, 52.5, "JUG"

    fig.add_trace(go.Scatter(x=[px], y=[py], mode="markers+text", text=[f"<b>{code_text}</b>"], textposition="middle center", textfont=dict(color="#ffffff", size=10, family="sans-serif"), marker=dict(size=28, color=PRIMARY, line=dict(color="#ffffff", width=2)), hovertemplate=f"<b>{nombre_mostrar}</b><br>{pos_str} {lado_s}<extra></extra>", showlegend=False))
    fig.update_xaxes(visible=False, range=[-3, 71])
    fig.update_yaxes(visible=False, range=[-3, 108], scaleanchor="x", scaleratio=1)
    fig.update_layout(height=330, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

# =============================================================================
# 6. RENDERIZADO DEL ENCABEZADO
# =============================================================================
col_photo, col_hero, col_pitch = st.columns([1.0, 2.7, 1.1], gap="medium")

with col_photo:
    if url_foto_jugador and pd.notna(url_foto_jugador): st.markdown(f'<img src="{url_foto_jugador}" class="photo-v0">', unsafe_allow_html=True)
    else: st.markdown(f'<div class="photo-placeholder-v0"><span style="font-size:3.2rem; font-weight:900; color:{PRIMARY};">AD</span></div>', unsafe_allow_html=True)

with col_hero:
    pos_label_full = f"{posicion_str.upper()} {lado_str.upper()}".strip()
    html_hero = f"""
        <div class="pd-hero">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <h1 class="pd-name" style="margin-top:0;">{nombre_mostrar}</h1>
                    <div style="margin-top: 0.6rem;"><span class="pd-badge">{pos_label_full}</span></div>
                    <div class="pd-club">ADARVE JUVENIL DH &middot; Temporada 2026/27</div>
                </div>
                <img src="{url_escudo_oficial}" style="width:46px; height:auto;">
            </div>
            <div class="pd-facts">
                <div class="pd-fact"><div class="k">Nacimiento</div><div class="v">{fecha_nac_str}</div></div>
                <div class="pd-fact"><div class="k">Pierna</div><div class="v v-cyan">{pierna_str.upper()}</div></div>
                <div class="pd-fact"><div class="k">Minutos Partidos</div><div class="v v-gold">{minutos_totales_partido}′</div></div>
                <div class="pd-fact"><div class="k">Ranking</div><div class="v v-green">{ranking_real_str}</div></div>
            </div>
        </div>
    """
    st.markdown(html_hero, unsafe_allow_html=True)

with col_pitch:
    st.plotly_chart(_campograma_v0(posicion_str, pierna_str, lado_str, nombre_mostrar), use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# 7. PESTAÑAS DE SUB-PÁGINAS ESTILO V0
# =============================================================================
tab_tests, tab_gps = st.tabs(["  Conditioning Tests  ", "  GPS & Match Output  "])

with tab_tests:
    st.markdown('<div class="pd-section-title">MEJORES REGISTROS TEMPORADA</div>', unsafe_allow_html=True)
    
    def get_best(df, col_jugador, jug_norm_val, col_val, filter_col=None, filter_val=None, exact=False):
        if df is None or df.empty or col_val not in df.columns or col_jugador not in df.columns: return None
        dff = df.copy()
        if filter_col and filter_col in dff.columns and filter_val: 
            if exact:
                dff = dff[dff[filter_col].astype(str).str.upper() == str(filter_val).upper()]
            else:
                dff = dff[dff[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]
        dff[col_val] = pd.to_numeric(dff[col_val], errors='coerce')
        dff = dff.dropna(subset=[col_val])
        jug_data = dff[dff[col_jugador] == jug_norm_val]
        if jug_data.empty: return None
        if 'DEC_MAX' in col_val: return jug_data[col_val].min()
        return jug_data[col_val].max()

    v_cmj = get_best(df_saltos, 'Nombre_Norm', jug_norm, 'Altura', 'Tipo_Norm', 'CMJ', exact=True)
    v_vam = get_best(df_vam, 'Nombre_Norm', jug_norm, 'VAM')
    v_dj = get_best(df_dri, 'Nombre_Norm', jug_norm, 'Altura')
    v_dri = get_best(df_dri, 'Nombre_Norm', jug_norm, 'DRI')
    v_pb = get_best(df_fts, 'Nombre_Norm', jug_norm, 'Press_Banca')
    v_dom = get_best(df_fts, 'Nombre_Norm', jug_norm, 'Dominada')
    v_vmax = get_best(df_campo, 'Nombre_Norm', jug_norm, 'V_MAX')
    v_ac = get_best(df_campo, 'Nombre_Norm', jug_norm, 'AC_MAX')
    v_dec = get_best(df_campo, 'Nombre_Norm', jug_norm, 'DEC_MAX')

    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)

    def render_kpi(col, title, val, unit, decimals=1):
        if val is not None and not pd.isna(val):
            fmt_val = f"{val:.{decimals}f} {unit}".strip()
            if unit == "reps": fmt_val = f"{int(val)} {unit}"
            col.metric(title, fmt_val)
        else: col.metric(title, "-")

    render_kpi(r1c1, "Salto CMJ", v_cmj, "cm")
    render_kpi(r1c2, "Prueba 5 min", v_vam, "km/h")
    render_kpi(r1c3, "Drop Jump (50cm)", v_dj, "cm")
    render_kpi(r1c4, "Índice DRI DJ", v_dri, "", decimals=2)
    render_kpi(r1c5, "Press Banca", v_pb, "reps")
    render_kpi(r2c1, "Dominadas", v_dom, "reps")
    render_kpi(r2c2, "V. Máx", v_vmax, "km/h")
    render_kpi(r2c3, "Acel. Máx", v_ac, "m/s²", decimals=2)
    render_kpi(r2c4, "Decel. Máx", v_dec, "m/s²", decimals=2)

    st.divider()

    left_col, right_col = st.columns([1.5, 1], gap="large")

    with left_col:
        st.markdown('<div class="pd-section-title">Evolución de tests en el tiempo</div>', unsafe_allow_html=True)
        test_categoria = st.selectbox("Selecciona Batería de Tests:", ["🩺 Movilidad", "🫁 VAM Aeróbico", "⚙️ Dinamometría", "🚀 Saltos & DRI", "🏋️ Tren Superior", "⚡ Velocidad en Campo"], label_visibility="collapsed")
        
        df_j_mov = df_mov[df_mov['Nombre_Norm'] == jug_norm].copy() if df_mov is not None and not df_mov.empty else pd.DataFrame()
        df_j_vam = df_vam[df_vam['Nombre_Norm'] == jug_norm].copy() if df_vam is not None and not df_vam.empty else pd.DataFrame()
        df_j_dina = df_dina[df_dina['Nombre_Norm'] == jug_norm].copy() if df_dina is not None and not df_dina.empty else pd.DataFrame()
        df_j_s = df_saltos[df_saltos['Nombre_Norm'] == jug_norm].copy() if df_saltos is not None and not df_saltos.empty else pd.DataFrame()
        df_j_ts = df_fts[df_fts['Nombre_Norm'] == jug_norm].copy() if df_fts is not None and not df_fts.empty else pd.DataFrame()
        df_j_campo = df_campo[df_campo['Nombre_Norm'] == jug_norm].copy() if df_campo is not None and not df_campo.empty else pd.DataFrame()

        if test_categoria == "🩺 Movilidad":
            sub_mov = st.radio("Test de Movilidad:", ["Dorsiflexión", "Rotación Interna", "Flexión Cadera"], horizontal=True)
            if not df_j_mov.empty:
                fig_m = go.Figure()
                if sub_mov == "Dorsiflexión":
                    agg = calc_mean_std(df_j_mov, 'Fecha_dt', 'DORSIFLEX_D')
                    if not agg.empty: fig_m.add_trace(go.Scatter(x=agg['Fecha'], y=agg['Mean'], error_y=dict(type='data', array=agg['Std'], visible=True), mode='lines+markers', name='Derecha', line=dict(color=PRIMARY, width=3)))
                    agg_i = calc_mean_std(df_j_mov, 'Fecha_dt', 'DORSIFLEX_I')
                    if not agg_i.empty: fig_m.add_trace(go.Scatter(x=agg_i['Fecha'], y=agg_i['Mean'], error_y=dict(type='data', array=agg_i['Std'], visible=True), mode='lines+markers', name='Izquierda', line=dict(color=TEAM, width=3)))
                    fig_m.add_hline(y=12, line_dash="dash", line_color=GOOD, annotation_text="Ref: 12 cm")
                elif sub_mov == "Rotación Interna":
                    agg = calc_mean_std(df_j_mov, 'Fecha_dt', 'ROT_INT_D')
                    if not agg.empty: fig_m.add_trace(go.Scatter(x=agg['Fecha'], y=agg['Mean'], error_y=dict(type='data', array=agg['Std'], visible=True), mode='lines+markers', name='Derecha', line=dict(color=PRIMARY, width=3)))
                    agg_i = calc_mean_std(df_j_mov, 'Fecha_dt', 'ROT_INT_I')
                    if not agg_i.empty: fig_m.add_trace(go.Scatter(x=agg_i['Fecha'], y=agg_i['Mean'], error_y=dict(type='data', array=agg_i['Std'], visible=True), mode='lines+markers', name='Izquierda', line=dict(color=TEAM, width=3)))
                    fig_m.add_hline(y=35, line_dash="dash", line_color=GOOD, annotation_text="Ref: 35°")
                elif sub_mov == "Flexión Cadera":
                    agg = calc_mean_std(df_j_mov, 'Fecha_dt', 'FLEX_CAD_D')
                    if not agg.empty: fig_m.add_trace(go.Scatter(x=agg['Fecha'], y=agg['Mean'], error_y=dict(type='data', array=agg['Std'], visible=True), mode='lines+markers', name='Derecha', line=dict(color=PRIMARY, width=3)))
                    agg_i = calc_mean_std(df_j_mov, 'Fecha_dt', 'FLEX_CAD_I')
                    if not agg_i.empty: fig_m.add_trace(go.Scatter(x=agg_i['Fecha'], y=agg_i['Mean'], error_y=dict(type='data', array=agg_i['Std'], visible=True), mode='lines+markers', name='Izquierda', line=dict(color=TEAM, width=3)))
                    fig_m.add_hline(y=90, line_dash="dash", line_color=GOOD, annotation_text="Ref: 90°")
                
                fig_m.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": False})
            else: st.info("No hay datos para este test.")

        elif test_categoria == "🫁 VAM Aeróbico":
            if not df_j_vam.empty:
                agg = calc_mean_std(df_j_vam, 'Fecha_dt', 'VAM')
                fig_v = go.Figure()
                fig_v.add_trace(go.Scatter(x=agg['Fecha'], y=agg['Mean'], error_y=dict(type='data', array=agg['Std'], visible=True), mode='lines+markers', name='VAM', line=dict(color=PRIMARY, width=3)))
                
                ref_vam_val = None
                if df_ref_vam is not None and not df_ref_vam.empty:
                    df_ref_vam.columns = [str(c).strip() for c in df_ref_vam.columns]
                    c_pos_ref = next((c for c in df_ref_vam.columns if 'posicion' in c.lower() or 'posición' in c.lower()), df_ref_vam.columns[0])
                    c_vam_ref = next((c for c in df_ref_vam.columns if 'vam' in c.lower()), df_ref_vam.columns[1])
                    for _, row in df_ref_vam.iterrows():
                        ref_p = str(row[c_pos_ref]).strip().lower()
                        if ref_p and ref_p in posicion_str.lower():
                            ref_vam_val = pd.to_numeric(row[c_vam_ref], errors='coerce')
                            break
                
                if ref_vam_val and pd.notna(ref_vam_val):
                    fig_v.add_shape(type="line", x0=-0.5, x1=len(agg['Fecha'])-0.5, y0=ref_vam_val, y1=ref_vam_val, line=dict(color=GOOD, width=2, dash="dash"))
                    fig_v.add_annotation(x=len(agg['Fecha'])-1, y=ref_vam_val, text=f"Ref Posición: {ref_vam_val} km/h", showarrow=False, yshift=12, font=dict(color=GOOD, size=10), xanchor="right")
                
                fig_v.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False})
            else: st.info("No hay datos aeróbicos.")

        elif test_categoria == "⚙️ Dinamometría":
            if not df_j_dina.empty:
                df_j_dina['Fmax_Abs'] = pd.to_numeric(df_j_dina['Fmax_Abs'], errors='coerce')
                agg = df_j_dina.groupby(['Fecha', 'Fecha_dt', 'Exercise'], as_index=False)['Fmax_Abs'].mean()
                
                def get_lado_base(ex):
                    ex_str = str(ex).strip()
                    ex_low = ex_str.lower()
                    if "derecha" in ex_low or "_der" in ex_low or " der" in ex_low: lado = "Derecha"
                    elif "izquierda" in ex_low or "_izq" in ex_low or " izq" in ex_low: lado = "Izquierda"
                    else: lado = "Bilateral"
                    
                    base = re.sub(r'(?i)[_-]?derecha', '', ex_str)
                    base = re.sub(r'(?i)[_-]?izquierda', '', base)
                    base = re.sub(r'(?i)[_-]?der\b', '', base)
                    base = re.sub(r'(?i)[_-]?izq\b', '', base)
                    return pd.Series([lado, base.replace('_', ' ').strip()])
                    
                agg[['Lado', 'Base_Exercise']] = agg['Exercise'].apply(get_lado_base)
                agg = agg.sort_values(['Fecha_dt', 'Base_Exercise'])
                
                fig_d = go.Figure()
                for lado, color in [('Derecha', PRIMARY), ('Izquierda', TEAM), ('Bilateral', GOOD)]:
                    df_lado = agg[agg['Lado'] == lado]
                    if not df_lado.empty:
                        fig_d.add_trace(go.Bar(
                            x=[df_lado['Fecha'], df_lado['Base_Exercise']],
                            y=df_lado['Fmax_Abs'],
                            name=lado,
                            marker_color=color,
                            text=df_lado['Fmax_Abs'].round(1),
                            textposition='outside',
                            textfont=dict(color=TEXT)
                        ))
                
                fig_d.update_layout(
                    height=400, 
                    barmode='group',
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color=TEXT),
                    xaxis=dict(tickangle=0, dividerwidth=2, dividercolor=BORDER),
                    yaxis_title="Fmax Abs (N)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, title="")
                )
                st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})
            else: st.info("No hay datos de dinamometría para este jugador.")

        elif test_categoria == "🚀 Saltos & DRI":
            sub_s = st.radio("Vista:", ["Evolución CMJ", "Evolución DRI y DJ"], horizontal=True)
            if sub_s == "Evolución CMJ":
                if not df_j_s.empty:
                    fig_s = go.Figure()
                    for t_norm, col_name, c_color in [('CMJ', 'CMJ Total', PRIMARY), ('CMJ_D', 'slCMJ Derecha', TEAM), ('CMJ_I', 'slCMJ Izquierda', WARNING)]:
                        df_t = df_j_s[df_j_s['Tipo_Norm'] == t_norm]
                        agg = calc_mean_std(df_t, 'Fecha_dt', 'Altura')
                        if not agg.empty: 
                            fig_s.add_trace(go.Scatter(x=agg['Fecha'], y=agg['Mean'], error_y=dict(type='data', array=agg['Std'], visible=True), mode='lines+markers', name=col_name, line=dict(color=c_color, width=3), marker=dict(size=8)))
                    
                    fig_s.add_hline(y=38.5, line_dash="dash", line_color=PRIMARY, annotation_text="Ref CMJ")
                    fig_s.add_hline(y=21.0, line_dash="dash", line_color=WARNING, annotation_text="Ref slCMJ")
                    
                    fig_s.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos de saltos.")
            else:
                df_j_dri = df_dri[df_dri['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt') if df_dri is not None and not df_dri.empty else pd.DataFrame()
                if not df_j_dri.empty:
                    fig_dri = make_subplots(specs=[[{"secondary_y": True}]])
                    agg_dri = calc_mean_std(df_j_dri, 'Fecha_dt', 'DRI')
                    agg_dj = calc_mean_std(df_j_dri, 'Fecha_dt', 'Altura')
                    
                    if not agg_dri.empty: 
                        fig_dri.add_trace(go.Bar(x=agg_dri['Fecha'], y=agg_dri['Mean'], error_y=dict(type='data', array=agg_dri['Std'], visible=True), name='Índice DRI', marker_color=PRIMARY), secondary_y=False)
                    if not agg_dj.empty: 
                        fig_dri.add_trace(go.Scatter(x=agg_dj['Fecha'], y=agg_dj['Mean'], error_y=dict(type='data', array=agg_dj['Std'], visible=True), mode='lines+markers', name='Altura DJ (cm)', line=dict(color=TEAM, width=3, dash='dot'), marker=dict(size=8)), secondary_y=True)
                    
                    fig_dri.update_yaxes(title_text="Índice DRI", secondary_y=False, showgrid=True, gridcolor=BORDER, zeroline=False, rangemode='tozero')
                    fig_dri.update_yaxes(title_text="Altura DJ (cm)", secondary_y=True, showgrid=False, zeroline=False, rangemode='tozero')
                    
                    fig_dri.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT), legend=dict(orientation="h", y=-0.2), barmode='group')
                    st.plotly_chart(fig_dri, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos DRI y Drop Jump.")

        elif test_categoria == "🏋️ Tren Superior":
            if not df_j_ts.empty:
                fig_ts = go.Figure()
                agg_pb = calc_mean_std(df_j_ts, 'Fecha_dt', 'Press_Banca')
                agg_dom = calc_mean_std(df_j_ts, 'Fecha_dt', 'Dominada')
                
                mean_eq_pb = df_fts['Press_Banca'].mean() if df_fts is not None and not df_fts.empty else 0
                mean_eq_dom = df_fts['Dominada'].mean() if df_fts is not None and not df_fts.empty else 0

                if not agg_pb.empty: fig_ts.add_trace(go.Scatter(x=agg_pb['Fecha'], y=agg_pb['Mean'], error_y=dict(type='data', array=agg_pb['Std'], visible=True), mode='lines+markers', name='Press Banca', line=dict(color=PRIMARY, width=3)))
                if not agg_dom.empty: fig_ts.add_trace(go.Scatter(x=agg_dom['Fecha'], y=agg_dom['Mean'], error_y=dict(type='data', array=agg_dom['Std'], visible=True), mode='lines+markers', name='Dominadas', line=dict(color=TEAM, width=3)))
                
                fig_ts.add_hline(y=mean_eq_pb, line_dash="dash", line_color=PRIMARY, opacity=0.5, annotation_text="Media Eq PB")
                fig_ts.add_hline(y=mean_eq_dom, line_dash="dash", line_color=TEAM, opacity=0.5, annotation_text="Media Eq Dom")
                
                fig_ts.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
            else: st.info("No hay datos de Tren Superior.")

        elif test_categoria == "⚡ Velocidad en Campo":
            if not df_j_campo.empty:
                agg_v = calc_mean_std(df_j_campo, 'Fecha_dt', 'V_MAX')
                agg_ac = calc_mean_std(df_j_campo, 'Fecha_dt', 'AC_MAX')
                agg_dec = calc_mean_std(df_j_campo, 'Fecha_dt', 'DEC_MAX')
                
                fig_vel = make_subplots(specs=[[{"secondary_y": True}]])
                if not agg_v.empty: fig_vel.add_trace(go.Scatter(x=agg_v['Fecha'], y=agg_v['Mean'], error_y=dict(type='data', array=agg_v['Std'], visible=True), mode='lines+markers', name='V_MAX (km/h)', line=dict(color=PRIMARY, width=3)), secondary_y=False)
                if not agg_ac.empty: fig_vel.add_trace(go.Scatter(x=agg_ac['Fecha'], y=agg_ac['Mean'], mode='lines+markers', name='Acel Max (m/s²)', line=dict(color=GOOD, width=2, dash='dot')), secondary_y=True)
                if not agg_dec.empty: fig_vel.add_trace(go.Scatter(x=agg_dec['Fecha'], y=agg_dec['Mean'], mode='lines+markers', name='Decel Max (m/s²)', line=dict(color=WARNING, width=2, dash='dot')), secondary_y=True)
                
                ref_vmax, ref_acmax, ref_decmax = None, None, None
                if df_ref_campo is not None and not df_ref_campo.empty:
                    df_ref_campo.columns = [str(c).strip().lower() for c in df_ref_campo.columns]
                    c_pos_c = next((c for c in df_ref_campo.columns if 'posic' in c), df_ref_campo.columns[0])
                    c_vmax = next((c for c in df_ref_campo.columns if 'v_max' in c or 'v. max' in c or 'vmax' in c), None)
                    c_acmax = next((c for c in df_ref_campo.columns if 'ac_max' in c or 'ac. max' in c or 'acmax' in c or 'acel' in c), None)
                    c_decmax = next((c for c in df_ref_campo.columns if 'dec_max' in c or 'dec. max' in c or 'decmax' in c or 'decel' in c), None)
                    for _, row in df_ref_campo.iterrows():
                        ref_p = str(row[c_pos_c]).strip().lower()
                        if ref_p and ref_p in posicion_str.lower():
                            if c_vmax: ref_vmax = pd.to_numeric(row[c_vmax], errors='coerce')
                            if c_acmax: ref_acmax = pd.to_numeric(row[c_acmax], errors='coerce')
                            if c_decmax: ref_decmax = pd.to_numeric(row[c_decmax], errors='coerce')
                            break
                
                if pd.isna(ref_vmax) or ref_vmax is None: ref_vmax = df_campo['V_MAX'].mean() if not df_campo.empty else None
                if pd.isna(ref_acmax) or ref_acmax is None: ref_acmax = df_campo['AC_MAX'].mean() if not df_campo.empty else None
                if pd.isna(ref_decmax) or ref_decmax is None: ref_decmax = df_campo['DEC_MAX'].mean() if not df_campo.empty else None

                if ref_vmax and pd.notna(ref_vmax):
                    fig_vel.add_hline(y=ref_vmax, line_dash="dash", line_color=PRIMARY, annotation_text=f"Ref V.Máx: {ref_vmax:.1f}", yref="y")
                if ref_acmax and pd.notna(ref_acmax):
                    fig_vel.add_hline(y=ref_acmax, line_dash="dash", line_color=GOOD, annotation_text=f"Ref AC.Máx: {ref_acmax:.2f}", yref="y2")
                if ref_decmax and pd.notna(ref_decmax):
                    fig_vel.add_hline(y=ref_decmax, line_dash="dash", line_color=WARNING, annotation_text=f"Ref DEC.Máx: {ref_decmax:.2f}", yref="y2")

                fig_vel.update_yaxes(title_text="V_MAX (km/h)", range=[20, 40], showgrid=True, gridcolor=BORDER, zeroline=False, secondary_y=False)
                fig_vel.update_yaxes(title_text="Acel / Decel (m/s²)", range=[-8, 8], showgrid=False, zeroline=False, secondary_y=True)
                fig_vel.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT), legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_vel, use_container_width=True, config={"displayModeBar": False})
            else: st.info("No hay datos de Velocidad en Campo.")

    with right_col:
        st.markdown('<div class="pd-section-title">Perfil Z-Score &middot; Radar</div>', unsafe_allow_html=True)
        
        all_dates = pd.Series(dtype='datetime64[ns]')
        if df_vam is not None and not df_vam.empty: all_dates = pd.concat([all_dates, df_vam['Fecha_dt']])
        if df_saltos is not None and not df_saltos.empty: all_dates = pd.concat([all_dates, df_saltos['Fecha_dt']])
        if df_dri is not None and not df_dri.empty: all_dates = pd.concat([all_dates, df_dri['Fecha_dt']])
        if df_fts is not None and not df_fts.empty: all_dates = pd.concat([all_dates, df_fts['Fecha_dt']])
        if df_campo is not None and not df_campo.empty: all_dates = pd.concat([all_dates, df_campo['Fecha_dt']])
        all_dates = all_dates.dropna()

        if not all_dates.empty:
            unique_dates = np.sort(all_dates.dt.date.unique())[::-1]
            filtro_radar = st.selectbox("Fecha de Evaluación (Z-Score):", unique_dates, format_func=lambda x: x.strftime('%d/%m/%Y'))

            def get_metric_zscore(df, val_col, target_date):
                if df is None or df.empty or val_col not in df.columns: return pd.DataFrame()
                dff = df[df['Fecha_dt'].dt.date == target_date].copy()
                if dff.empty: return pd.DataFrame()
                dff[val_col] = pd.to_numeric(dff[val_col], errors='coerce')
                agg = dff.groupby('Nombre_Norm')[val_col].max().reset_index()
                mean_v = agg[val_col].mean()
                std_v = agg[val_col].std()
                if pd.isna(std_v) or std_v == 0: std_v = 1
                agg[f'Z_{val_col}'] = (agg[val_col] - mean_v) / std_v
                return agg

            df_radar = df_pos[['Nombre_Norm', 'Posicion']].copy() if not df_pos.empty else pd.DataFrame(columns=['Nombre_Norm', 'Posicion'])

            df_vam_z = get_metric_zscore(df_vam, 'VAM', filtro_radar)
            if not df_vam_z.empty: df_radar = pd.merge(df_radar, df_vam_z[['Nombre_Norm', 'Z_VAM']], on='Nombre_Norm', how='left')

            df_cmj = df_saltos[df_saltos['Tipo_Norm'] == 'CMJ'] if df_saltos is not None and not df_saltos.empty else pd.DataFrame()
            df_cmj_z = get_metric_zscore(df_cmj, 'Altura', filtro_radar)
            if not df_cmj_z.empty: 
                df_cmj_z.rename(columns={'Z_Altura': 'Z_CMJ'}, inplace=True)
                df_radar = pd.merge(df_radar, df_cmj_z[['Nombre_Norm', 'Z_CMJ']], on='Nombre_Norm', how='left')

            df_dri_z = get_metric_zscore(df_dri, 'DRI', filtro_radar)
            if not df_dri_z.empty: df_radar = pd.merge(df_radar, df_dri_z[['Nombre_Norm', 'Z_DRI']], on='Nombre_Norm', how='left')

            if df_fts is not None and not df_fts.empty:
                df_fts_t = df_fts.copy()
                df_fts_t['Tren_Sup'] = pd.to_numeric(df_fts_t['Press_Banca'], errors='coerce').fillna(0) + pd.to_numeric(df_fts_t['Dominada'], errors='coerce').fillna(0)
                df_ts_z = get_metric_zscore(df_fts_t, 'Tren_Sup', filtro_radar)
                if not df_ts_z.empty: df_radar = pd.merge(df_radar, df_ts_z[['Nombre_Norm', 'Z_Tren_Sup']], on='Nombre_Norm', how='left')

            df_vmax_z = get_metric_zscore(df_campo, 'V_MAX', filtro_radar)
            if not df_vmax_z.empty: df_radar = pd.merge(df_radar, df_vmax_z[['Nombre_Norm', 'Z_V_MAX']], on='Nombre_Norm', how='left')

            categories = ['VAM', 'CMJ', 'DRI', 'Tren Sup.', 'V_MAX']
            cols = ['Z_VAM', 'Z_CMJ', 'Z_DRI', 'Z_Tren_Sup', 'Z_V_MAX']
            
            for c in cols:
                if c not in df_radar.columns: df_radar[c] = np.nan

            df_jug_r = df_radar[df_radar['Nombre_Norm'] == jug_norm]
            df_pos_r = df_radar[df_radar['Posicion'].astype(str).str.contains(posicion_str.split()[0], case=False, na=False)] if posicion_str != "Por definir" else df_radar

            v_j = [df_jug_r[c].mean() for c in cols]
            v_p = [df_pos_r[c].mean() for c in cols]
            v_eq = [0, 0, 0, 0, 0]

            v_j = [(x if pd.notna(x) else 0) for x in v_j]; v_j.append(v_j[0])
            v_p = [(x if pd.notna(x) else 0) for x in v_p]; v_p.append(v_p[0])
            v_eq.append(v_eq[0])
            cat_cl = categories + [categories[0]]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=v_eq, theta=cat_cl, fill="none", name="Media Equipo (0)", line=dict(color=MUTED, width=1.5, dash='dash')))
            fig_radar.add_trace(go.Scatterpolar(r=v_p, theta=cat_cl, fill="toself", name="Media Demarcación", line=dict(color=TEAM, width=2), fillcolor="rgba(56,189,248,0.15)"))
            fig_radar.add_trace(go.Scatterpolar(r=v_j, theta=cat_cl, fill="toself", name=nombre_mostrar, line=dict(color=PRIMARY, width=3), fillcolor="rgba(225,29,72,0.30)"))
            
            fig_radar.update_layout(
                height=550, margin=dict(l=60, r=60, t=40, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                polar=dict(
                    bgcolor=SURFACE_2, 
                    radialaxis=dict(range=[-3, 3], tickvals=[-2, -1, 0, 1, 2], ticktext=['-2 SD', '-1 SD', 'Media', '+1 SD', '+2 SD'], gridcolor=BORDER, tickfont=dict(color=MUTED, size=10)), 
                    angularaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT, size=13))
                ),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=12))
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No hay fechas registradas para calcular el Z-Score.")

# -----------------------------------------------------------------------------
# SUB-PAGE 2: GPS DATA Y MATCH OUTPUT
# -----------------------------------------------------------------------------
with tab_gps:
    if not df_p_jug.empty:
        st.markdown('<div class="pd-section-title">GPS Totals (Season)</div>', unsafe_allow_html=True)
        
        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Sesiones GPS", f"{len(df_p_jug)}")
        g2.metric("Distancia Total", f"{df_p_jug['Dist_Total'].sum()/1000:.1f} km" if not df_p_jug.empty else "0.0 km")
        g3.metric("Velocidad Máxima", f"{df_p_jug['V_MAX'].max():.1f} km/h" if not df_p_jug.empty else "0.0 km/h")
        g4.metric("Media Dist/Sesión", f"{df_p_jug['Dist_Total'].mean():.0f} m" if not df_p_jug.empty else "0 m")
        g5.metric("Acc + Dec Totales", f"{df_p_jug['Acc_Dec'].sum():.0f}" if not df_p_jug.empty else "0")

        st.divider()

        df_matches_all = df_gps_all.copy() if not df_gps_all.empty else pd.DataFrame()
        if not df_matches_all.empty:
            df_matches_all['Fecha_Date'] = df_matches_all['Fecha_dt'].dt.date
            df_matches_all['Is_Partido'] = df_matches_all['Fecha_Date'].isin(dict_calendario.keys())
            df_matches_all = df_matches_all[df_matches_all['Is_Partido']].copy()
            df_matches_all = pd.merge(df_matches_all, df_pos[['Nombre_Norm', 'Posicion']], on='Nombre_Norm', how='left')
        
        df_matches_jug = df_p_jug[df_p_jug['Is_Partido'] == True].sort_values('Fecha_dt', ascending=True).reset_index(drop=True) if not df_p_jug.empty else pd.DataFrame()
        
        st.markdown('<div class="pd-section-title">Rendimiento Competitivo en Partido (Match Output)</div>', unsafe_allow_html=True)
        
        if not df_matches_jug.empty and not df_matches_all.empty:
            
            if 'sel_match_dt' not in st.session_state or st.session_state['sel_match_dt'] not in df_matches_jug['Fecha_dt'].values:
                st.session_state['sel_match_dt'] = df_matches_jug.iloc[-1]['Fecha_dt']

            st.markdown("<p style='font-size:0.85rem; color:#8b949e; margin-bottom:0.75rem; font-weight:700;'>FILTRO DE PARTIDO (FIXTURE GRID):</p>", unsafe_allow_html=True)
            
            # PARRILLA DE BOTONES ESTILO FIXTURE GRID
            cols_per_row = 6
            for i in range(0, len(df_matches_jug), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for j, (idx, row) in enumerate(df_matches_jug.iloc[i:i+cols_per_row].iterrows()):
                    with row_cols[j]:
                        l_url = get_logo(row['Rival'])
                        st.markdown(f'<div style="text-align:center;"><img src="{l_url}" style="width:36px; height:36px; object-fit:contain; margin-bottom:2px;"></div>', unsafe_allow_html=True)
                        
                        loc_txt = str(row.get('Localizacion', '')).strip().upper()
                        loc_code = f" ({loc_txt[0]})" if loc_txt else ""
                        btn_label = f"J{idx+1} · {pd.to_datetime(row['Fecha_dt']).strftime('%d/%m')}{loc_code}"
                        
                        if st.button(btn_label, key=f"btn_fixture_{idx}"):
                            st.session_state['sel_match_dt'] = row['Fecha_dt']

            st.markdown("<br>", unsafe_allow_html=True)
            col_radar_match, col_metrics_panel = st.columns([1.8, 1.2], gap="large")

            cols_all_gps = [
                'Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'N_Sprints', 
                'N_Acc', 'N_Dec', 'AC_MAX', 'DEC_MAX', 'V_MAX', 'Player_Load'
            ]
            
            params_labels = [
                "Dist Total", "Dist >18", "Dist >25.2", "Dist >28.8", "Nº Sprints", 
                "Nº Acel", "Nº Decel", "Ac Max", "Dec Max", "V Max", "Player Load"
            ]

            pos_base = posicion_str.split()[0] if posicion_str != "Por definir" else ""
            df_matches_pos = df_matches_all[df_matches_all['Posicion'].astype(str).str.contains(pos_base, case=False, na=False)]
            
            if not df_matches_pos.empty:
                mean_pos = df_matches_pos[cols_all_gps].mean()
                std_pos = df_matches_pos[cols_all_gps].std().replace({0: 1, np.nan: 1})
                
                df_opt_base = df_matches_jug[df_matches_jug['Minutos'] > 60].sort_values('Fecha_dt', ascending=True).tail(4)
                if df_opt_base.empty: df_opt_base = df_matches_jug.sort_values('Fecha_dt', ascending=True).tail(4)
                mean_opt = df_opt_base[cols_all_gps].mean()
                
                match_data = df_matches_jug[df_matches_jug['Fecha_dt'] == st.session_state['sel_match_dt']]
                if match_data.empty: match_data = df_matches_jug.iloc[[-1]]
                row_selected = match_data.iloc[0]
                vals_match = row_selected[cols_all_gps]

                z_pos = [0] * len(cols_all_gps)
                z_opt = [(mean_opt[c] - mean_pos[c]) / std_pos[c] for c in cols_all_gps]
                z_match = [(vals_match[c] - mean_pos[c]) / std_pos[c] for c in cols_all_gps]

                # Cerrar radar
                z_pos += [z_pos[0]]
                z_opt += [z_opt[0]]
                z_match += [z_match[0]]
                theta_labels = params_labels + [params_labels[0]]

                with col_radar_match:
                    r_name = str(row_selected['Rival']).upper() if row_selected['Rival'] else "PARTIDO"
                    
                    fig_mr = go.Figure()
                    fig_mr.add_trace(go.Scatterpolar(r=z_pos, theta=theta_labels, fill="none", name="Media Posición (0)", line=dict(color=TEAM, width=2, dash='dash')))
                    fig_mr.add_trace(go.Scatterpolar(r=z_opt, theta=theta_labels, fill="toself", name="Perfil Óptimo (Ópt.)", line=dict(color=WARNING, width=2), fillcolor="rgba(245, 158, 11, 0.15)"))
                    fig_mr.add_trace(go.Scatterpolar(
                        r=z_match, theta=theta_labels, fill="toself", mode="lines+markers", name=f"vs {r_name}", 
                        line=dict(color=PRIMARY, width=3), fillcolor="rgba(225,29,72,0.30)"
                    ))
                    
                    fig_mr.update_layout(
                        height=500, margin=dict(l=60, r=60, t=40, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        polar=dict(
                            bgcolor=SURFACE_2, 
                            radialaxis=dict(showticklabels=False, showgrid=True, gridcolor=BORDER, range=[-2.5, 3.5]), 
                            angularaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT, size=12))
                        ),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=12))
                    )
                    st.plotly_chart(fig_mr, use_container_width=True, config={"displayModeBar": False})

                with col_metrics_panel:
                    st.markdown(f'<div class="pd-section-title">Valores Reales: vs {r_name}</div>', unsafe_allow_html=True)
                    
                    units_map = {
                        'Dist_Total': 'm', 'Dist_18': 'm', 'Dist_25': 'm', 'Dist_28': 'm',
                        'N_Sprints': 'sprints', 'N_Acc': 'acciones', 'N_Dec': 'acciones',
                        'AC_MAX': 'm/s²', 'DEC_MAX': 'm/s²', 'V_MAX': 'km/h', 'Player_Load': 'PL'
                    }

                    for i, col_k in enumerate(cols_all_gps):
                        lbl = params_labels[i]
                        val_m = vals_match[col_k]
                        unit = units_map.get(col_k, '')
                        
                        if col_k in ['V_MAX', 'AC_MAX', 'DEC_MAX']:
                            fmt_str = f"{val_m:.2f} {unit}"
                        else:
                            fmt_str = f"{val_m:.0f} {unit}"

                        st.markdown(f"""
                            <div class="metric-row">
                                <span class="metric-label">{lbl}</span>
                                <span class="metric-val">{fmt_str}</span>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No hay datos suficientes de posición para calcular el radar.")
        else:
            st.info("Aún no hay registros de partidos para construir el perfil.")

        st.markdown('<div class="pd-section-title">Evolución GPS Panorámica: Intensidad vs Aceleraciones</div>', unsafe_allow_html=True)
        
        # Orden Cronológico Fijo (Izquierda a Derecha)
        df_p_jug_chart = df_p_jug.sort_values('Fecha_dt', ascending=True)
        
        fig_gps_combined = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_gps_combined.add_trace(go.Bar(x=df_p_jug_chart['Fecha'], y=df_p_jug_chart['Dist_18'], name="Dist >18 km/h", marker_color=PRIMARY), secondary_y=False)
        fig_gps_combined.add_trace(go.Bar(x=df_p_jug_chart['Fecha'], y=df_p_jug_chart['Dist_25'], name="Sprint >25 km/h", marker_color=TEAM), secondary_y=False)
        
        fig_gps_combined.add_trace(go.Scatter(
            x=df_p_jug_chart['Fecha'], y=df_p_jug_chart['Acc_Dec'], mode="lines+markers+text", name="Nº Acel + Decel", 
            line=dict(color=GOOD, width=3), marker=dict(size=8),
            text=df_p_jug_chart['Label'], textposition='top center', textfont=dict(color=TEXT, size=11)
        ), secondary_y=True)

        max_dist = (df_p_jug_chart['Dist_18'] + df_p_jug_chart['Dist_25']).max()
        max_acc_dec = df_p_jug_chart['Acc_Dec'].max()

        fig_gps_combined.update_layout(
            barmode="stack", height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
            font=dict(color=TEXT), legend=dict(orientation="h", y=-0.2)
        )
        
        fig_gps_combined.update_yaxes(title_text="Distancia (m)", showgrid=True, gridcolor=BORDER, secondary_y=False, range=[0, max_dist * 1.25] if pd.notna(max_dist) else None)
        fig_gps_combined.update_yaxes(title_text="Nº Acel + Decel", showgrid=False, secondary_y=True, range=[0, max_acc_dec * 1.3] if pd.notna(max_acc_dec) else None)
        
        st.plotly_chart(fig_gps_combined, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="pd-section-title">Registro Detallado Sesión a Sesión</div>', unsafe_allow_html=True)
        cols_table = ['Fecha', 'Tipo_Sesion', 'RPE_Score', 'Rival', 'Localizacion', 'Minutos', 'Duracion', 'Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'N_Sprints', 'N_Acc', 'N_Dec', 'Acc_Dec', 'V_MAX', 'AC_MAX', 'DEC_MAX', 'Player_Load']
        cols_present = [c for c in cols_table if c in df_p_jug.columns]
        
        df_display = df_p_jug_chart[cols_present].copy()
        if 'Fecha_dt' in df_p_jug_chart.columns:
            df_display['Fecha_dt'] = df_p_jug_chart['Fecha_dt']
            df_display = df_display.sort_values('Fecha_dt', ascending=False).drop(columns=['Fecha_dt'])
            
        format_dict = {}
        for col in ['Duracion', 'Dist_Total', 'Dist_18', 'Dist_25', 'Dist_28', 'N_Sprints', 'N_Acc', 'N_Dec', 'Acc_Dec', 'Player_Load']:
            if col in df_display.columns: format_dict[col] = "{:.0f}"
        for col in ['V_MAX', 'AC_MAX', 'DEC_MAX']:
            if col in df_display.columns: format_dict[col] = "{:.2f}"
            
        st.dataframe(df_display.style.format(format_dict), use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos GPS disponibles para este jugador.")