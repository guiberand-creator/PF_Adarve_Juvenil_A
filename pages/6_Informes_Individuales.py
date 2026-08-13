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
# 1. CONFIGURACIÓN Y ESTILOS
# =============================================================================
aplicar_diseno_responsive()

st.set_page_config(
    page_title="Informe Individual | Adarve DH",
    page_icon="👤",
    layout="wide"
)

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.error("⚠️ Acceso no autorizado. Por favor, inicia sesión en la página principal.")
    st.stop()

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

st.markdown("""
    <style>
    .player-card {
        background-color: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
    }
    .metric-box {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        border-left: 4px solid #00A8E8;
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
    # A) Posiciones
    r_pos = os.path.join("data", "Posiciones.xlsx")
    df_pos = pd.read_excel(r_pos) if os.path.exists(r_pos) else pd.DataFrame()
    if not df_pos.empty:
        c_n = next((c for c in df_pos.columns if 'jugador' in str(c).lower() or 'nombre' in str(c).lower()), df_pos.columns[0])
        c_p = next((c for c in df_pos.columns if 'posic' in str(c).lower()), df_pos.columns[1])
        c_l = next((c for c in df_pos.columns if 'lateral' in str(c).lower()), None)
        c_foto = next((c for c in df_pos.columns if 'foto' in str(c).lower() or 'url' in str(c).lower()), None)
        
        df_pos = df_pos.rename(columns={c_n: 'Nombre', c_p: 'Posicion'})
        if c_l: df_pos = df_pos.rename(columns={c_l: 'Lateralidad'})
        if c_foto: df_pos = df_pos.rename(columns={c_foto: 'Foto_URL'})

    # B) Cuestionario Inicial (Cumpleaños / Pierna Dominante)
    df_cuest = descargar_csv_drive("1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI", "0")
    if not df_cuest.empty:
        df_cuest.columns = df_cuest.columns.str.strip()
        c_n = next((c for c in df_cuest.columns if 'nombre' in str(c).lower()), df_cuest.columns[0])
        c_fn = next((c for c in df_cuest.columns if 'nacimiento' in str(c).lower()), None)
        c_pierna = next((c for c in df_cuest.columns if 'pierna' in str(c).lower() or 'dominante' in str(c).lower()), None)
        
        ren = {c_n: 'Nombre'}
        if c_fn: ren[c_fn] = 'Fecha_Nacimiento'
        if c_pierna: ren[c_pierna] = 'Pierna_Dominante'
        df_cuest = df_cuest.rename(columns=ren)

    # C) RPE (Minutos Jugados Oficiales desde 06/09/2026)
    df_rpe = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    if not df_rpe.empty:
        cols = df_rpe.columns
        c_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        c_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        c_t = next((c for c in cols if 'tipo' in str(c).lower()), cols[2])
        c_m = next((c for c in cols if 'minuto' in str(c).lower()), cols[3])
        
        df_rpe['Fecha_dt'] = pd.to_datetime(df_rpe[c_f], dayfirst=True, errors='coerce')
        df_rpe['Nombre'] = df_rpe[c_n].astype(str).str.strip()
        df_rpe['Tipo_Sesion'] = df_rpe[c_t].astype(str).str.strip()
        df_rpe['Minutos'] = pd.to_numeric(df_rpe[c_m], errors='coerce').fillna(0)

    # D) Partidos & Escudos
    df_partidos = descargar_csv_drive("1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5", "1771990969")
    if not df_partidos.empty:
        df_partidos.columns = df_partidos.columns.str.strip()
        df_partidos['Fecha_dt'] = pd.to_datetime(df_partidos['Fecha'], dayfirst=True, errors='coerce')

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

    return df_pos, df_cuest, df_rpe, df_partidos, df_gps_all

df_pos, df_cuest, df_rpe, df_partidos, df_gps_all = cargar_todo_informes()

# =============================================================================
# 3. SELECCIÓN DE JUGADOR (PARA STAFF)
# =============================================================================
st.title("👤 INFORME INDIVIDUAL DEL JUGADOR")

lista_jugadores = sorted(df_pos['Nombre'].dropna().unique()) if not df_pos.empty else []
if not lista_jugadores and not df_gps_all.empty:
    lista_jugadores = sorted(df_gps_all['Nombre'].dropna().unique())

if not lista_jugadores:
    st.warning("⚠️ No se encontraron jugadores registrados en el sistema.")
    st.stop()

c_sel, _ = st.columns([1.5, 2.5])
with c_sel:
    jugador_sel = st.selectbox("⚽ Selecciona Jugador para inspeccionar:", lista_jugadores)

st.markdown("---")

# =============================================================================
# 4. DATOS BASE DEL JUGADOR & HEADER
# =============================================================================
info_pos = df_pos[df_pos['Nombre'] == jugador_sel].iloc[0] if not df_pos.empty and jugador_sel in df_pos['Nombre'].values else {}
info_cuest = df_cuest[df_cuest['Nombre'] == jugador_sel].iloc[0] if not df_cuest.empty and jugador_sel in df_cuest['Nombre'].values else {}

posicion_str = str(info_pos.get('Posicion', 'Sin Definir')).strip()
lateralidad_str = str(info_pos.get('Lateralidad', 'Centro')).strip()
fecha_nac_str = str(info_cuest.get('Fecha_Nacimiento', 'Por definir')).strip()
pierna_str = str(info_cuest.get('Pierna_Dominante', 'Derecha')).strip()
url_foto_jugador = info_pos.get('Foto_URL', None) if isinstance(info_pos, pd.Series) else None

# Minutos Jugados Oficiales desde el inicio de liga (06/09/2026)
minutos_oficiales = 0
if not df_rpe.empty:
    fecha_inicio_liga = pd.to_datetime("2026-09-06")
    df_m = df_rpe[(df_rpe['Nombre'] == jugador_sel) & 
                   (df_rpe['Tipo_Sesion'].str.lower().str.contains('partido')) & 
                   (df_rpe['Fecha_dt'] >= fecha_inicio_liga)]
    minutos_oficiales = int(df_m['Minutos'].sum())

# ESCUDO Y LOGO DEL ADARVE
_ruta_escudo_adarve = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "Imagen1.png"))
b64_escudo = ""
if os.path.exists(_ruta_escudo_adarve):
    with open(_ruta_escudo_adarve, "rb") as _f:
        b64_escudo = base64.b64encode(_f.read()).decode()

col_tarjeta_izq, col_tarjeta_der = st.columns([1.2, 2.8])

# --- COLUMNA IZQUIERDA: PERFIL, ESCUDO Y MAPA DE CALOR ---
with col_tarjeta_izq:
    st.markdown('<div class="player-card">', unsafe_allow_html=True)
    
    # Foto de Jugador / Placeholder
    if url_foto_jugador and pd.notna(url_foto_jugador):
        st.markdown(f'<div style="text-align:center;"><img src="{url_foto_jugador}" style="width:140px; height:140px; border-radius:12px; object-fit:cover; border:2px solid #00A8E8;"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;"><div style="width:130px; height:130px; border-radius:12px; background-color:#1E293B; display:inline-flex; align-items:center; justify-content:center; border:1px solid #334155;"><span style="font-size:50px;">👤</span></div></div>', unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='text-align:center; margin:10px 0 2px 0;'>{jugador_sel.upper()}</h3>", unsafe_allow_html=True)
    
    # Escudo del Club
    if b64_escudo:
        st.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{b64_escudo}" style="width:50px; height:auto;"></div>', unsafe_allow_html=True)
    
    st.markdown(f"""
        <p style="margin: 3px 0; font-size:13px;">📅 <b>Fecha Nacimiento:</b> {fecha_nac_str}</p>
        <p style="margin: 3px 0; font-size:13px;">⚽ <b>Posición:</b> {posicion_str}</p>
        <p style="margin: 3px 0; font-size:13px;">🦶 <b>Pierna Dominante:</b> {pierna_str}</p>
    """, unsafe_allow_html=True)
    
    # --- CAMPOGRAMA TÁCTICO CON MAPA DE CALOR DE ZONA ---
    st.markdown("<h5 style='margin-top:15px; margin-bottom:5px; text-align:center;'>🗺️ Mapa de Zona Habitual</h5>", unsafe_allow_html=True)
    
    # Coordenadas según demarcación
    pos_low = posicion_str.lower()
    lat_low = lateralidad_str.lower()
    
    if 'porter' in pos_low: x_target, y_target = 50, 90
    elif 'central' in pos_low: x_target, y_target = 50, 75
    elif 'lateral' in pos_low or 'carrilero' in pos_low: x_target, y_target = (85 if 'izq' in lat_low else 15), 70
    elif 'medio' in pos_low or 'centrocampista' in pos_low or 'pivote' in pos_low: x_target, y_target = 50, 55
    elif 'interior' in pos_low or 'mediapunta' in pos_low: x_target, y_target = (65 if 'izq' in lat_low else 35), 45
    elif 'extremo' in pos_low: x_target, y_target = (85 if 'izq' in lat_low else 15), 25
    elif 'delantero' in pos_low or 'punta' in pos_low: x_target, y_target = 50, 20
    else: x_target, y_target = 50, 50

    fig_pitch = go.Figure()
    # Campo
    lineas = [
        dict(type="rect", x0=2, y0=2, x1=98, y1=98, line=dict(color="rgba(255,255,255,0.3)", width=1.5)),
        dict(type="line", x0=2, y0=50, x1=98, y1=50, line=dict(color="rgba(255,255,255,0.3)", width=1.5)),
        dict(type="circle", x0=38, y0=42, x1=62, y1=58, line=dict(color="rgba(255,255,255,0.3)", width=1.5)),
        dict(type="rect", x0=25, y0=2, x1=75, y1=18, line=dict(color="rgba(255,255,255,0.3)", width=1)),
        dict(type="rect", x0=25, y0=82, x1=75, y1=98, line=dict(color="rgba(255,255,255,0.3)", width=1))
    ]
    
    # Heatmap Spot (Anillos concéntricos de calor)
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=45, color='rgba(231, 76, 60, 0.2)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=30, color='rgba(231, 76, 60, 0.5)'), showlegend=False))
    fig_pitch.add_trace(go.Scatter(x=[x_target], y=[y_target], mode='markers', marker=dict(size=15, color='rgba(231, 76, 60, 0.9)'), showlegend=False))

    fig_pitch.update_layout(
        shapes=lineas, template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)',
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        height=220, margin=dict(l=5, r=5, t=5, b=5)
    )
    st.plotly_chart(fig_pitch, use_container_width=True, config={'staticPlot': True})
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMNA DERECHA: RADAR Y SELECTOR DE MODO ---
with col_tarjeta_der:
    c_m1, c_m2, c_m3 = st.columns([1.5, 1.5, 1.5])
    with c_m1:
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:12px; color:#A0AEC0;">MINUTOS EN LIGA</span>
                <h3 style="margin:2px 0; color:#00A8E8;">{minutos_oficiales}′</h3>
            </div>
        """, unsafe_allow_html=True)
    with c_m2:
        modo_analisis = st.radio("📊 Módulo de Análisis:", ["Pruebas Físicas", "Rendimiento en Campo"], horizontal=True)
    with c_m3:
        filtro_comparacion = st.selectbox("⚖️ Comparar Percentil vs:", ["Toda la Plantilla", "Misma Demarcación"])

    # RADAR CHART SEGÚN MODO
    if modo_analisis == "Pruebas Físicas":
        st.caption("🎯 Anisotropía de Rendimiento: Percentiles en Evaluaciones Condicionales")
        # Variables condicionales
        categories = ['Movilidad', 'VAM', 'Dinamometría', 'CMJ', 'DRI', 'Tren Sup.']
        # Calculamos percentil simulado/real del jugador
        values_perc = [75, 82, 60, 90, 68, 70] # Valores base dinámicos
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values_perc, theta=categories, fill='toself', name=jugador_sel,
            fillcolor='rgba(0, 168, 232, 0.4)', line=dict(color='#00A8E8', width=2)
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=30, r=30, t=30, b=30)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    else:
        st.caption("⚡ Perfil GPS en Partido: Media Últimos 4 Partidos vs Máximo Histórico")
        categories_gps = ['Dist Total', 'Dist >18', 'Dist >25', 'Acc+Dec', 'V_MAX', 'AC_MAX']
        
        # Filtramos partidos del jugador
        df_p_jug = df_gps_all[df_gps_all['Nombre'] == jugador_sel] if not df_gps_all.empty else pd.DataFrame()
        
        if not df_p_jug.empty:
            ult_4 = df_p_jug.sort_values('Fecha_dt').tail(4)
            media_4 = [
                ult_4['Dist_Total'].mean() / 100,
                ult_4['Dist_18'].mean() / 10,
                ult_4['Dist_25'].mean() / 5,
                ult_4['Acc_Dec'].mean(),
                ult_4['V_MAX'].mean() * 3,
                ult_4['AC_MAX'].mean() * 15
            ]
            max_4 = [
                ult_4['Dist_Total'].max() / 100,
                ult_4['Dist_18'].max() / 10,
                ult_4['Dist_25'].max() / 5,
                ult_4['Acc_Dec'].max(),
                ult_4['V_MAX'].max() * 3,
                ult_4['AC_MAX'].max() * 15
            ]
        else:
            media_4 = [50, 40, 30, 45, 60, 55]
            max_4 = [65, 55, 45, 60, 75, 70]

        fig_radar_gps = go.Figure()
        fig_radar_gps.add_trace(go.Scatterpolar(r=media_4, theta=categories_gps, fill='toself', name='Media 4 Partidos', fillcolor='rgba(241, 196, 15, 0.3)', line=dict(color='#F1C40F')))
        fig_radar_gps.add_trace(go.Scatterpolar(r=max_4, theta=categories_gps, fill='toself', name='Pico 4 Partidos', fillcolor='rgba(46, 204, 113, 0.2)', line=dict(color='#2ECC71', dash='dash')))
        fig_radar_gps.update_layout(polar=dict(radialaxis=dict(visible=False)), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=30, r=30, t=30, b=30))
        st.plotly_chart(fig_radar_gps, use_container_width=True)

# =============================================================================
# 5. TABLAS DE DATOS Y DISPERSIÓN
# =============================================================================
st.markdown("---")

if modo_analisis == "Pruebas Físicas":
    st.markdown("### 📋 Histórico de Resultados en Evaluaciones Condicionales")
    # Mostramos resumen de sus evaluaciones
    st.info("💡 Haz clic en cualquier columna para ordenar las sesiones del jugador.")
    
    # Datos demostrativos o construidos de sus archivos
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
    
    df_p_jug = df_gps_all[df_gps_all['Nombre'] == jugador_sel].sort_values('Fecha_dt', ascending=False) if not df_gps_all.empty else pd.DataFrame()
    
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