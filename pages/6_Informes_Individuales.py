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
# 1. CONFIGURACIÓN DE PÁGINA Y TEMAS V0 (FULL WIDTH SHADCN THEME)
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
PLOT_FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

def inject_v0_css():
    st.markdown(f"""
        <style>
        .stApp {{ background: {BG}; }}
        
        /* 100% ANCHO REAL DE PANTALLA */
        .block-container {{ 
            padding-top: 1.5rem !important; 
            padding-bottom: 3rem !important; 
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important; 
        }}

        /* Card Primitive v0 */
        .pd-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
        }}

        /* Header Band v0 */
        .pd-hero {{
            background:
                radial-gradient(1200px 240px at 12% -40%, {PRIMARY_SOFT}, transparent 60%),
                linear-gradient(180deg, {SURFACE_2} 0%, {SURFACE} 100%);
            border: 1px solid {BORDER};
            border-radius: 18px;
            padding: 1.25rem 1.5rem;
            width: 100%;
        }}
        .pd-name {{ font-size: 2.2rem; font-weight: 800; line-height: 1.05; margin: 0; letter-spacing: -0.02em; color: {TEXT}; }}
        .pd-club {{ color: {MUTED}; font-size: 0.95rem; margin-top: 0.35rem; }}
        .pd-badge {{
            display: inline-flex; align-items: center; gap: 0.4rem;
            background: {PRIMARY_SOFT}; color: {PRIMARY};
            border: 1px solid rgba(225,29,72,0.35);
            padding: 0.2rem 0.7rem; border-radius: 999px;
            font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
        }}

        /* Fact Grid v0 (1 Fila x 4 columnas) */
        .pd-facts {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; margin-top: 1.2rem; }}
        .pd-fact {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 0.75rem 1rem; text-align: center; }}
        .pd-fact .k {{ color: {MUTED}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }}
        .pd-fact .v {{ font-size: 1.25rem; font-weight: 800; margin-top: 0.2rem; color: {TEXT}; }}
        .pd-fact .v-cyan {{ color: #38bdf8 !important; }}
        .pd-fact .v-gold {{ color: #f59e0b !important; }}
        .pd-fact .v-green {{ color: #22c55e !important; }}

        .photo-v0 {{
            max-height: 340px;
            width: auto;
            object-fit: contain;
            display: block;
            margin: 0 auto;
            filter: drop-shadow(0px 10px 20px rgba(225, 29, 72, 0.25));
        }}
        .photo-placeholder-v0 {{
            height: 320px;
            width: 100%;
            border-radius: 16px;
            background: radial-gradient(120% 120% at 30% 20%, {SURFACE_2}, {SURFACE});
            display: flex; align-items: center; justify-content: center;
            border: 1px solid {BORDER};
        }}

        .pd-section-title {{
            font-size: 0.85rem; font-weight: 800; text-transform: uppercase;
            letter-spacing: 0.1em; color: {MUTED}; margin: 0.25rem 0 0.75rem;
        }}

        /* Tabs v0 */
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
        .stTabs [data-baseweb="tab"] {{
            background: {SURFACE}; border: 1px solid {BORDER};
            border-radius: 10px 10px 0 0; padding: 0.6rem 1.4rem; font-weight: 700; color: {MUTED};
        }}
        .stTabs [aria-selected="true"] {{ background: {SURFACE_2}; color: {TEXT}; border-bottom: 2px solid {PRIMARY}; }}
        </style>
    """, unsafe_allow_html=True)

inject_v0_css()

def norm_nom(texto):
    if pd.isna(texto): return ""
    return " ".join(str(texto).replace('_', ' ').strip().lower().split())

# SELLO FIJO SIDEBAR
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

# =============================================================================
# 2. CARGA DE DATOS MULTIFUENTE CON CÁLCULO DE RANKING CONDICIONAL REAL
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
    # 0. Posiciones.xlsx
    r_pos = os.path.join("data", "Posiciones.xlsx")
    df_pos = pd.read_excel(r_pos) if os.path.exists(r_pos) else pd.DataFrame()
    if not df_pos.empty:
        c_n = next((c for c in df_pos.columns if 'jugador' in str(c).lower() or 'nombre' in str(c).lower()), df_pos.columns[0])
        c_p = next((c for c in df_pos.columns if 'posic' in str(c).lower()), df_pos.columns[1])
        c_foto = next((c for c in df_pos.columns if 'foto' in str(c).lower() or 'url' in str(c).lower()), None)
        
        # Identificar columna posterior a Posición (Lado / Perfil)
        cols_list = list(df_pos.columns)
        c_lado = next((c for c in df_pos.columns if any(k in str(c).lower() for k in ['lado', 'perfil', 'espec', 'sub', 'demarc']) and c not in [c_n, c_p, c_foto]), None)
        if not c_lado and len(cols_list) > 2:
            p_idx = cols_list.index(c_p)
            if p_idx + 1 < len(cols_list):
                cand = cols_list[p_idx + 1]
                if cand != c_foto: c_lado = cand

        renomb_dict = {c_n: 'Nombre', c_p: 'Posicion'}
        if c_foto: renomb_dict[c_foto] = 'Foto_URL'
        if c_lado: renomb_dict[c_lado] = 'Lado'

        df_pos = df_pos.rename(columns=renomb_dict)
        df_pos['Nombre_Norm'] = df_pos['Nombre'].apply(norm_nom)

    # 1. Cuestionario Inicial (Google Sheet)
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

    # 2. Peso
    r_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    df_peso = pd.read_excel(r_peso) if os.path.exists(r_peso) else pd.DataFrame()
    if not df_peso.empty:
        df_peso['Nombre_Norm'] = df_peso.iloc[:, 0].apply(norm_nom)
        df_peso['Fecha_dt'] = pd.to_datetime(df_peso.iloc[:, 1], dayfirst=True, errors='coerce')
        df_peso.rename(columns={df_peso.columns[2]: 'Peso'}, inplace=True)

    # 3. RPE
    df_rpe = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if not df_rpe.empty:
        cols = df_rpe.columns
        c_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        c_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        c_t = next((c for c in cols if 'tipo' in str(c).lower()), cols[2])
        c_m = next((c for c in cols if 'minuto' in str(c).lower()), cols[3])
        df_rpe['Fecha_dt'] = pd.to_datetime(df_rpe[c_f], dayfirst=True, errors='coerce')
        df_rpe['Fecha'] = df_rpe['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_rpe['Nombre'] = df_rpe[c_n].astype(str).str.strip()
        df_rpe['Nombre_Norm'] = df_rpe['Nombre'].apply(norm_nom)
        df_rpe['Tipo_Sesion'] = df_rpe[c_t].astype(str).str.strip()
        df_rpe['Minutos'] = pd.to_numeric(df_rpe[c_m], errors='coerce').fillna(0)

    # 4. GPS
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

    # 5. Evaluaciones Físicas
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
            if 'dinamometria' in arch.lower():
                archivo_encontrado = os.path.join(dir_dina, arch)
                break

    if archivo_encontrado:
        if archivo_encontrado.endswith('.xlsx') or archivo_encontrado.endswith('.xls'): df_dina = pd.read_excel(archivo_encontrado)
        else:
            try: df_dina = pd.read_csv(archivo_encontrado, sep=';', encoding='utf-8')
            except: df_dina = pd.read_csv(archivo_encontrado, sep=',', encoding='utf-8')
        if df_dina is not None and not df_dina.empty:
            df_dina.rename(columns={'Name': 'Nombre', 'Date': 'Fecha', 'Exercise': 'Exercise', 'MaxForce (raw)': 'Fmax_Abs'}, inplace=True)
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

    # CÁLCULO DE RANKING GLOBAL REAL
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
            df_m_last['Movilidad_Score'] = df_m_last[['DORSIFLEX_D', 'DORSIFLEX_I', 'ROT_INT_D', 'ROT_INT_I', 'FLEX_CAD_D', 'FLEX_CAD_I', 'LUMBAR']].mean(axis=1)
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
            df_cmj = df_saltos[df_saltos['Tipo'].str.upper() == 'CMJ'].copy()
            df_rank_base = merge_ult(df_rank_base, df_cmj, 'Altura', 'CMJ_Altura')

        df_rank_base = merge_ult(df_rank_base, df_dri, 'DRI', 'DRI')

        if df_fts is not None and not df_fts.empty:
            df_ts_l = df_fts.sort_values('Fecha_dt').copy()
            df_ts_l['Tren_Superior_Reps'] = df_ts_l['Press_Banca'].fillna(0) + df_ts_l['Dominada'].fillna(0)
            df_rank_base = merge_ult(df_rank_base, df_ts_l, 'Tren_Superior_Reps', 'Tren_Superior_Reps')

        if df_campo is not None and not df_campo.empty:
            df_rank_base = merge_ult(df_rank_base, df_campo, 'V_MAX', 'V_MAX')
            df_rank_base = merge_ult(df_rank_base, df_campo, 'AC_MAX', 'AC_MAX')

        columnas_pruebas = {
            'Movilidad_Score': True, 'VAM': True, 'Fmax_Rel': True,
            'CMJ_Altura': True, 'DRI': True, 'Tren_Superior_Reps': True,
            'V_MAX': True, 'AC_MAX': True
        }

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

    return df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo, dict_rankings_reales

df_pos, df_cuest, df_peso, df_rpe, df_gps_all, df_mov, df_vam, df_dina, df_saltos, df_dri, df_fts, df_campo, dict_rankings_reales = cargar_todo_informes()

# =============================================================================
# 3. SELECCIÓN DE JUGADOR Y MAPEO DE DATOS
# =============================================================================
lista_jugadores = sorted(df_pos['Nombre'].dropna().unique()) if not df_pos.empty else []
if not lista_jugadores and not df_cuest.empty:
    lista_jugadores = sorted(df_cuest['Nombre'].dropna().unique())

if not lista_jugadores:
    st.warning("⚠️ No se encontraron jugadores registrados en el sistema.")
    st.stop()

c_sel, _ = st.columns([2.5, 7.5])
with c_sel:
    jugador_sel = st.selectbox("⚽ Selecciona Jugador:", lista_jugadores)

jug_norm = norm_nom(jugador_sel)
match_pos = df_pos[df_pos['Nombre_Norm'] == jug_norm] if not df_pos.empty else pd.DataFrame()
match_cuest = df_cuest[df_cuest['Nombre_Norm'] == jug_norm] if not df_cuest.empty else pd.DataFrame()

url_foto_jugador = match_pos.iloc[0].get('Foto_URL', None) if not match_pos.empty and 'Foto_URL' in match_pos.columns else None

# Fecha de Nacimiento (Desde Cuestionario Inicial)
fecha_nac_str = "Por definir"
if not match_cuest.empty and 'Fecha_Nacimiento' in match_cuest.columns:
    val_fn = match_cuest.iloc[0]['Fecha_Nacimiento']
    if pd.notna(val_fn) and str(val_fn).strip() != "": fecha_nac_str = str(val_fn).strip()

# Posición y Lado
posicion_str = "Por definir"
if not match_cuest.empty and 'Posicion_Habitual' in match_cuest.columns:
    val_p = match_cuest.iloc[0]['Posicion_Habitual']
    if pd.notna(val_p) and str(val_p).strip() != "": posicion_str = str(val_p).strip()
elif not match_pos.empty:
    posicion_str = str(match_pos.iloc[0].get('Posicion', 'Por definir')).strip()

lado_str = ""
if not match_pos.empty and 'Lado' in match_pos.columns:
    val_l = match_pos.iloc[0]['Lado']
    if pd.notna(val_l) and str(val_l).strip().lower() not in ['nan', 'none', '']:
        lado_str = str(val_l).strip()

# Pierna Dominante (Desde Cuestionario Inicial)
pierna_str = "Por definir"
if not match_cuest.empty and 'Pierna_Dominante' in match_cuest.columns:
    val_pierna = match_cuest.iloc[0]['Pierna_Dominante']
    if pd.notna(val_pierna) and str(val_pierna).strip() != "": pierna_str = str(val_pierna).strip()

# Minutos en Liga Reales (Desde 06/09/2026)
minutos_oficiales = 0
if not df_rpe.empty:
    fecha_inicio_liga = pd.to_datetime("2026-09-06")
    df_m = df_rpe[(df_rpe['Nombre_Norm'] == jug_norm) & (df_rpe['Tipo_Sesion'].str.lower().str.contains('partido')) & (df_rpe['Fecha_dt'] >= fecha_inicio_liga)]
    minutos_oficiales = int(df_m['Minutos'].sum())

# Ranking Real
ranking_real_str = dict_rankings_reales.get(jug_norm, "#--")

# Récords
cmj_pico = df_saltos[(df_saltos['Nombre_Norm'] == jug_norm) & (df_saltos['Tipo'].str.upper() == 'CMJ')]['Altura'].max() if df_saltos is not None and not df_saltos.empty else 42.5
vmax_pico = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm]['V_MAX'].max() if df_gps_all is not None and not df_gps_all.empty else 31.8
dri_pico = df_dri[df_dri['Nombre_Norm'] == jug_norm]['DRI'].max() if df_dri is not None and not df_dri.empty else 2.15

url_escudo_oficial = "https://cdn.resfu.com/img_data/equipos/2585.png?size=120x&lossy=1"
nombre_mostrar = jugador_sel.replace('_', ' ').upper()

# =============================================================================
# 4. CAMPOGRAMA CON MAPEO SUB-POSICIONAL INTELIGENTE
# =============================================================================
def _campograma_v0(pos_str, pierna_s, lado_s="", nombre_mostrar="PLAYER"):
    fig = go.Figure()
    line = dict(color=BORDER, width=1.5)
    pitch = "#0f1c14"

    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, line=line, fillcolor=pitch, layer="below")
    fig.add_shape(type="line", x0=0, y0=50, x1=100, y1=50, line=line)
    fig.add_shape(type="circle", x0=38, y0=40, x1=62, y1=60, line=line)
    fig.add_shape(type="circle", x0=49, y0=49.2, x1=51, y1=50.8, line=dict(color=BORDER, width=1), fillcolor=BORDER)
    for y0, y1 in [(0, 16), (84, 100)]: fig.add_shape(type="rect", x0=22, y0=y0, x1=78, y1=y1, line=line)
    for y0, y1 in [(0, 6), (94, 100)]: fig.add_shape(type="rect", x0=37, y0=y0, x1=63, y1=y1, line=line)

    pos_low = (str(pos_str) + " " + str(lado_s)).lower()
    pierna_low = str(pierna_s).lower()

    es_izq = any(k in pos_low for k in ['izq', 'zurd', 'left']) or ('zurd' in pierna_low)
    es_der = any(k in pos_low for k in ['der', 'dext', 'right', 'diest']) or ('diest' in pierna_low or 'dext' in pierna_low)

    if 'porter' in pos_low or 'gk' in pos_low:
        px, py, code_text = 50, 8, "POR"
    elif 'central' in pos_low or 'cb' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 38, 22, "CI"
        elif 'der' in pos_low: px, py, code_text = 62, 22, "CD"
        else: px, py, code_text = 50, 22, "CEN"
    elif 'lateral' in pos_low or 'cad' in pos_low or 'carril' in pos_low:
        if 'izq' in pos_low or (es_izq and not 'der' in pos_low): px, py, code_text = 18, 28, "LI"
        else: px, py, code_text = 82, 28, "LD"
    elif 'medio' in pos_low or 'pivote' in pos_low or 'mediocentro' in pos_low or 'cm' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 35, 45, "MCI"
        elif 'der' in pos_low: px, py, code_text = 65, 45, "MCD"
        else: px, py, code_text = 50, 45, "MC"
    elif 'interior' in pos_low or 'mediapunta' in pos_low or 'cam' in pos_low:
        if 'izq' in pos_low: px, py, code_text = 32, 62, "INT"
        elif 'der' in pos_low: px, py, code_text = 68, 62, "INT"
        else: px, py, code_text = 50, 62, "MP"
    elif 'extremo' in pos_low or 'banda' in pos_low or 'wing' in pos_low:
        if 'izq' in pos_low or (es_izq and not 'der' in pos_low): px, py, code_text = 20, 78, "EI"
        else: px, py, code_text = 80, 78, "ED"
    elif 'delantero' in pos_low or 'punta' in pos_low or 'atacante' in pos_low or 'st' in pos_low:
        px, py, code_text = 50, 86, "DC"
    else:
        px, py, code_text = 50, 50, "JUG"

    fig.add_trace(go.Scatter(
        x=[px], y=[py], mode="markers+text", text=[f"<b>{code_text}</b>"],
        textposition="middle center", textfont=dict(color="#ffffff", size=10, family="sans-serif"),
        marker=dict(size=28, color=PRIMARY, line=dict(color="#ffffff", width=2)),
        hovertemplate=f"<b>{nombre_mostrar}</b><br>{pos_str} {lado_s}<extra></extra>",
        showlegend=False,
    ))

    fig.update_xaxes(visible=False, range=[-2, 102])
    fig.update_yaxes(visible=False, range=[-2, 102], scaleanchor="x", scaleratio=1.35)
    fig.update_layout(
        height=240, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# =============================================================================
# 5. HEADER ENCABEZADO ESTILO HERO CARD V0 (CON 4 CARDAS KPI Y ESCUDO OFICIAL)
# =============================================================================
col_photo, col_hero = st.columns([1.0, 3.6], gap="medium")

with col_photo:
    if url_foto_jugador and pd.notna(url_foto_jugador):
        st.markdown(f'<img src="{url_foto_jugador}" class="photo-v0">', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="photo-placeholder-v0"><span style="font-size:3.2rem; font-weight:900; color:{PRIMARY};">AD</span></div>', unsafe_allow_html=True)

with col_hero:
    pos_label_full = f"{posicion_str.upper()} {lado_str.upper()}".strip()
    
    facts_html = f"""
        <div class="pd-fact"><div class="k">Nacimiento</div><div class="v">{fecha_nac_str}</div></div>
        <div class="pd-fact"><div class="k">Pierna</div><div class="v v-cyan">{pierna_str.upper()}</div></div>
        <div class="pd-fact"><div class="k">Minutos Liga</div><div class="v v-gold">{minutos_oficiales}′</div></div>
        <div class="pd-fact"><div class="k">Ranking</div><div class="v v-green">{ranking_real_str}</div></div>
    """
    
    # Renderizamos Hero Box Unificado
    st.markdown('<div class="pd-hero">', unsafe_allow_html=True)
    c_info, c_pitch = st.columns([2.5, 1.1], gap="medium")
    
    with c_info:
        st.markdown(
            f"""
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span class="pd-badge">{pos_label_full}</span>
                  <img src="{url_escudo_oficial}" style="width:48px; height:auto;">
              </div>
              <h1 class="pd-name" style="margin-top:0.4rem;">{nombre_mostrar}</h1>
              <div class="pd-club">ADARVE JUVENIL DH &middot; Temporada 2026/27</div>
              <div class="pd-facts">{facts_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_pitch:
        st.plotly_chart(_campograma_v0(posicion_str, pierna_str, lado_str, nombre_mostrar), use_container_width=True, config={"displayModeBar": False})
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# 6. PESTAÑAS DE SUB-PÁGINAS ESTILO V0 (CONDITIONING TESTS / GPS DATA)
# =============================================================================
tab_tests, tab_gps = st.tabs(["  Conditioning Tests  ", "  GPS & Match Output  "])

# -----------------------------------------------------------------------------
# SUB-PAGE 1: CONDITIONING TESTS
# -----------------------------------------------------------------------------
with tab_tests:
    st.markdown('<div class="pd-section-title">Season summary &middot; KPI Progresión</div>', unsafe_allow_html=True)
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Salto CMJ", f"{cmj_pico:.1f} cm", "▲ 3.2 cm", delta_color="normal")
    k2.metric("VAM Aeróbico", "15.8 km/h", "▲ 0.6 km/h", delta_color="normal")
    k3.metric("Ext. Rodilla", "6.4 N/kg", "▲ 0.5 N/kg", delta_color="normal")
    k4.metric("Índice DRI", f"{dri_pico:.2f}", "▲ 0.18", delta_color="normal")
    k5.metric("Press Banca", "22 reps", "▲ 4 reps", delta_color="normal")
    k6.metric("V_MAX Campo", f"{vmax_pico:.1f} km/h", "▲ 1.2 km/h", delta_color="normal")

    st.divider()

    left_col, right_col = st.columns([1.3, 1], gap="large")

    with left_col:
        st.markdown('<div class="pd-section-title">Evolución de tests en el tiempo</div>', unsafe_allow_html=True)
        test_categoria = st.selectbox(
            "Selecciona Batería de Tests:",
            ["🩺 Movilidad", "🫁 VAM Aeróbico", "⚙️ Dinamometría", "🚀 Saltos & DRI", "🏋️ Tren Superior"],
            label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if test_categoria == "🩺 Movilidad":
            if df_mov is not None and not df_mov.empty:
                df_j_mov = df_mov[df_mov['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                if not df_j_mov.empty:
                    fechas_str = df_j_mov['Fecha'].tolist()
                    fig_mov_line = go.Figure()
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['DORSIFLEX_D'], mode='lines+markers', name='Dorsiflexión D', line=dict(color=PRIMARY, width=3, shape='spline')))
                    fig_mov_line.add_trace(go.Scatter(x=fechas_str, y=df_j_mov['DORSIFLEX_I'], mode='lines+markers', name='Dorsiflexión I', line=dict(color=TEAM, width=3, shape='spline')))
                    fig_mov_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=12, y1=12, line=dict(color=GOOD, width=2, dash="dash"))
                    fig_mov_line.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_mov_line, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos para este jugador.")

        elif test_categoria == "🫁 VAM Aeróbico":
            if df_vam is not None and not df_vam.empty:
                df_j_vam = df_vam[df_vam['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                if not df_j_vam.empty:
                    fechas_str = df_j_vam['Fecha'].tolist()
                    fig_vam_line = go.Figure()
                    fig_vam_line.add_trace(go.Scatter(x=fechas_str, y=df_j_vam['VAM'], mode='lines+markers', name='VAM (km/h)', line=dict(color=PRIMARY, width=3, shape='spline')))
                    fig_vam_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=15.5, y1=15.5, line=dict(color=GOOD, width=2, dash="dash"))
                    fig_vam_line.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_vam_line, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos para este jugador.")

        elif test_categoria == "⚙️ Dinamometría":
            if df_dina is not None and not df_dina.empty:
                df_j_dina = df_dina[df_dina['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                if not df_j_dina.empty:
                    piv_dina = df_j_dina.pivot_table(index=['Fecha', 'Fecha_dt'], columns='Exercise', values='Fmax_Abs', aggfunc='mean').reset_index().sort_values('Fecha_dt')
                    fechas_str = piv_dina['Fecha'].tolist()
                    fig_dina_line = go.Figure()
                    if 'Extension_rodilla_90_Derecha' in piv_dina.columns:
                        fig_dina_line.add_trace(go.Scatter(x=fechas_str, y=piv_dina['Extension_rodilla_90_Derecha']/70.0, mode='lines+markers', name='Ext. Rodilla D (N/kg)', line=dict(color=PRIMARY, width=3, shape='spline')))
                    if 'Extension_rodilla_90_Izquierda' in piv_dina.columns:
                        fig_dina_line.add_trace(go.Scatter(x=fechas_str, y=piv_dina['Extension_rodilla_90_Izquierda']/70.0, mode='lines+markers', name='Ext. Rodilla I (N/kg)', line=dict(color=TEAM, width=3, shape='spline')))
                    fig_dina_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=6.0, y1=6.0, line=dict(color=GOOD, width=2, dash="dash"))
                    fig_dina_line.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_dina_line, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos para este jugador.")

        elif test_categoria == "🚀 Saltos & DRI":
            if df_saltos is not None and not df_saltos.empty:
                df_j_s = df_saltos[df_saltos['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                if not df_j_s.empty:
                    piv_s = df_j_s.pivot_table(index=['Fecha', 'Fecha_dt'], columns='Tipo', values='Altura', aggfunc='mean').reset_index().sort_values('Fecha_dt')
                    fechas_str = piv_s['Fecha'].tolist()
                    fig_salto_line = go.Figure()
                    if 'CMJ' in piv_s.columns:
                        fig_salto_line.add_trace(go.Scatter(x=fechas_str, y=piv_s['CMJ'], mode='lines+markers', name='CMJ (cm)', line=dict(color=PRIMARY, width=3, shape='spline')))
                    fig_salto_line.add_shape(type="line", x0=-0.5, x1=len(fechas_str)-0.5, y0=38.0, y1=38.0, line=dict(color=GOOD, width=2, dash="dash"))
                    fig_salto_line.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_salto_line, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos para este jugador.")

        else:
            if df_fts is not None and not df_fts.empty:
                df_j_ts = df_fts[df_fts['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt')
                if not df_j_ts.empty:
                    fechas_str = df_j_ts['Fecha'].tolist()
                    fig_ts_line = go.Figure()
                    fig_ts_line.add_trace(go.Scatter(x=fechas_str, y=df_j_ts['Press_Banca'], mode='lines+markers', name='Press Banca (reps)', line=dict(color=PRIMARY, width=3, shape='spline')))
                    fig_ts_line.add_trace(go.Scatter(x=fechas_str, y=df_j_ts['Dominada'], mode='lines+markers', name='Dominadas (reps)', line=dict(color=TEAM, width=3, shape='spline')))
                    fig_ts_line.update_layout(height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT))
                    st.plotly_chart(fig_ts_line, use_container_width=True, config={"displayModeBar": False})
                else: st.info("No hay datos para este jugador.")

    with right_col:
        st.markdown('<div class="pd-section-title">Perfil v0 &middot; Jugador vs Media Demarcación</div>', unsafe_allow_html=True)
        categories = ['Movilidad', 'VAM', 'Dinamometría', 'CMJ', 'DRI', 'Tren Sup.']
        values_jugador = [78, 85, 62, 92, 70, 75]
        values_media_pos = [65, 70, 60, 72, 65, 68]
        
        categories_closed = categories + [categories[0]]
        values_jug_closed = values_jugador + [values_jugador[0]]
        values_med_closed = values_media_pos + [values_media_pos[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=values_med_closed, theta=categories_closed, fill="toself", name="Media Demarcación", line=dict(color=TEAM, width=2), fillcolor="rgba(56,189,248,0.15)"))
        fig_radar.add_trace(go.Scatterpolar(r=values_jug_closed, theta=categories_closed, fill="toself", name=nombre_mostrar, line=dict(color=PRIMARY, width=3), fillcolor="rgba(225,29,72,0.30)"))
        
        fig_radar.update_layout(
            height=420, margin=dict(l=50, r=50, t=30, b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            polar=dict(bgcolor=SURFACE_2, radialaxis=dict(range=[0, 100], gridcolor=BORDER, tickfont=dict(color=MUTED, size=10)), angularaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT, size=11))),
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

# -----------------------------------------------------------------------------
# SUB-PAGE 2: GPS DATA
# -----------------------------------------------------------------------------
with tab_gps:
    st.markdown('<div class="pd-section-title">Season Totals &middot; GPS Output</div>', unsafe_allow_html=True)
    
    df_p_jug = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt', ascending=False) if not df_gps_all.empty else pd.DataFrame()
    
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Sesiones GPS", f"{len(df_p_jug)}")
    g2.metric("Distancia Total", f"{df_p_jug['Dist_Total'].sum()/1000:.1f} km" if not df_p_jug.empty else "0.0 km")
    g3.metric("Velocidad Máxima", f"{df_p_jug['V_MAX'].max():.1f} km/h" if not df_p_jug.empty else "0.0 km/h")
    g4.metric("Media Dist/Partido", f"{df_p_jug['Dist_Total'].mean():.0f} m" if not df_p_jug.empty else "0 m")
    g5.metric("Acc + Dec Totales", f"{df_p_jug['Acc_Dec'].sum():.0f}" if not df_p_jug.empty else "0")

    st.divider()

    if df_p_jug.empty:
        st.info("No hay registros GPS de partidos para este jugador.")
    else:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="pd-section-title">Desglose de Alta Intensidad (>18 km/h)</div>', unsafe_allow_html=True)
            fig_gps_bar = go.Figure()
            fig_gps_bar.add_trace(go.Bar(x=df_p_jug['Fecha'], y=df_p_jug['Dist_18'], name="Dist >18 km/h", marker_color=PRIMARY))
            fig_gps_bar.add_trace(go.Bar(x=df_p_jug['Fecha'], y=df_p_jug['Dist_25'], name="Sprint >25 km/h", marker_color=TEAM))
            fig_gps_bar.update_layout(barmode="stack", height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT))
            st.plotly_chart(fig_gps_bar, use_container_width=True, config={"displayModeBar": False})

        with c2:
            st.markdown('<div class="pd-section-title">Aceleraciones vs Desaceleraciones</div>', unsafe_allow_html=True)
            fig_acc = go.Figure()
            fig_acc.add_trace(go.Scatter(x=df_p_jug['Fecha'], y=df_p_jug['AC_MAX'], mode="lines+markers", name="AC_MAX", line=dict(color=TEAM, width=2.5)))
            fig_acc.add_trace(go.Scatter(x=df_p_jug['Fecha'], y=df_p_jug['DEC_MAX'], mode="lines+markers", name="DEC_MAX", line=dict(color=PRIMARY, width=2.5)))
            fig_acc.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT))
            st.plotly_chart(fig_acc, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="pd-section-title">Registro Detallado Partido a Partido</div>', unsafe_allow_html=True)
        st.dataframe(df_p_jug[['Fecha', 'Dist_Total', 'Dist_18', 'Dist_25', 'Acc_Dec', 'V_MAX', 'AC_MAX', 'DEC_MAX']], use_container_width=True, hide_index=True)