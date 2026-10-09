import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os
from utils import aplicar_estilos_globales, aplicar_diseno_responsive

# Al principio de la página
aplicar_diseno_responsive()

# -----------------------------------------------------------------------------
# SELLO FIJO AL PIE DEL SIDEBAR (+30% TAMAÑO)
# -----------------------------------------------------------------------------
_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        import base64
        _b64 = base64.b64encode(_f.read()).decode()
        
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{
            position: fixed;
            bottom: 20px;
            left: 10px;
            width: 260px;
            text-align: center;
            z-index: 999;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
        }}
        .footer-sello-unico img {{
            width: 195px;
            height: auto;
            margin-bottom: 8px;
        }}
        .footer-sello-unico p {{
            font-size: 11px !important;
            color: #CCCCCC !important;
            margin: 2px 0 0 0 !important;
            letter-spacing: 0.5px;
        }}
        </style>

        <div class="footer-sello-unico">
            <img src="data:image/png;base64,{_b64}">
            <p>© 2026 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 1. SEGURIDAD: CONTROL DE ACCESO (LOGIN)
# ==========================================
if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
    st.stop()

# ==========================================
# 2. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Wellness y Recuperación - Unión Adarve", layout="wide")
aplicar_estilos_globales()

# ==========================================
# 3. HELPER: NORMALIZACIÓN DE TEXTO PARA CRUCE SEGURO
# ==========================================
def normalizar_texto(text):
    if pd.isna(text):
        return ""
    return (str(text).strip().lower()
            .replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            .replace('ü', 'u').replace('ñ', 'n'))

# ==========================================
# 4. EXTRACCIÓN Y LIMPIEZA DE DATOS (WELLNESS)
# ==========================================
@st.cache_data(ttl=10)
def cargar_datos_wellness():
    sheet_id = "12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o"
    gid = "1891505901"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip().str.upper()
        df.columns = (df.columns
                           .str.replace('É', 'E').str.replace('Ú', 'U')
                           .str.replace('Á', 'A').str.replace('Í', 'I').str.replace('Ó', 'O'))
        
        df['FECHA_REAL'] = pd.to_datetime(df['MARCA TEMPORAL'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['FECHA_REAL'])
        df['FECHA_DIA'] = df['FECHA_REAL'].dt.date
        df['JUGADOR'] = df['NOMBRE Y APELLIDOS'].fillna('Anónimo').astype(str).str.strip()
        df['JUGADOR_NORM'] = df['JUGADOR'].apply(normalizar_texto)
        
        col_sueno = [c for c in df.columns if c.startswith('SUE')][0]
        col_dolor = [c for c in df.columns if c.startswith('DOLOR')][0]
        col_estres = [c for c in df.columns if c.startswith('ESTRES')][0]
        col_carga = [c for c in df.columns if c.startswith('CARGA')][0]
        col_entrenar = [c for c in df.columns if 'ENTRENAR' in c][0]
        
        col_zona_lista = [c for c in df.columns if 'MUSCULATURA' in c or 'CARGADA' in c]
        col_zona = col_zona_lista[0] if col_zona_lista else None
        
        col_det_lista = [c for c in df.columns if 'ESPECIFICA' in c or 'SIENTES' in c or 'DIFERENTE' in c]
        col_det = col_det_lista[0] if col_det_lista else None
        
        df['SUEÑO'] = pd.to_numeric(df[col_sueno], errors='coerce').fillna(0)
        df['DOLOR'] = pd.to_numeric(df[col_dolor], errors='coerce').fillna(0)
        df['ESTRÉS'] = pd.to_numeric(df[col_estres], errors='coerce').fillna(0)
        df['CARGA'] = pd.to_numeric(df[col_carga], errors='coerce').fillna(0)
        df['DISPONIBLE'] = df[col_entrenar].astype(str).str.strip().str.lower()
        
        df['ZONA_DOLOR'] = df[col_zona].fillna('Ninguna').astype(str).str.strip() if col_zona else 'Ninguna'
        df['DETALLE_DOLOR'] = df[col_det].fillna('-').astype(str).str.strip() if col_det else '-'
        
        df['ZONA_DOLOR'] = df['ZONA_DOLOR'].apply(lambda x: 'Ninguna' if x.lower() in ['', 'nan', 'none', '-'] else x)
        df['DETALLE_DOLOR'] = df['DETALLE_DOLOR'].apply(lambda x: '-' if x.lower() in ['', 'nan', 'none', '-'] else x)
        
        df['WELLNESS_TOTAL'] = (df['SUEÑO'] + df['DOLOR'] + df['ESTRÉS'] + df['CARGA']) / 4
        
        return df, None
    except Exception as e:
        return None, str(e)

# ==========================================
# 5. EXTRACCIÓN Y CÁLCULO FÍSICO DEL TEST DE SALTO (DROP JUMP DRI)
# ==========================================
@st.cache_data(ttl=10)
def cargar_datos_saltos():
    sheet_id_saltos = "1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y"
    gid_saltos = "0"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id_saltos}/export?format=csv&gid={gid_saltos}"
    
    try:
        df_jumps_raw = pd.read_csv(url_csv)
        df_jumps_raw.columns = df_jumps_raw.columns.str.strip()
        
        col_jugador = 'Nombre de atleta'
        col_tc = 'TC'
        col_altura = 'Altura'
        col_fecha = 'Fecha y hora'
        
        df_jumps_raw['JUGADOR'] = df_jumps_raw[col_jugador].fillna('Anónimo').astype(str).str.strip()
        df_jumps_raw['JUGADOR_NORM'] = df_jumps_raw['JUGADOR'].apply(normalizar_texto)
        
        df_jumps_raw['FECHA_STR'] = df_jumps_raw[col_fecha].astype(str).str.split('_').str[0]
        df_jumps_raw['FECHA_REAL'] = pd.to_datetime(df_jumps_raw['FECHA_STR'], format='%Y-%m-%d', errors='coerce')
        df_jumps_raw = df_jumps_raw.dropna(subset=['FECHA_REAL'])
        df_jumps_raw['FECHA_DIA'] = df_jumps_raw['FECHA_REAL'].dt.date
        
        df_jumps_raw['TC_SEG'] = df_jumps_raw[col_tc].astype(str).str.replace(',', '.').pipe(pd.to_numeric, errors='coerce').fillna(0.0)
        df_jumps_raw['ALTURA_CM'] = df_jumps_raw[col_altura].astype(str).str.replace(',', '.').pipe(pd.to_numeric, errors='coerce').fillna(0.0)
        
        df_jumps_raw['ALTURA_M'] = df_jumps_raw['ALTURA_CM'] / 100.0
        altura_cajon_m = 0.50
        
        df_jumps_raw['DRI_INTENTO'] = np.where(
            df_jumps_raw['TC_SEG'] > 0,
            (altura_cajon_m + df_jumps_raw['ALTURA_M']) / (9.81 * (df_jumps_raw['TC_SEG'] ** 2)),
            0.0
        )
        
        df_grouped = df_jumps_raw.groupby(['JUGADOR_NORM', 'FECHA_DIA']).agg(
            DRI_MEDIO=('DRI_INTENTO', 'mean'),
            DRI_STD_INTENTOS=('DRI_INTENTO', 'std'),
            ALTURA_MEDIA_CM=('ALTURA_CM', 'mean'),
            TC_MEDIO_S=('TC_SEG', 'mean'),
            INTENTOS=('DRI_INTENTO', 'count')
        ).reset_index()
        
        df_grouped['DRI_STD_INTENTOS'] = df_grouped['DRI_STD_INTENTOS'].fillna(0.0)
        
        return df_grouped, None
    except Exception as e:
        return None, str(e)

# ==========================================
# 6. CABECERA HOMOGÉNEA
# ==========================================
st.title("CONTROL DE WELLNESS Y RECUPERACIÓN")
st.caption("Wellness (media móvil 15 sem) y recuperación SNC (Media móvil DRI 4 sem)")
st.markdown("---")

df_well, error_w = cargar_datos_wellness()
df_saltos, error_s = cargar_datos_saltos()

if error_w or error_s:
    if error_w: st.error(f"Error al conectar con la base de datos de Wellness: {error_w}")
    if error_s: st.error(f"Error al conectar con la base de datos de Saltos Chronojump: {error_s}")
else:
    fechas_disponibles = sorted(df_well['FECHA_DIA'].unique(), reverse=True)
    
    col_top1, col_top2 = st.columns([1, 3])
    with col_top1:
        fecha_seleccionada = st.selectbox("📅 Seleccionar Fecha de Análisis", fechas_disponibles)
        
    # ==========================================
    # 7. CÁLCULO DE VENTANAS MÓVILES ADAPTATIVAS (Z-SCORES)
    # ==========================================
    df_well_ord = df_well.sort_values(by=['JUGADOR_NORM', 'FECHA_REAL']).copy()
    df_well_ord['WELL_MEDIA_15'] = df_well_ord.groupby('JUGADOR_NORM')['WELLNESS_TOTAL'].transform(
        lambda x: x.rolling(window=15, min_periods=1).mean()
    )
    df_well_ord['WELL_STD_15'] = df_well_ord.groupby('JUGADOR_NORM')['WELLNESS_TOTAL'].transform(
        lambda x: x.rolling(window=15, min_periods=1).std()
    ).fillna(0)
    df_well_ord['Z_SCORE_WELLNESS'] = np.where(
        df_well_ord['WELL_STD_15'] > 0,
        (df_well_ord['WELLNESS_TOTAL'] - df_well_ord['WELL_MEDIA_15']) / df_well_ord['WELL_STD_15'],
        df_well_ord['WELLNESS_TOTAL'] - df_well_ord['WELL_MEDIA_15']
    )
    
    df_saltos_ord = df_saltos.sort_values(by=['JUGADOR_NORM', 'FECHA_DIA']).copy()
    df_saltos_ord['DRI_MEDIA_4'] = df_saltos_ord.groupby('JUGADOR_NORM')['DRI_MEDIO'].transform(
        lambda x: x.rolling(window=4, min_periods=1).mean()
    )
    df_saltos_ord['DRI_STD_4'] = df_saltos_ord.groupby('JUGADOR_NORM')['DRI_MEDIO'].transform(
        lambda x: x.rolling(window=4, min_periods=1).std()
    ).fillna(0)
    df_saltos_ord['Z_SCORE_SALTO'] = np.where(
        df_saltos_ord['DRI_STD_4'] > 0,
        (df_saltos_ord['DRI_MEDIO'] - df_saltos_ord['DRI_MEDIA_4']) / df_saltos_ord['DRI_STD_4'],
        df_saltos_ord['DRI_MEDIO'] - df_saltos_ord['DRI_MEDIA_4']
    )
    
    df_well_hoy = df_well_ord[df_well_ord['FECHA_DIA'] == fecha_seleccionada].copy()
    df_saltos_hoy = df_saltos_ord[df_saltos_ord['FECHA_DIA'] == fecha_seleccionada].copy()
    
    df_cruzado = pd.merge(
        df_well_hoy, 
        df_saltos_hoy[['JUGADOR_NORM', 'DRI_MEDIO', 'DRI_MEDIA_4', 'DRI_STD_INTENTOS', 'ALTURA_MEDIA_CM', 'TC_MEDIO_S', 'INTENTOS', 'Z_SCORE_SALTO']], 
        on='JUGADOR_NORM', 
        how='left'
    )
    
    df_cruzado = df_cruzado.sort_values(by='Z_SCORE_WELLNESS', ascending=True)
    tiene_saltos_hoy = not df_cruzado['Z_SCORE_SALTO'].isna().all()

    # ==========================================
    # 8. PANEL GRÁFICO DINÁMICO ADAPTATIVO
    # ==========================================
    if not df_cruzado.empty:
        # Generar anotaciones superiores con W: media en negrita y color condicional (Verde >= 3.0, Rojo < 3.0)
        anotaciones_media_wellness = []
        for _, r_ann in df_cruzado.iterrows():
            w_avg = r_ann['WELLNESS_TOTAL']
            z_val = r_ann['Z_SCORE_WELLNESS']
            color_w = "#2ECC71" if w_avg >= 3.0 else "#E74C3C"
            y_pos = max(z_val, 0)
            anotaciones_media_wellness.append(dict(
                x=r_ann['JUGADOR'],
                y=y_pos,
                text=f"<b>W: {w_avg:.1f}</b>",
                showarrow=False,
                font=dict(color=color_w, size=12),
                yanchor="bottom",
                yshift=12
            ))

        min_z_val = df_cruzado['Z_SCORE_WELLNESS'].min()
        max_z_val = df_