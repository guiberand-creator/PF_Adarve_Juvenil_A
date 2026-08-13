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
# 1. CONFIGURACIÓN Y ESTILOS CSS GLASSMORPHISM (HUD STYLE)
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

# CSS ESTILO HUD FUTURISTA / GLASSMORPHISM
st.markdown("""
    <style>
    /* Estilos Glassmorphism principales */
    .hud-card {
        background: rgba(15, 23, 42, 0.75) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    }
    
    .hud-header-title {
        font-size: 32px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        margin: 0 0 2px 0 !important;
    }
    .hud-header-sub {
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #00E5FF !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        margin-bottom: 12px !important;
    }

    /* Mosaico KPI Cards */
    .kpi-tile {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 10px;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-label {
        font-size: 10px !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 22px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
    }
    .kpi-value-cyan { color: #00E5FF !important; }
    .kpi-value-gold { color: #FFC107 !important; }
    .kpi-value-green { color: #00E676 !important; }

    .photo-scout {
        width: 175px;
        height: 175px;
        border-radius: 16px;
        object-fit: cover;
        display: block;
        margin: 0 auto;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
    }
    .photo-placeholder-scout {
        width: 175px;
        height: 175px;
        border-radius: 16px;
        background-color: #1E293B;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Badges para tabla */
    .badge-win { background-color: rgba(0,230,118,0.2); color: #00E676; padding: 3px 8px; border-radius: 6px; font-weight:bold; }
    .badge-draw { background-color: rgba(255,193,7,0.2); color: #FFC107; padding: 3px 8px; border-radius: 6px; font-weight:bold; }
    .badge-loss { background-color: rgba(255,46,147,0.2); color: #FF2E93; padding: 3px 8px; border-radius: 6px; font-weight:bold; }
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
    r_pos = os.path.join("data", "Posiciones.xlsx")
    df_pos = pd.read_excel(r_pos) if os.path.exists(r_pos) else pd.DataFrame()
    if not df_pos.empty:
        c_n = next((c for c in df_pos.columns if 'jugador' in str(c).lower() or 'nombre' in str(c).lower()), df_pos.columns[0])
        c_p = next((c for c in df_pos.columns if 'posic' in str(c).lower()), df_pos.columns[1])
        c_foto = next((c for c in df_pos.columns if 'foto' in str(c).lower() or 'url' in str(c).lower()), None)
        df_pos = df_pos.rename(columns={c_n: 'Nombre', c_p: 'Posicion'})
        if c_foto: df_pos = df_pos.rename(columns={c_foto: 'Foto_URL'})
        df_pos['Nombre_Norm'] = df_pos['Nombre'].apply(norm_nom)

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

    return df_pos, df_cuest, df_rpe, df_gps_all

df_pos, df_cuest, df_rpe, df_gps_all = cargar_todo_informes()

# =============================================================================
# 3. SELECCIÓN DE JUGADOR (PARA STAFF)
# =============================================================================
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

# =============================================================================
# 5. DASHBOARD PRO SCOUTING (PANEL HUD EN 3 COLUMNAS)
# =============================================================================

nombre_mostrar = jugador_sel.replace('_', ' ').upper()

c_left, c_center, c_right = st.columns([1.1, 1.4, 1.5], gap="medium")

# --- COLUMNA 1: VISUAL (ESCUDO -> FOTO -> TAG -> CAMPOGRAMA) ---
with c_left:
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    
    # Escudo arriba del todo
    st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="{url_escudo_oficial}" style="width:68px; height:auto;"></div>', unsafe_allow_html=True)

    # Foto
    if url_foto_jugador and pd.notna(url_foto_jugador):
        st.markdown(f'<div><img src="{url_foto_jugador}" class="photo-scout"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div><div class="photo-placeholder-scout"><span style="font-size:65px;">👤</span></div></div>', unsafe_allow_html=True)
    
    # Tag debajo de la foto
    st.markdown('<div style="text-align:center; font-size:11px; font-weight:800; color:#00E5FF; letter-spacing:1.5px; margin-top:8px; margin-bottom:12px;">JUVENIL DIVISIÓN DE HONOR</div>', unsafe_allow_html=True)
    
    # Campograma Vertical Proporcional
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
        dict(type="rect", x0=0, y0=0, x1=68, y1=105, line=dict(color="rgba(255,255,255,0.35)", width=1.5)),
        dict(type="line", x0=0, y0=52.5, x1=68, y1=52.5, line=dict(color="rgba(255,255,255,0.35)", width=1.5)),
        dict(type="circle", x0=24.85, y0=43.35, x1=43.15, y1=61.65, line=dict(color="rgba(255,255,255,0.35)", width=1.5)),
        dict(type="rect", x0=13.84, y0=0, x1=54.16, y1=16.5, line=dict(color="rgba(255,255,255,0.35)", width=1)),
        dict(type="rect", x0=13.84, y0=88.5, x1=54.16, y1=105, line=dict(color="rgba(255,255,255,0.35)", width=1))
    ]

    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=40, color='rgba(0, 229, 255, 0.25)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=24, color='rgba(0, 229, 255, 0.55)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=12, color='rgba(0, 229, 255, 0.95)'), showlegend=False))

    fig_pitch.update_layout(
        shapes=lineas_campo, template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(range=[-2, 70], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[-2, 107], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True, scaleanchor="x", scaleratio=1),
        height=210, margin=dict(l=2, r=2, t=2, b=2)
    )
    st.plotly_chart(fig_pitch, use_container_width=True, config={'staticPlot': True})
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMNA 2: RADAR DE RENDIMIENTO Y EMBLEMA CENTRAL ---
with c_center:
    st.markdown('<div class="hud-card" style="height:100%;">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:12px; font-weight:800; color:#94A3B8; letter-spacing:1px; margin-bottom:8px;">PERFIL TÁCTICO CONDICIONAL</div>', unsafe_allow_html=True)
    
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
        fill='toself', name=jugador_sel.replace('_', ' '),
        fillcolor='rgba(0, 229, 255, 0.35)',
        line=dict(color='#00E5FF', width=3, shape='spline'),
        marker=dict(size=6, color='#FFFFFF', line=dict(color='#00E5FF', width=2))
    ))

    fig_radar.update_layout(
        polar=dict(
            bgcolor='rgba(15, 23, 42, 0.5)',
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255,255,255,0.12)', tickfont=dict(size=9, color='#8E9BAE')),
            angularaxis=dict(gridcolor='rgba(255,255,255,0.12)', tickfont=dict(size=11, color='#FFFFFF', family="Arial Black"))
        ),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
        height=380, margin=dict(l=25, r=25, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMNA 3: FICHA TÉCNICA & MOSAICO DE KPI CARDS ---
with c_right:
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    
    # Nombre + Datos Básicos
    st.markdown(f'<div class="hud-header-title">{nombre_mostrar}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hud-header-sub">ADARVE DH | {posicion_str.upper()}</div>', unsafe_allow_html=True)
    
    # Ficha rapida
    st.markdown(f"""
        <div style="display:flex; justify-content:space-between; margin-bottom:15px; background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px;">
            <span style="font-size:12px; color:#94A3B8;"><b>NACIMIENTO:</b> {fecha_nac_str}</span>
            <span style="font-size:12px; color:#94A3B8;"><b>PIERNA:</b> {pierna_str.upper()}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # MOSAICO KPI CARDS (2 FILAS x 3 COLUMNAS)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">MINUTOS LIGA</div>
                <div class="kpi-value kpi-value-gold">{minutos_oficiales}′</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">RPE MEDIO</div>
                <div class="kpi-value kpi-value-cyan">{rpe_medio:.1f}</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">PUESTO RANKING</div>
                <div class="kpi-value kpi-value-green">#4</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    k4, k5, k6 = st.columns(3)
    with k4:
        vmax_pico = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm]['V_MAX'].max() if not df_gps_all.empty else 32.4
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">V_MAX PICO</div>
                <div class="kpi-value">{vmax_pico:.1f} <span style="font-size:12px;">km/h</span></div>
            </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">SALTO CMJ</div>
                <div class="kpi-value">38.5 <span style="font-size:12px;">cm</span></div>
            </div>
        """, unsafe_allow_html=True)
    with k6:
        st.markdown(f"""
            <div class="kpi-tile">
                <div class="kpi-label">INDICE DRI</div>
                <div class="kpi-value">2.15</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# 6. ZONA INFERIOR: REGISTRO DE PARTIDOS + LÍNEA DE TENDENCIA TEMPORAL
# =============================================================================
st.markdown("<br>", unsafe_allow_html=True)

c_bot_left, c_bot_right = st.columns([1.8, 1.2], gap="medium")

with c_bot_left:
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:14px; font-weight:800; color:#FFFFFF; letter-spacing:1px; margin-bottom:10px;">⚽ REGISTRO DE PARTIDOS & GPS HISTÓRICO</div>', unsafe_allow_html=True)
    
    df_p_jug = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt', ascending=False) if not df_gps_all.empty else pd.DataFrame()
    
    if df_p_jug.empty:
        # Tabla de ejemplo vistosa
        df_demo_matches = pd.DataFrame({
            'Fecha': ['15/11/2026', '08/11/2026', '01/11/2026', '25/10/2026'],
            'Rival': ['Rayo Majadahonda', 'Real Madrid DH', 'Atletico Madrileño', 'Getafe CF'],
            'Res.': ['V 2-1', 'D 0-2', 'E 1-1', 'V 3-0'],
            'Minutos': [90, 75, 90, 85],
            'Dist Total (m)': [10450, 8920, 10120, 9800],
            'Dist >18 (m)': [850, 620, 790, 810],
            'V_MAX (km/h)': [31.8, 29.5, 30.2, 32.1]
        })
        st.dataframe(df_demo_matches, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_p_jug[['Fecha', 'Dist_Total', 'Dist_18', 'Dist_25', 'Acc_Dec', 'V_MAX', 'AC_MAX', 'DEC_MAX']], use_container_width=True, hide_index=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with c_bot_right:
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:14px; font-weight:800; color:#FFFFFF; letter-spacing:1px; margin-bottom:5px;">📈 RENDIMIENTO TEMPORAL</div>', unsafe_allow_html=True)
    st.caption("Evolución de Carga e Intensidad (Distancia Total vs Alta Velocidad)")
    
    # Gráfica de líneas multinivel estilo HUD
    fechas_line = ['Part 1', 'Part 2', 'Part 3', 'Part 4', 'Part 5']
    dist_total_norm = [80, 65, 90, 85, 95]
    dist_18_norm = [60, 45, 80, 75, 88]
    acc_dec_norm = [70, 55, 85, 80, 90]

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=fechas_line, y=dist_total_norm, mode='lines+markers', name='Dist Total', line=dict(color='#00E5FF', width=2.5, shape='spline')))
    fig_line.add_trace(go.Scatter(x=fechas_line, y=dist_18_norm, mode='lines+markers', name='Dist >18 km/h', line=dict(color='#FF2E93', width=2.5, shape='spline')))
    fig_line.add_trace(go.Scatter(x=fechas_line, y=acc_dec_norm, mode='lines+markers', name='Acc+Dec', line=dict(color='#00E676', width=2, dash='dot', shape='spline')))

    fig_line.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.5)',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.08)', range=[0, 110]),
        height=240, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)