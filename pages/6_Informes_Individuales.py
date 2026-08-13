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
    
    /* TARJETAS COMPACTAS EN GRID 2x2 */
    .kpi-tile-compact {
        background: rgba(30, 41, 59, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 16px 10px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        margin-bottom: 12px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .kpi-label-compact {
        font-size: 10px !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        margin-bottom: 4px;
    }
    .kpi-value-compact {
        font-size: 20px !important;
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

    # C) RPE (Minutos Jugados Oficiales desde 06/09/2026)
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

    # D) GPS
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
nombre_mostrar = jugador_sel.replace('_', ' ').upper()

# =============================================================================
# 5. DISPOSICIÓN SUPERIOR (50% ENCABEZADO AGRUPADO / 50% RADAR GIGANTE)
# =============================================================================

col_izq_top, col_der_top = st.columns([1.1, 0.9], gap="large")

# --- MITAD IZQUIERDA: ENCABEZADO AGRUPADO COMPACTO ---
with col_izq_top:
    col_foto, col_vis, col_kpis = st.columns([1.0, 1.0, 1.2], gap="small")

    # 1. Foto (Extremo Izquierdo)
    with col_foto:
        if url_foto_jugador and pd.notna(url_foto_jugador):
            st.markdown(f'<img src="{url_foto_jugador}" class="photo-full-body">', unsafe_allow_html=True)
        else:
            st.markdown('<div class="photo-placeholder-full"><span style="font-size:65px; color:#64748B;">👤</span></div>', unsafe_allow_html=True)

    # 2. Escudo + Tag + Campograma
    with col_vis:
        st.markdown(f'<div style="text-align:center; margin-bottom:2px;"><img src="{url_escudo_oficial}" style="width:55px; height:auto;"></div>', unsafe_allow_html=True)
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
            height=300, margin=dict(l=2, r=2, t=2, b=2)
        )
        st.plotly_chart(fig_pitch, use_container_width=True, config={'staticPlot': True})

    # 3. Mosaico Compacto de Tarjetas KPI en Grid 2x2
    with col_kpis:
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        
        # Fila 1
        k_r1_1, k_r1_2 = st.columns(2, gap="small")
        with k_r1_1:
            st.markdown(f"""
                <div class="kpi-tile-compact">
                    <div class="kpi-label-compact">📅 NACIMIENTO</div>
                    <div class="kpi-value-compact">{fecha_nac_str}</div>
                </div>
            """, unsafe_allow_html=True)
            
        with k_r1_2:
            st.markdown(f"""
                <div class="kpi-tile-compact">
                    <div class="kpi-label-compact">🦶 PIERNA HÁBIL</div>
                    <div class="kpi-value-compact kpi-value-cyan">{pierna_str.upper()}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        # Fila 2
        k_r2_1, k_r2_2 = st.columns(2, gap="small")
        with k_r2_1:
            st.markdown(f"""
                <div class="kpi-tile-compact">
                    <div class="kpi-label-compact">⏱️ MINUTOS LIGA</div>
                    <div class="kpi-value-compact kpi-value-gold">{minutos_oficiales}′</div>
                </div>
            """, unsafe_allow_html=True)

        with k_r2_2:
            st.markdown(f"""
                <div class="kpi-tile-compact">
                    <div class="kpi-label-compact">🏆 RANKING</div>
                    <div class="kpi-value-compact kpi-value-green">#4</div>
                </div>
            """, unsafe_allow_html=True)

# --- MITAD DERECHA: RADAR GIGANTE + CONTROLES ABAJO ---
with col_der_top:
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:13px; font-weight:800; color:#94A3B8; letter-spacing:1px; margin-bottom:4px;">PERFIL TÁCTICO CONDICIONAL</div>', unsafe_allow_html=True)
    
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
        height=380, margin=dict(l=25, r=25, t=15, b=15),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # Controles en 2 columnas ajustadas justo debajo del radar
    c_ctrl1, c_ctrl2 = st.columns(2, gap="small")
    with c_ctrl1:
        modo_analisis = st.radio("📊 Módulo:", ["Pruebas Físicas", "Rendimiento en Campo"], horizontal=True)
    with c_ctrl2:
        filtro_comparacion = st.selectbox("⚖️ Comparar Percentil vs:", ["Toda la Plantilla", "Misma Demarcación"])
        
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# 6. TABLAS DE DATOS Y DISPERSIÓN
# =============================================================================
st.markdown("---")

if modo_analisis == "Pruebas Físicas":
    st.markdown("### 📋 Histórico de Resultados en Evaluaciones Condicionales")
    st.info("💡 Haz clic en cualquier columna para ordenar las sesiones del jugador.")
    
    df_hist_eval = pd.DataFrame({
        'Fecha': ['13/08/2026', '01/06/2026'],
        'Test': ['Batería Completa Inicio', 'Pretemporada'],
        'CMJ (cm)': [38.5, 36.2],
        'DRI': [2.15, 1.98],
        'VAM (km/h)': [15.2, 14.8],
        'Dinamometría (N/kg)': [5.8, 5.4],
        'Press Banca (reps)': [18, 15],
        'Dominadas (reps)': [12, 10]
    })
    st.dataframe(df_hist_eval, use_container_width=True, hide_index=True)

else:
    st.markdown("### ⚽ Registro GPS Partido a Partido")
    
    df_p_jug = df_gps_all[df_gps_all['Nombre_Norm'] == jug_norm].sort_values('Fecha_dt', ascending=False) if not df_gps_all.empty else pd.DataFrame()
    
    if df_p_jug.empty:
        st.info("No hay registros GPS disponibles para este jugador.")
    else:
        st.dataframe(df_p_jug[['Fecha', 'Dist_Total', 'Dist_18', 'Dist_25', 'Acc_Dec', 'V_MAX', 'AC_MAX', 'DEC_MAX']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 📈 Dispersión: Volumen (Dist. Total) vs Alta Intensidad (>18 km/h)")
        
        fig_sc = px.scatter(
            df_p_jug, x="Dist_Total", y="Dist_18", size="Dist_25",
            hover_data=["Fecha"], labels={"Dist_Total": "Distancia Total (m)", "Dist_18": "Distancia >18 km/h (m)"},
            title=f"Evolución Intensidad vs Volumen - {jugador_sel}", template="plotly_dark"
        )
        fig_sc.update_traces(marker=dict(color='#00A8E8', line=dict(width=1, color='White')))
        fig_sc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', height=400)
        st.plotly_chart(fig_sc, use_container_width=True)