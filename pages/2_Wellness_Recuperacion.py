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
st.caption("Control de métricas de estado biológico (Wellness 15s) y estado neuromuscular del SNC (Drop Jump 4s) del ADARVE JUVENIL DH.")
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
        if tiene_saltos_hoy:
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=df_cruzado['JUGADOR'], y=df_cruzado['Z_SCORE_WELLNESS'],
                    name='Wellness (15s móvil)', marker_color='#00A8E8',
                    text=df_cruzado['Z_SCORE_WELLNESS'].round(1), textposition='auto', hoverinfo='skip'
                ))
                fig_bar.add_trace(go.Bar(
                    x=df_cruzado['JUGADOR'], y=df_cruzado['Z_SCORE_SALTO'],
                    name='Salto DRI (4s móvil)', marker_color='#FFC107',
                    text=df_cruzado['Z_SCORE_SALTO'].round(1), textposition='auto', hoverinfo='skip'
                ))
                fig_bar.add_shape(type="line", x0=-0.5, x1=len(df_cruzado)-0.5, y0=-1.5, y1=-1.5, line=dict(color="#B31F24", width=2, dash="dash"))
                fig_bar.update_layout(
                    title="Estado Percibido (Wellness) vs Fatiga Neuromuscular (Drop Jump)",
                    xaxis_title="Jugadores analizados", yaxis_title="Z-Score", barmode='group',
                    template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(range=[-3.1, 3.1]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=500
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_g2:
                fig_scatter = go.Figure()
                textos_hover_scatter = []
                for _, row in df_cruzado.iterrows():
                    estado_txt = "🚑 Enfermería" if row['DISPONIBLE'] == 'no' else "🟢 Disponible"
                    hover_html = (
                        f"<b>Jugador:</b> {row['JUGADOR']}<br>"
                        f"<b>Wellness Z-Score (15s):</b> {round(row['Z_SCORE_WELLNESS'], 2)}<br>"
                        f"<b>Salto Z-Score (4s):</b> {round(row['Z_SCORE_SALTO'], 2) if pd.notna(row['Z_SCORE_SALTO']) else '-'}<br>"
                        f"<b>Molestia:</b> {row['ZONA_DOLOR']}<br>"
                        f"<b>Estado:</b> {estado_txt}"
                    )
                    textos_hover_scatter.append(hover_html)
                    
                fig_scatter.add_trace(go.Scatter(
                    x=df_cruzado['Z_SCORE_WELLNESS'], y=df_cruzado['Z_SCORE_SALTO'],
                    mode='markers+text', text=df_cruzado['JUGADOR'], textposition='top center',
                    hovertext=textos_hover_scatter, hoverinfo='text',
                    marker=dict(size=14, color=np.where(df_cruzado['Z_SCORE_SALTO'] < -1.5, '#B31F24', '#00A8E8'), line=dict(width=1.5, color='white')),
                    name='Jugador'
                ))
                fig_scatter.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.25)", line_width=1)
                fig_scatter.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.25)", line_width=1)
                fig_scatter.add_annotation(x=1.6, y=1.6, text="🟢 RECUPERADO", showarrow=False, font=dict(color="#2ECC71", size=10, weight="bold"))
                fig_scatter.add_annotation(x=-1.6, y=1.6, text="🟡 FATIGA PERCIBIDA", showarrow=False, font=dict(color="#FFC107", size=10, weight="bold"))
                fig_scatter.add_annotation(x=1.6, y=-1.6, text="🟠 RIESGO OCULTO (SNC)", showarrow=False, font=dict(color="#D35400", size=10, weight="bold"))
                fig_scatter.add_annotation(x=-1.6, y=-1.6, text="🔴 FATIGA INTEGRAL", showarrow=False, font=dict(color="#B31F24", size=10, weight="bold"))
                fig_scatter.update_layout(
                    title="Matriz de Readiness y Toma de Decisiones",
                    xaxis_title="← Más Fatiga Subjetiva | Wellness Z-Score | Más Frescura →",
                    yaxis_title="← Fatiga Central (SNC) | Salto Z-Score (DRI) | SNC Óptimo →",
                    template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(range=[-3.2, 3.2]), yaxis=dict(range=[-3.2, 3.2]),
                    height=500, showlegend=False
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
        else:
            fig_bar_only = go.Figure()
            colores_wellness_barras = []
            for val in df_cruzado['Z_SCORE_WELLNESS']:
                if -1.5 <= val <= 1.5: colores_wellness_barras.append('#00A8E8')
                elif -2.5 <= val < -1.5: colores_wellness_barras.append('#D35400')
                elif val < -2.5: colores_wellness_barras.append('#B31F24')
                else: colores_wellness_barras.append('#2ECC71')
                    
            fig_bar_only.add_trace(go.Bar(
                x=df_cruzado['JUGADOR'], y=df_cruzado['Z_SCORE_WELLNESS'],
                marker_color=colores_wellness_barras, text=df_cruzado['Z_SCORE_WELLNESS'].round(2),
                textposition='auto', name='Z-Score Wellness'
            ))
            fig_bar_only.add_shape(type="line", x0=-0.5, x1=len(df_cruzado)-0.5, y0=-1.5, y1=-1.5, line=dict(color="#D35400", width=1.5, dash="dash"))
            fig_bar_only.add_shape(type="line", x0=-0.5, x1=len(df_cruzado)-0.5, y0=-2.5, y1=-2.5, line=dict(color="#B31F24", width=1.5, dash="dot"))
            
            fig_bar_only.update_layout(
                title=f"Desviación de Wellness Individual el {fecha_seleccionada.strftime('%d/%m/%Y')} (Sin test de salto registrado)",
                xaxis_title="Plantilla Analizada", yaxis_title="Z-Score de Carga Interna (Wellness)",
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(range=[min(df_cruzado['Z_SCORE_WELLNESS'].min() - 0.5, -3.0), max(df_cruzado['Z_SCORE_WELLNESS'].max() + 0.5, 3.0)]), height=500
            )
            st.plotly_chart(fig_bar_only, use_container_width=True)
    else:
        st.info("No hay registros de Wellness para este día.")

# ==========================================
    # 9. NUEVO: MAPA ANATÓMICO PORCENTUAL DE MOLESTIAS (OPCIÓN A)
    # ==========================================
    st.markdown("---")
    st.markdown(f"### 🩺 Mapa Anatómico de Molestias y Carga Muscular ({fecha_seleccionada.strftime('%d/%m/%Y')})")
    st.caption("Solo se contabilizan los jugadores DISPONIBLES para entrenar hoy (excluyendo bajas/lesionados).")

    # Consideramos disponible a cualquier jugador que NO haya marcado "no" en la disponibilidad
    df_disp = df_cruzado[~df_cruzado['DISPONIBLE'].str.startswith('no', na=False)].copy()
    total_disponibles = len(df_disp)

    if total_disponibles == 0:
        st.warning("⚠️ No hay jugadores disponibles en la sesión seleccionada.")
    else:
        # Definición de las 5 zonas según la encuesta
        zonas_definidas = ['Cuadriceps', 'Pubis', 'Adductores', 'Isquios', 'Gemelos']
        dict_conteo_zonas = {z: [] for z in zonas_definidas}

        # Conteo por zona
        for _, r in df_disp.iterrows():
            j_nom = r['JUGADOR']
            z_resp = str(r['ZONA_DOLOR']).strip()
            
            if 'todo' in z_resp.lower():
                for z in zonas_definidas:
                    dict_conteo_zonas[z].append(j_nom)
            else:
                for z in zonas_definidas:
                    if z.lower() in z_resp.lower():
                        dict_conteo_zonas[z].append(j_nom)

        # Mapa de Coordenadas Anatómicas en Plotly (0 a 100)
        # Vista Anterior (Izquierda) y Vista Posterior (Derecha)
        coords_zonas = {
            'Cuadriceps': {'x': 25, 'y': 48, 'vista': 'Anterior'},
            'Pubis':      {'x': 25, 'y': 58, 'vista': 'Anterior'},
            'Adductores': {'x': 22, 'y': 52, 'vista': 'Anterior'},
            'Isquios':    {'x': 75, 'y': 48, 'vista': 'Posterior'},
            'Gemelos':    {'x': 75, 'y': 28, 'vista': 'Posterior'}
        }

        x_coords, y_coords, text_labels, text_hovers, colors, sizes = [], [], [], [], [], []

        for z in zonas_definidas:
            jugs = dict_conteo_zonas[z]
            num_jugs = len(jugs)
            pct = (num_jugs / total_disponibles) * 100 if total_disponibles > 0 else 0
            
            pos = coords_zonas[z]
            x_coords.append(pos['x'])
            y_coords.append(pos['y'])
            
            text_labels.append(f"<b>{z}</b><br>{pct:.1f}%")
            
            lista_str = "<br>• " + "<br>• ".join(jugs) if jugs else "<br><i>Ninguno</i>"
            hover_html = f"<b>{z.upper()}</b><br>Porcentaje: <b>{pct:.1f}%</b> ({num_jugs}/{total_disponibles} disp.)<br><b>Jugadores:</b>{lista_str}"
            text_hovers.append(hover_html)
            
            # Color e intensidad según el % de afectación
            if pct == 0:
                colors.append("#2ECC71") # Verde
                sizes.append(28)
            elif pct < 20:
                colors.append("#F1C40F") # Amarillo
                sizes.append(36)
            elif pct < 40:
                colors.append("#E67E22") # Naranja
                sizes.append(42)
            else:
                colors.append("#E74C3C") # Rojo Intenso
                sizes.append(48)

        # Renderizado de la figura anatómica en Plotly
        fig_body = go.Figure()

        # Puntos de dolor interactivos (go.Scatter)
        fig_body.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='markers+text',
            text=text_labels,
            textposition='top center',
            hovertext=text_hovers,
            hoverinfo='text',
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.85,
                line=dict(width=2, color='white')
            )
        ))

        # Siluetas del cuerpo mediante formas geométricas estilizadas (Anterior & Posterior)
        shapes_body = [
            # Cabeza Ant
            dict(type="circle", x0=22, y0=85, x1=28, y1=95, fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            # Torso Ant
            dict(type="path", path="M 18 83 L 32 83 L 29 62 L 21 62 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            # Piernas Ant
            dict(type="path", path="M 21 62 L 24 62 L 23 20 L 19 20 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            dict(type="path", path="M 26 62 L 29 62 L 31 20 L 27 20 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            
            # Cabeza Post
            dict(type="circle", x0=72, y0=85, x1=78, y1=95, fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            # Torso Post
            dict(type="path", path="M 68 83 L 82 83 L 79 62 L 71 62 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            # Piernas Post
            dict(type="path", path="M 71 62 L 74 62 L 73 20 L 69 20 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5)),
            dict(type="path", path="M 76 62 L 79 62 L 81 20 L 77 20 Z", fillcolor="rgba(255,255,255,0.08)", line=dict(color="#666", width=1.5))
        ]

        fig_body.update_layout(
            shapes=shapes_body,
            xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(range=[10, 105], showgrid=False, zeroline=False, showticklabels=False),
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[
                dict(x=25, y=100, text="<b>VISTA ANTERIOR</b>", showarrow=False, font=dict(color="#00A8E8", size=13)),
                dict(x=75, y=100, text="<b>VISTA POSTERIOR</b>", showarrow=False, font=dict(color="#00A8E8", size=13))
            ],
            height=520,
            margin=dict(l=10, r=10, t=30, b=10)
        )

        col_mapa, col_desglose = st.columns([6, 4])
        
        with col_mapa:
            st.plotly_chart(fig_body, use_container_width=True)

        with col_desglose:
            st.markdown("#### 📋 Detalle de Plantilla Disponible Afectada")
            st.write(f"**Plantilla Disponible Hoy:** `{total_disponibles}` jugadores")
            
            for z in zonas_definidas:
                jugs = dict_conteo_zonas[z]
                pct = (len(jugs) / total_disponibles * 100) if total_disponibles > 0 else 0
                
                with st.expander(f"🔴 **{z}**: {pct:.1f}% ({len(jugs)} jug.)"):
                    if jugs:
                        for j_nom in jugs:
                            st.markdown(f"• **{j_nom}**")
                    else:
                        st.caption("Sin molestias registradas en esta zona.")

    # ==========================================
    # 10. TABLA DESPLEGABLE ADAPTATIVA E INTELIGENTE
    # ==========================================
    st.markdown("---")
    st.markdown("### 📋 Desglose Analítico de Puntuaciones")
    mostrar_tabla = st.checkbox("📋 Mostrar / Ocultar la tabla completa de valoraciones individuales", value=False)
    
    if mostrar_tabla:
        df_tabla = df_cruzado.copy()
        
        st.markdown("""
            <style>
            [data-testid="stDataFrame"] table { font-size: 14px !important; }
            [data-testid="stDataFrame"] td { padding: 6px 10px !important; }
            </style>
        """, unsafe_allow_html=True)
        
        def formatear_altura(row):
            if pd.isna(row['Z_SCORE_SALTO']): return "-  ="
            hoy = row['ALTURA_MEDIA_CM']
            return f"{hoy:.1f} 🔺" if row['Z_SCORE_SALTO'] > 0.1 else (f"{hoy:.1f} 🔻" if row['Z_SCORE_SALTO'] < -0.1 else f"{hoy:.1f} =")

        def formatear_contacto(row):
            if pd.isna(row['Z_SCORE_SALTO']): return "-  ="
            hoy = row['TC_MEDIO_S']
            return f"{hoy:.3f} 🔺" if row['Z_SCORE_SALTO'] < -0.1 else (f"{hoy:.3f} 🔻" if row['Z_SCORE_SALTO'] > 0.1 else f"{hoy:.3f} =")

        def formatear_dri(row):
            if pd.isna(row['Z_SCORE_SALTO']): return "-  ="
            hoy = row['DRI_MEDIO']
            return f"{hoy:.2f} 🔺" if row['Z_SCORE_SALTO'] > 0.1 else (f"{hoy:.2f} 🔻" if row['Z_SCORE_SALTO'] < -0.1 else f"{hoy:.2f} =")

        df_tabla['ALTURA_TXT'] = df_tabla.apply(formatear_altura, axis=1)
        df_tabla['CONTACTO_TXT'] = df_tabla.apply(formatear_contacto, axis=1)
        df_tabla['DRI_TXT'] = df_tabla.apply(formatear_dri, axis=1)
        
        columnas_filtrar = ['JUGADOR', 'SUEÑO', 'DOLOR', 'ESTRÉS', 'CARGA', 'WELLNESS_TOTAL']
        columnas_nombres = ['JUGADOR', 'SUEÑO', 'DOLOR MUSCULAR', 'ESTRÉS', 'CARGA ACUMULADA', 'MEDIA WELLNESS']
        
        if tiene_saltos_hoy:
            columnas_filtrar += ['ALTURA_TXT', 'CONTACTO_TXT', 'DRI_TXT']
            columnas_nombres += ['ALTURA (CM)', 'CONTACTO (S)', 'DRI MEDIO']
            
        columnas_filtrar += ['ZONA_DOLOR', 'DETALLE_DOLOR', 'Z_SCORE_SALTO']
        columnas_nombres += ['ZONA DE MOLESTIA', 'DETALLE MOLESTIA', 'Z_SALTO_RAW']
        
        df_final = df_tabla[columnas_filtrar].copy()
        df_final.columns = columnas_nombres
        
        def categorizar_alertas_cruzadas(row):
            w_val = row['MEDIA WELLNESS']
            z_salto = row['Z_SALTO_RAW']
            if pd.isna(z_salto):
                return "⚠️ Fatiga Subjetiva" if w_val < 3.0 else "🟢 Sin problemas"
            if w_val < 3.0 and z_salto < -1.5: return "❌ Alerta Integral"
            elif z_salto < -1.5: return "⚡ Alerta SNC (Neuromuscular)"
            elif w_val < 3.0: return "⚠️ Fatiga Subjetiva"
            return "🟢 Sin problemas"
            
        df_final['ESTADO'] = df_final.apply(categorizar_alertas_cruzadas, axis=1)
        df_final = df_final.drop(columns=['Z_SALTO_RAW'])
        df_final = df_final.sort_values(by='MEDIA WELLNESS', ascending=True).reset_index(drop=True)
        
        def colorear_celdas_criticas(val):
            try:
                if float(val) < 3.0: return 'background-color: rgba(179, 31, 36, 0.25); color: #FF8F8F; font-weight: bold;'
            except ValueError: pass
            return ''

        def colorear_dri_caida(val):
            if isinstance(val, str) and '🔻' in val: return 'background-color: rgba(179, 31, 36, 0.25); color: #FF8F8F; font-weight: bold;'
            return ''

        def colorear_molestias_activas(val):
            if isinstance(val, str) and val.strip() != "" and "no me duele nada" not in val.lower():
                return 'background-color: rgba(179, 31, 36, 0.25); color: #FF8F8F; font-weight: bold;'
            return ''

        subset_wellness = ['SUEÑO', 'DOLOR MUSCULAR', 'ESTRÉS', 'CARGA ACUMULADA', 'MEDIA WELLNESS']
        
        df_estilizado = df_final.style.map(colorear_celdas_criticas, subset=subset_wellness)
        if tiene_saltos_hoy:
            df_estilizado = df_estilizado.map(colorear_dri_caida, subset=['DRI MEDIO'])
            
        df_estilizado = df_estilizado.map(colorear_molestias_activas, subset=['ZONA DE MOLESTIA']).format({
            'SUEÑO': "{:.1f}", 'DOLOR MUSCULAR': "{:.1f}", 'ESTRÉS': "{:.1f}", 'CARGA ACUMULADA': "{:.1f}", 'MEDIA WELLNESS': "{:.1f}"
        })
        
        st.dataframe(df_estilizado, use_container_width=True, height=450)