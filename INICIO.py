import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os
import base64
from utils import aplicar_estilos_globales

# -----------------------------------------------------------------------------
# SELLO FIJO AL PIE DEL SIDEBAR (FORZADO A TAMAÑO REAL)
# -----------------------------------------------------------------------------
_dir_raiz = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.join(_dir_raiz, "assets", "logo-guille_blanco.png")

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        _b64 = base64.b64encode(_f.read()).decode()
        
    st.sidebar.markdown(f"""
        <style>
        .watermark-login {{ display: none !important; }}

        .footer-sello-unico {{
            position: fixed !important;
            bottom: 20px !important;
            left: 10px !important;
            width: 260px !important;
            text-align: center !important;
            z-index: 99999 !important;
            padding-top: 12px !important;
            border-top: 1px solid rgba(255, 255, 255, 0.15) !important;
            background-color: transparent !important;
        }}
        .footer-sello-unico img {{
            width: 195px !important;
            max-width: 195px !important;
            min-width: 195px !important;
            height: auto !important;
            margin-bottom: 8px !important;
            display: inline-block !important;
        }}
        .footer-sello-unico p {{
            font-size: 11px !important;
            color: #CCCCCC !important;
            margin: 2px 0 0 0 !important;
            letter-spacing: 0.5px !important;
        }}
        </style>

        <div class="footer-sello-unico">
            <img src="data:image/png;base64,{_b64}">
            <p>© 2026 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Adarve Juvenil DH App", layout="wide")
aplicar_estilos_globales()


# ==========================================
# 2. FUNCIONES DE EXTRACCIÓN DE DATOS
# ==========================================

@st.cache_data(ttl=30)
def obtener_cumpleaños_semana():
    sheet_id = "1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip() 
        df['Fecha de nacimiento'] = pd.to_datetime(df['Fecha de nacimiento'], dayfirst=True, errors='coerce')
        hoy = datetime.now().date()
        cumpleañeros = []
        for index, row in df.iterrows():
            if pd.isnull(row['Fecha de nacimiento']): continue
            fecha_nac = row['Fecha de nacimiento'].date()
            nombre = row['Nombre y apellidos']
            try: cumple_este_año = fecha_nac.replace(year=hoy.year)
            except ValueError: cumple_este_año = fecha_nac.replace(year=hoy.year, day=28)
            if cumple_este_año < hoy:
                try: cumple_este_año = cumple_este_año.replace(year=hoy.year + 1)
                except ValueError: cumple_este_año = cumple_este_año.replace(year=hoy.year + 1, day=28)
            dias_faltan = (cumple_este_año - hoy).days
            if 0 <= dias_faltan <= 7:
                cumpleañeros.append({"nombre": nombre, "fecha": cumple_este_año.strftime("%d/%m"), "dias": dias_faltan})
        return cumpleañeros, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=30)
def obtener_datos_partidos():
    sheet_id = "1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5"
    gid = "1771990969"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip()
        if 'Resultado' not in df.columns: return None, [], "No se encuentra la columna 'Resultado'."
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df = df.sort_values(by='Fecha').reset_index(drop=True)
        df['Resultado'] = df['Resultado'].fillna('')
        df['Resultado_Clean'] = df['Resultado'].astype(str).str.strip().str.lower()
        nulos_python = ['', 'nan', 'none', 'null', '-', 'na']
        df_jugados = df[~df['Resultado_Clean'].isin(nulos_python)]
        df_pendientes = df[df['Resultado_Clean'].isin(nulos_python)]
        racha = []
        if not df_jugados.empty:
            ultimos_5 = df_jugados.tail(5)['Resultado_Clean'].tolist()
            for r in ultimos_5:
                r_str = str(r)
                if 'victoria' in r_str: racha.append('V')
                elif 'empate' in r_str: racha.append('E')
                elif 'derrota' in r_str: racha.append('D')
        proximo_partido = None
        if not df_pendientes.empty:
            prox = df_pendientes.iloc[0]
            escudo_url = str(prox.get('Escudos', '')).strip()
            if escudo_url.lower() in nulos_python: escudo_url = None
            proximo_partido = {
                'equipo': str(prox.get('Equipo', 'Rival')).strip(),
                'condicion': str(prox.get('Casa/fuera', 'Por definir')).strip(),
                'escudo': escudo_url,
                'fecha': prox['Fecha'].strftime('%d/%m/%Y') if pd.notna(prox['Fecha']) else "Por definir"
            }
        return proximo_partido, racha, None
    except Exception as e:
        return None, [], f"Error del sistema: {str(e)}"

@st.cache_data(ttl=10)
def analizar_datos_completos():
    sheet_rpe_id = "1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s"
    gid_rpe = "1785642271"
    url_rpe = f"https://docs.google.com/spreadsheets/d/{sheet_rpe_id}/export?format=csv&gid={gid_rpe}"
    
    sheet_well_id = "12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o"
    url_well = f"https://docs.google.com/spreadsheets/d/{sheet_well_id}/export?format=csv"
    
    rpe_medio_hoy = 0.0
    sesion_tipo_hoy = "Sesión"
    rpe_olvidados = []
    rpe_respondieron = 0
    well_medio_hoy = 0.0
    well_olvidados = []
    well_criticos = []
    well_respondieron = 0
    bajas_actuales = []
    dict_wellness_jugadores = {}

    try:
        # 1. CARGA RPE
        df_rpe = pd.read_csv(url_rpe)
        df_rpe.columns = df_rpe.columns.str.strip().str.upper()
        df_rpe['Fecha_Real'] = pd.to_datetime(df_rpe['MARCA TEMPORAL'], dayfirst=True, errors='coerce')
        df_rpe = df_rpe.dropna(subset=['Fecha_Real'])
        df_rpe['Fecha_Dia'] = df_rpe['Fecha_Real'].dt.date
        df_rpe['Nombre_Clean'] = df_rpe['NOMBRE Y APELLIDOS'].fillna('Anónimo').astype(str).str.strip()
        
        # 2. CARGA WELLNESS
        df_well = pd.read_csv(url_well)
        df_well.columns = df_well.columns.str.strip().str.upper()
        df_well.columns = (df_well.columns
                           .str.replace('É', 'E').str.replace('Ú', 'U')
                           .str.replace('Á', 'A').str.replace('Í', 'I').str.replace('Ó', 'O'))
        
        df_well['Fecha_Real'] = pd.to_datetime(df_well['MARCA TEMPORAL'], dayfirst=True, errors='coerce')
        df_well = df_well.dropna(subset=['Fecha_Real'])
        df_well['Fecha_Dia'] = df_well['Fecha_Real'].dt.date
        df_well['Nombre_Clean'] = df_well['NOMBRE Y APELLIDOS'].fillna('Anónimo').astype(str).str.strip()
        
        plantilla_completa = sorted(list(set(df_rpe['Nombre_Clean'].unique()).union(set(df_well['Nombre_Clean'].unique()))))
        
        # --- PROCESAMIENTO WELLNESS ---
        ultima_fecha_well = df_well['Fecha_Dia'].max()
        if pd.notnull(ultima_fecha_well):
            df_w_hoy = df_well[df_well['Fecha_Dia'] == ultima_fecha_well].copy()
            
            col_entrenar = [c for c in df_w_hoy.columns if 'ENTRENAR' in c]
            if col_entrenar:
                df_w_hoy['Entrenar_Clean'] = df_w_hoy[col_entrenar[0]].astype(str).str.strip().str.lower()
                df_bajas = df_w_hoy[df_w_hoy['Entrenar_Clean'] == 'no']
                bajas_actuales = sorted(list(df_bajas['Nombre_Clean'].unique()))
                df_w_validos = df_w_hoy[df_w_hoy['Entrenar_Clean'] != 'no'].copy()
            else:
                df_w_validos = df_w_hoy.copy()
            
            col_sueno = [c for c in df_w_validos.columns if c.startswith('SUE')]
            col_dolor = [c for c in df_w_validos.columns if c.startswith('DOLOR')]
            col_estres = [c for c in df_w_validos.columns if c.startswith('ESTRES')]
            col_carga = [c for c in df_w_validos.columns if c.startswith('CARGA')]
            
            if col_sueno and col_dolor and col_estres and col_carga:
                v_sueno = pd.to_numeric(df_w_validos[col_sueno[0]], errors='coerce').fillna(0)
                v_dolor = pd.to_numeric(df_w_validos[col_dolor[0]], errors='coerce').fillna(0)
                v_estres = pd.to_numeric(df_w_validos[col_estres[0]], errors='coerce').fillna(0)
                v_carga = pd.to_numeric(df_w_validos[col_carga[0]], errors='coerce').fillna(0)
                
                df_w_validos['Well_Player_Mean'] = (v_sueno + v_dolor + v_estres + v_carga) / 4
                well_medio_hoy = df_w_validos['Well_Player_Mean'].mean() if not df_w_validos.empty else 0.0
                
                # Guardar el Wellness exacto por jugador para el campograma
                for _, r_w in df_w_validos.iterrows():
                    dict_wellness_jugadores[r_w['Nombre_Clean']] = r_w['Well_Player_Mean']

                df_criticos = df_w_validos[df_w_validos['Well_Player_Mean'] < 3.0]
                well_criticos = sorted(list(df_criticos['Nombre_Clean'].unique()))
            
            respondieron_w = df_w_hoy['Nombre_Clean'].unique()
            well_respondieron = len(respondieron_w)
            well_olvidados = [j for j in plantilla_completa if j not in respondieron_w and j not in bajas_actuales]

        # --- PROCESAMIENTO RPE ---
        ultima_fecha_rpe = df_rpe['Fecha_Dia'].max()
        if pd.notnull(ultima_fecha_rpe):
            df_r_hoy = df_rpe[df_rpe['Fecha_Dia'] == ultima_fecha_rpe].copy()
            
            col_cardio = [c for c in df_r_hoy.columns if 'CARDIO' in c or 'PULMONAR' in c]
            col_muscular = [c for c in df_r_hoy.columns if 'MUSCULAR' in c]
            col_tipo_sesion = [c for c in df_r_hoy.columns if 'TIPO DE SESI' in c or 'TIPO_SESI' in c]
            col_minutos = [c for c in df_r_hoy.columns if 'MINUTOS' in c]
            
            df_r_hoy['RPE_Cardio'] = pd.to_numeric(df_r_hoy[col_cardio[0]], errors='coerce').fillna(0) if col_cardio else 0
            df_r_hoy['RPE_Muscular'] = pd.to_numeric(df_r_hoy[col_muscular[0]], errors='coerce').fillna(0) if col_muscular else 0
            df_r_hoy['RPE_General'] = (df_r_hoy['RPE_Cardio'] + df_r_hoy['RPE_Muscular']) / 2
            
            df_r_hoy['Sesion_Clean'] = df_r_hoy[col_tipo_sesion[0]].fillna('').astype(str).str.strip().str.lower() if col_tipo_sesion else ''
            df_r_hoy['Minutos_Num'] = pd.to_numeric(df_r_hoy[col_minutos[0]], errors='coerce').fillna(0) if col_minutos else 0
            
            df_filtrado = df_r_hoy[df_r_hoy['Sesion_Clean'] != 'entreno a parte/lesión']
            
            if col_tipo_sesion and not df_filtrado.empty:
                etiqueta_moda = df_filtrado[col_tipo_sesion[0]].dropna().mode()
                if not etiqueta_moda.empty:
                    sesion_tipo_hoy = str(etiqueta_moda.iloc[0]).strip()
            elif col_tipo_sesion and not df_r_hoy.empty:
                sesion_tipo_hoy = str(df_r_hoy[col_tipo_sesion[0]].dropna().iloc[0]).strip()

            def es_valido_partido(row):
                if 'partido' in row['Sesion_Clean'] and row['Minutos_Num'] < 70:
                    return False
                return True
                
            if not df_filtrado.empty:
                masca_partido = df_filtrado.apply(es_valido_partido, axis=1)
                df_validos_media = df_filtrado[masca_partido]
                rpe_medio_hoy = df_validos_media['RPE_General'].mean() if not df_validos_media.empty else 0.0
            else:
                rpe_medio_hoy = 0.0
            
            respondieron_r = df_r_hoy['Nombre_Clean'].unique()
            rpe_respondieron = len(respondieron_r)
            rpe_olvidados = [j for j in plantilla_completa if j not in respondieron_r and j not in bajas_actuales]

        return (rpe_medio_hoy, sesion_tipo_hoy, rpe_olvidados, rpe_respondieron, 
                well_medio_hoy, well_olvidados, well_criticos, well_respondieron, 
                bajas_actuales, len(plantilla_completa), dict_wellness_jugadores)
                
    except Exception as e:
        return 0.0, "Sesión", [], 0, 0.0, [], [], 0, [], 22, {}

# ==========================================
# 3. SISTEMA DE LOGIN (ELIMINACIÓN RADICAL)
# ==========================================
if 'logeado' not in st.session_state:
    st.session_state['logeado'] = False

if not st.session_state['logeado']:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none; } 
        [data-testid="collapsedControl"] { display: none; }
        
        /* FULMINAR EL TEXTO DEL BOTÓN DE VISIBILIDAD DE CORZÓN */
        div[data-testid="stTextInputRootElement"] button {
            font-size: 0px !important;
            color: transparent !important;
            width: 0px !important;
            height: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            display: none !important;
        }
        
        /* Asegurar que la caja e input queden limpios */
        div[data-testid="stTextInputRootElement"] input {
            color: #FFFFFF !important;
        }
        
        div.stButton {
            margin-top: 15px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_vacia1, col_centro, col_vacia2 = st.columns([1.2, 1.6, 1.2])
    with col_centro:
        st.markdown("<br><br><br><h1 style='text-align: center; margin-bottom: 25px; letter-spacing: 1px;'>ACCESO STAFF</h1>", unsafe_allow_html=True)
        
        clave_usuario = st.text_input("Contraseña", type="password", label_visibility="collapsed", placeholder="Escribe la contraseña aquí...")
        
        if st.button("Entrar", use_container_width=True):
            if clave_usuario == "lobo":
                st.session_state['logeado'] = True
                st.rerun()
            else: 
                st.error("Contraseña incorrecta.")
    st.stop()

# ==========================================
# 4. APP PRINCIPAL
# ==========================================
else:
    c1, c2, c3 = st.columns([1, 4, 1], vertical_alignment="center")
    with c1: st.image("assets/Imagen2.png", width=120) 
    with c2: st.markdown("<h1 style='text-align: center; margin: 0;'>PREPARACIÓN FÍSICA TEMPORADA 2026/2027</h1>", unsafe_allow_html=True)
    with c3: st.image("assets/Imagen1.png", width=120)

    st.markdown("---") 
    st.markdown("### PANEL DE CONTROL GENERAL")
    
    (rpe_val, sesion_lbl, rpe_faltan, rpe_cant, well_val, well_faltan, well_mal, well_cant, lesionados, total_jugadores, dict_well_jug) = analizar_datos_completos()
    
    col1, col2, col3 = st.columns(3)
    
    # 1. TARJETA WELLNESS (SOLO FALTAN POR RELLENAR)
    with col1: 
        texto_well = f"Completados: <b>{well_cant} / {total_jugadores}</b><br><br>"
        if well_faltan:
            texto_well += f"⏳ <b>Faltan por rellenar:</b><br>" + "<br>".join([f"• {n}" for n in well_faltan])
        else:
            texto_well += f"✅ ¡Todos los cuestionarios al día!"
            
        st.markdown(
            f"""
            <div style="background-color: rgba(0, 168, 232, 0.05); padding: 20px; border-radius: 8px; border-left: 5px solid #00A8E8; min-height: 220px;">
                <h5 style="margin: 0; color: #00A8E8; font-size: 0.9em; letter-spacing: 1px;">WELLNESS</h5>
                <p style="margin: 15px 0 0 0; font-size: 0.95em; color: #CCCCCC; line-height: 1.4;">{texto_well}</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    # 2. TARJETA DE CARGA INTERNA
    with col2: 
        texto_rpe = f"RPE Medio ({sesion_lbl}): <b>{rpe_val:.1f}</b><br><br>Completados: <b>{rpe_cant} / {total_jugadores}</b>"
        if rpe_faltan:
            texto_rpe += f"<br><br>⏳ <b>Faltan por rellenar:</b><br>" + "<br>".join([f"• {n}" for n in rpe_faltan])
        else:
            texto_rpe += f"<br><br>✅ Cuestionarios al día"
            
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 193, 7, 0.04); padding: 20px; border-radius: 8px; border-left: 5px solid #FFC107; min-height: 220px;">
                <h5 style="margin: 0; color: #FFC107; font-size: 0.9em; letter-spacing: 1px;">CARGA INTERNA</h5>
                <p style="margin: 15px 0 0 0; font-size: 0.95em; color: #CCCCCC; line-height: 1.4;">{texto_rpe}</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
            
    # 3. TARJETA DE ENFERMERÍA
    with col3: 
        color_enf = "#2ECC71" if len(lesionados) == 0 else "#B31F24"
        bg_enf = "rgba(46, 204, 113, 0.04)" if len(lesionados) == 0 else "rgba(179, 31, 36, 0.04)"
        
        if lesionados:
            texto_lista_bajas = "<br>".join([f"• {b} (No disponible)" for b in lesionados])
            texto_enf = f"Bajas actuales: <b>{len(lesionados)}</b><br><br>🚑 <b>Jugadores en enfermería / otros:</b><br>{texto_lista_bajas}"
        else:
            texto_enf = "Bajas actuales: <b>0</b><br><br>✅ ¡Toda la plantilla disponible!"
            
        st.markdown(
            f"""
            <div style="background-color: {bg_enf}; padding: 20px; border-radius: 8px; border-left: 5px solid {color_enf}; min-height: 220px;">
                <h5 style="margin: 0; color: {color_enf}; font-size: 0.9em; letter-spacing: 1px;">ENFERMERÍA-OTROS</h5>
                <p style="margin: 15px 0 0 0; font-size: 0.95em; color: #CCCCCC; line-height: 1.4;">{texto_enf}</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 5. CAMPOGRAMA TÁCTICO DE DISPONIBILIDAD Y WELLNESS
    # ==========================================
    st.markdown("### ⚽ DISPONIBILIDAD DE PLANTILLA Y ESTADO DE WELLNESS")
    st.caption("Puntos verdes, amarillos y rojos indican el nivel de Wellness percibido hoy (🟢 Óptimo | 🟡 Alerta Moderada | 🔴 Alta Fatiga).")

    ruta_posiciones = os.path.join(_dir_raiz, "data", "Posiciones.xlsx")
    
    if not os.path.exists(ruta_posiciones):
        st.warning("⚠️ No se encontró el archivo 'Posiciones.xlsx' en la carpeta data/.")
    else:
        df_pos = pd.read_excel(ruta_posiciones)
        df_pos.columns = df_pos.columns.str.strip()

        # Filtrar solo disponibles (los lesionados no se dibujan en el campo)
        df_disponibles_campo = df_pos[~df_pos['Jugador'].isin(lesionados)].copy()

        # Normalizamos el diccionario de wellness para cruzar de forma segura
        dict_well_norm = {str(k).replace('_', ' ').strip().lower(): v for k, v in dict_well_jug.items()}

        agrupados = {}

        for _, row_j in df_disponibles_campo.iterrows():
            nom_original = str(row_j['Jugador'])
            nom_mostrar = nom_original.replace('_', ' ')
            nom_busqueda = nom_mostrar.strip().lower()
            
            # Estado Wellness
            w_score = dict_well_norm.get(nom_busqueda, None)
            
            # 🛑 EXCLUIR DEL CAMPOGRAMA A LOS QUE NO TIENEN DATOS (SD)
            if w_score is None or pd.isna(w_score):
                continue
                
            # Limpiamos y preparamos las posiciones (Motor Inteligente)
            pos_clean = str(row_j.get('Posicion', '')).strip().title()
            lat_clean = str(row_j.get('Lateralidad', '')).strip().title()

            # --- MOTOR DE REGLAS DE COORDENADAS (Atacando hacia Y=0, Portero Y=92) ---
            
            # COORDENADA Y (Altura del campo)
            if 'Portero' in pos_clean: y = 92
            elif 'Central' in pos_clean: y = 78
            elif 'Lateral' in pos_clean: y = 70
            elif 'Mediocentro' in pos_clean: y = 55
            elif 'Mediapunta' in pos_clean: y = 40
            elif 'Extremo' in pos_clean: y = 25
            elif 'Delantero' in pos_clean: y = 15
            else: y = 50

            # COORDENADA X (Lateralidad) -> INVERTIDO: Izquierda del jugador = Derecha pantalla (X=75-85)
            if 'Izquierd' in lat_clean:
                if 'Lateral' in pos_clean or 'Extremo' in pos_clean: x = 85
                else: x = 65
            elif 'Derech' in lat_clean:
                if 'Lateral' in pos_clean or 'Extremo' in pos_clean: x = 15
                else: x = 35
            else:
                x = 50 # Centro
                
            coord_base = (x, y)
            
            # Asignar el color del semáforo
            if w_score >= 3.0:
                color_nodo = "#2ECC71"
                txt_score = f"{w_score:.1f}"
            elif w_score >= 2.5:
                color_nodo = "#F1C40F"
                txt_score = f"{w_score:.1f}"
            else:
                color_nodo = "#E74C3C"
                txt_score = f"{w_score:.1f}"

            # Construir la línea HTML del jugador
            texto_jugador = f"<span style='color:{color_nodo}; font-size:16px;'>●</span> {nom_mostrar} <b>({txt_score})</b>"
            
            if coord_base not in agrupados:
                agrupados[coord_base] = []
            agrupados[coord_base].append(texto_jugador)

        # Preparar el lienzo de Plotly
        fig_campo = go.Figure()

        # Dibujo de Líneas Tácticas del Campo de Fútbol
        lineas_campo = [
            dict(type="rect", x0=2, y0=2, x1=98, y1=98, line=dict(color="rgba(255,255,255,0.3)", width=2)),
            dict(type="line", x0=2, y0=50, x1=98, y1=50, line=dict(color="rgba(255,255,255,0.3)", width=2)),
            dict(type="circle", x0=38, y0=42, x1=62, y1=58, line=dict(color="rgba(255,255,255,0.3)", width=2)),
            dict(type="rect", x0=25, y0=2, x1=75, y1=18, line=dict(color="rgba(255,255,255,0.3)", width=1.5)), # Área abajo
            dict(type="rect", x0=25, y0=82, x1=75, y1=98, line=dict(color="rgba(255,255,255,0.3)", width=1.5))  # Área arriba
        ]

        # Convertir listas agrupadas en Anotaciones
        anotaciones = []
        for (x, y), lista_jugs in agrupados.items():
            texto_final = "<br>".join(lista_jugs)
            anotaciones.append(
                dict(
                    x=x, y=y,
                    text=texto_final,
                    showarrow=False,
                    align='left',
                    font=dict(size=14, color="white"),
                    bgcolor="rgba(15, 23, 42, 0.85)", # Fondo para máxima legibilidad
                    bordercolor="rgba(255,255,255,0.2)",
                    borderwidth=1,
                    borderpad=8
                )
            )

        fig_campo.update_layout(
            shapes=lineas_campo,
            annotations=anotaciones,
            xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
            yaxis=dict(range=[0, 105], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
            dragmode=False, # <-- ESTO BLOQUEA TOTALMENTE EL ARRASTRE/DESCONFIGURACIÓN
            template="plotly_dark",
            paper_bgcolor='rgba(15, 23, 42, 0.6)',
            plot_bgcolor='rgba(15, 23, 42, 0.6)',
            height=780,
            margin=dict(l=10, r=10, t=20, b=10),
            showlegend=False,
            hovermode=False # <-- ESTO BLOQUEA LOS TOOLTIPS, COMPORTAMIENTO DE IMAGEN
        )

        # Usar config={'staticPlot': True} convierte la gráfica en una imagen estática 100% rígida
        st.plotly_chart(fig_campo, use_container_width=True, config={'staticPlot': True})

    st.markdown("---")
    
    # --- AGENDA Y GESTIÓN DE GRUPO ---
    st.markdown("### AGENDA Y GESTIÓN DE GRUPO")
    col_partido, col_cumples = st.columns(2)
    
    with col_partido:
        st.markdown("#### PRÓXIMO PARTIDO")
        proximo_partido, racha, error_partidos = obtener_datos_partidos()
        if error_partidos: st.error(error_partidos)
        elif proximo_partido:
            html_racha = " - ".join([f'<span style="color: {"#50C878" if r=="V" else "gray" if r=="E" else "#FF6B6B"};">{r}</span>' for r in racha]) if racha else "<span style='color: gray;'>Sin datos previos</span>"
            img_escudo = f'<img src="{proximo_partido["escudo"]}" width="50" style="margin-bottom: 5px;">' if proximo_partido["escudo"] else ""
            st.markdown(f"""
            <div style="background-color: #1E2633; border-radius: 8px; padding: 15px; text-align: center; height: 100%;">
            <p style="color: #6C8EBF; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">DIVISIÓN DE HONOR JUVENIL</p>
            {img_escudo}
            <h3 style="margin: 5px 0;">ADARVE JUVENIL DH <span style="font-weight: normal; font-size: 0.8em; color: gray;">vs</span> {proximo_partido["equipo"].upper()}</h3>
            <p style="margin: 0; font-size: 0.9em;">📍 <strong>{proximo_partido["condicion"].upper()}</strong> | 📅 {proximo_partido["fecha"]}</p>
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #2C384A;">
            <p style="margin: 0; font-size: 0.8em; color: gray;">RACHA ÚLTIMOS PARTIDOS</p>
            <p style="margin: 5px 0 0 0; font-weight: bold; letter-spacing: 2px;">{html_racha}</p>
            </div></div>""", unsafe_allow_html=True)
        else: st.info("No hay próximos partidos programados en el calendario.")
        
    with col_cumples:
        st.markdown("#### CUMPLEAÑOS DE LA SEMANA")
        cumples_semana, error_msg = obtener_cumpleaños_semana()
        html_cumples = """<div style="background-color: #1E2633; border-radius: 8px; padding: 15px; height: 100%;"><p style="margin: 0; font-weight: bold; color: #50C878;">Celebraciones en los próximos 7 días:</p><ul style="margin-top: 10px; padding-left: 20px;">"""
        if cumples_semana is None: html_cumples += f"<li><span style='color: #FF6B6B;'>Error: {error_msg}</span></li>"
        elif len(cumples_semana) == 0: html_cumples += "<li><i>No hay cumpleaños programados para esta semana.</i></li>"
        else:
            for c in sorted(cumples_semana, key=lambda x: x['dias']):
                texto_dias = "<span style='color: #50C878; font-weight: bold;'>¡ES HOY! 🎂</span>" if c['dias'] == 0 else f"en {c['dias']} días"
                html_cumples += f"<li style='margin-bottom: 5px;'><strong>{c['nombre']}</strong> ({c['fecha']}) - {texto_dias}</li>"
        st.markdown(html_cumples + "</ul></div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("Cerrar Sesión"):
        st.session_state['logeado'] = False
        st.rerun()