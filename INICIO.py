import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os
import re
from utils import (es_exjugador, sin_exjugadores, quitar_exjugadores, leer_sheet_csv, configurar_pagina, controles_sidebar, inyectar_css, render_html, tarjetas_kpi,
                   chips_html, nombre_bonito, fecha_es, etiqueta_sesion, estilo_fig, mostrar_fig,
                   ROJO, NARANJA, AZUL, VERDE, NEUTRO_TEXTO, TEXTO, BORDE)

# ==========================================
# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA
# ==========================================
configurar_pagina("Adarve Juvenil DH App")
_dir_raiz = os.path.dirname(os.path.abspath(__file__))

# Umbrales wellness (escala 1-5, 5 = mejor)
WELL_ALERTA = 3.0     # media < 3.0  -> alerta (rojo)
WELL_AVISO = 3.3      # media < 3.3  -> aviso (amarillo)
ITEM_CRITICO = 1      # algún ítem en el mínimo (1) -> aviso

# ==========================================
# 2. FUNCIONES DE EXTRACCIÓN DE DATOS
# ==========================================
def obtener_cumpleaños_semana():
    sheet_id = "1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = leer_sheet_csv(url_csv)
        df.columns = df.columns.str.strip()
        df['Fecha de nacimiento'] = pd.to_datetime(df['Fecha de nacimiento'], dayfirst=True, errors='coerce')
        hoy = datetime.now().date()
        cumpleañeros = []
        for _, row in df.iterrows():
            if pd.isnull(row['Fecha de nacimiento']): continue
            fecha_nac = row['Fecha de nacimiento'].date()
            nombre = row['Nombre y apellidos']
            if es_exjugador(nombre): continue
            try: cumple = fecha_nac.replace(year=hoy.year)
            except ValueError: cumple = fecha_nac.replace(year=hoy.year, day=28)
            if cumple < hoy:
                try: cumple = cumple.replace(year=hoy.year + 1)
                except ValueError: cumple = cumple.replace(year=hoy.year + 1, day=28)
            dias = (cumple - hoy).days
            if 0 <= dias <= 7:
                cumpleañeros.append({"nombre": nombre, "fecha": cumple.strftime("%d/%m"), "dias": dias})
        return cumpleañeros, None
    except Exception as e:
        return None, str(e)


def obtener_datos_partidos():
    sheet_id = "1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5"
    gid = "1771990969"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = leer_sheet_csv(url_csv)
        df.columns = df.columns.str.strip()
        if 'Resultado' not in df.columns or 'Casa/fuera' not in df.columns:
            return None, [], "No se encuentran las columnas 'Resultado' o 'Casa/fuera'."
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df = df.sort_values(by='Fecha').reset_index(drop=True)

        def parsear_resultado(row):
            res_raw = str(row.get('Resultado', '')).strip()
            condicion = str(row.get('Casa/fuera', '')).strip().lower()
            if not res_raw or res_raw.lower() in ['', 'nan', 'none', 'null', '-', 'na']:
                return None
            match = re.search(r'(\d+)\s*[-:\s_xX]\s*(\d+)', res_raw)
            if not match:
                return None
            g_local, g_visit = int(match.group(1)), int(match.group(2))
            if 'casa' in condicion or 'local' in condicion:
                g_ad, g_riv = g_local, g_visit
            else:
                g_ad, g_riv = g_visit, g_local
            return 'V' if g_ad > g_riv else ('D' if g_ad < g_riv else 'E')

        df['Resultado_Signo'] = df.apply(parsear_resultado, axis=1)
        df_jugados = df[df['Resultado_Signo'].notna()]
        df_pendientes = df[df['Resultado_Signo'].isna()]
        racha = df_jugados.tail(5)['Resultado_Signo'].tolist() if not df_jugados.empty else []

        proximo = None
        if not df_pendientes.empty:
            prox = df_pendientes.iloc[0]
            escudo = str(prox.get('Escudos', '')).strip()
            if escudo.lower() in ['', 'nan', 'none', 'null', '-', 'na']: escudo = None
            proximo = {
                'equipo': str(prox.get('Equipo', 'Rival')).strip(),
                'condicion': str(prox.get('Casa/fuera', 'Por definir')).strip(),
                'escudo': escudo,
                'fecha': prox['Fecha'].strftime('%d/%m/%Y') if pd.notna(prox['Fecha']) else "Por definir"
            }
        return proximo, racha, None
    except Exception as e:
        return None, [], f"Error del sistema: {str(e)}"


def analizar_datos_completos():
    """Devuelve un diccionario con el resumen del día (wellness, RPE, bajas).
    Si algo falla, 'error' contiene el motivo (antes se ocultaba y salían ceros)."""
    url_rpe = "https://docs.google.com/spreadsheets/d/1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s/export?format=csv&gid=1785642271"
    url_well = "https://docs.google.com/spreadsheets/d/12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o/export?format=csv"

    r = dict(rpe_medio=np.nan, rpe_n_validos=0, sesion_tipo="Sesión", fecha_rpe=None, rpe_olvidados=[], rpe_respondieron=0,
             well_medio=np.nan, fecha_well=None, well_olvidados=[], well_respondieron=0,
             bajas=[], total=0, dict_wellness={}, dict_items_bajos={}, error=None)
    try:
        df_rpe = leer_sheet_csv(url_rpe)
        df_rpe.columns = df_rpe.columns.str.strip().str.upper()
        df_rpe['Fecha_Real'] = pd.to_datetime(df_rpe['MARCA TEMPORAL'], dayfirst=True, errors='coerce')
        df_rpe = df_rpe.dropna(subset=['Fecha_Real'])
        df_rpe['Fecha_Dia'] = df_rpe['Fecha_Real'].dt.date
        df_rpe['Nombre_Clean'] = df_rpe['NOMBRE Y APELLIDOS'].fillna('Anónimo').astype(str).str.strip()
        df_rpe = quitar_exjugadores(df_rpe, 'Nombre_Clean')

        df_well = leer_sheet_csv(url_well)
        df_well.columns = (df_well.columns.str.strip().str.upper()
                           .str.replace('É', 'E').str.replace('Ú', 'U').str.replace('Á', 'A')
                           .str.replace('Í', 'I').str.replace('Ó', 'O'))
        df_well['Fecha_Real'] = pd.to_datetime(df_well['MARCA TEMPORAL'], dayfirst=True, errors='coerce')
        df_well = df_well.dropna(subset=['Fecha_Real'])
        df_well['Fecha_Dia'] = df_well['Fecha_Real'].dt.date
        df_well['Nombre_Clean'] = df_well['NOMBRE Y APELLIDOS'].fillna('Anónimo').astype(str).str.strip()
        df_well = quitar_exjugadores(df_well, 'Nombre_Clean')

        ruta_pos = os.path.join(_dir_raiz, "data", "Posiciones.xlsx")
        plantilla = None
        if os.path.exists(ruta_pos):
            try:
                df_p = pd.read_excel(ruta_pos)
                df_p.columns = df_p.columns.str.strip()
                col_j = 'Jugador' if 'Jugador' in df_p.columns else df_p.columns[0]
                plantilla = sorted(df_p[col_j].dropna().astype(str).str.strip().tolist())
            except Exception:
                plantilla = None
        if plantilla is None:
            plantilla = sorted(set(df_rpe['Nombre_Clean']).union(set(df_well['Nombre_Clean'])))
        plantilla = sin_exjugadores(plantilla)
        r['total'] = len(plantilla)

        # --- WELLNESS (último día con respuestas) ---
        ult_w = df_well['Fecha_Dia'].max()
        if pd.notnull(ult_w):
            r['fecha_well'] = ult_w
            df_w = df_well[df_well['Fecha_Dia'] == ult_w].copy()
            col_entrenar = [c for c in df_w.columns if 'ENTRENAR' in c]
            if col_entrenar:
                df_w['Entrenar_Clean'] = df_w[col_entrenar[0]].astype(str).str.strip().str.lower()
                r['bajas'] = sorted(df_w[df_w['Entrenar_Clean'].str.startswith('no')]['Nombre_Clean'].unique())
                df_val = df_w[~df_w['Entrenar_Clean'].str.startswith('no')].copy()
            else:
                df_val = df_w.copy()

            cols_items = {}
            for pref, nombre in [('SUE', 'Sueño'), ('DOLOR', 'Dolor'), ('ESTRES', 'Estrés'), ('CARGA', 'Carga')]:
                c = [x for x in df_val.columns if x.startswith(pref)]
                if c: cols_items[nombre] = c[0]
            if len(cols_items) == 4:
                # CORRECCIÓN: un ítem vacío ya NO cuenta como 0 (antes bajaba la media y daba falsas alertas)
                items = df_val[list(cols_items.values())].apply(pd.to_numeric, errors='coerce')
                items.columns = list(cols_items.keys())
                df_val['Well_Media'] = items.mean(axis=1, skipna=True)
                r['well_medio'] = df_val['Well_Media'].mean()
                for i, row in df_val.iterrows():
                    r['dict_wellness'][row['Nombre_Clean']] = row['Well_Media']
                    bajos = [k for k, v in items.loc[i].items() if pd.notna(v) and v <= ITEM_CRITICO]
                    if bajos: r['dict_items_bajos'][row['Nombre_Clean']] = bajos

            respondieron_w = set(df_w['Nombre_Clean'].unique())
            r['well_respondieron'] = len(respondieron_w)
            r['well_olvidados'] = [j for j in plantilla if j not in respondieron_w and j not in r['bajas']]

        # --- RPE (último día con respuestas) ---
        ult_r = df_rpe['Fecha_Dia'].max()
        if pd.notnull(ult_r):
            r['fecha_rpe'] = ult_r
            df_r = df_rpe[df_rpe['Fecha_Dia'] == ult_r].copy()
            col_cardio = [c for c in df_r.columns if 'CARDIO' in c or 'PULMONAR' in c]
            col_musc = [c for c in df_r.columns if 'MUSCULAR' in c]
            col_tipo = [c for c in df_r.columns if 'TIPO DE SESI' in c or 'TIPO_SESI' in c]
            col_min = [c for c in df_r.columns if 'MINUTOS' in c]
            cardio = pd.to_numeric(df_r[col_cardio[0]], errors='coerce') if col_cardio else np.nan
            musc = pd.to_numeric(df_r[col_musc[0]], errors='coerce') if col_musc else np.nan
            df_r['RPE_General'] = pd.concat([pd.Series(cardio, index=df_r.index), pd.Series(musc, index=df_r.index)], axis=1).mean(axis=1)
            df_r['Sesion_Clean'] = df_r[col_tipo[0]].fillna('').astype(str).str.strip().str.lower() if col_tipo else ''
            df_r['Minutos_Num'] = pd.to_numeric(df_r[col_min[0]], errors='coerce').fillna(0) if col_min else 0
            df_f = df_r[df_r['Sesion_Clean'] != 'entreno a parte/lesión']
            if col_tipo and not df_f.empty:
                moda = df_f[col_tipo[0]].dropna().mode()
                if not moda.empty: r['sesion_tipo'] = str(moda.iloc[0]).strip()
            # Partido: solo cuentan para la media quienes jugaron >= 60' (mismo criterio que la página GPS)
            df_validos = df_f[~(df_f['Sesion_Clean'].str.contains('partido') & (df_f['Minutos_Num'] < 60))]
            r['rpe_n_validos'] = int(df_validos['RPE_General'].notna().sum())
            r['rpe_medio'] = df_validos['RPE_General'].mean() if not df_validos.empty else np.nan
            respondieron_r = set(df_r['Nombre_Clean'].unique())
            r['rpe_respondieron'] = len(respondieron_r)
            r['rpe_olvidados'] = [j for j in plantilla if j not in respondieron_r and j not in r['bajas']]
        return r
    except Exception as e:
        r['error'] = str(e)
        return r


# ==========================================
# 3. SISTEMA DE LOGIN
# ==========================================
if 'logeado' not in st.session_state:
    st.session_state['logeado'] = False

if not st.session_state['logeado']:
    inyectar_css("""
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        div[data-testid="stTextInputRootElement"] button { display: none !important; }
        div[data-testid="stTextInputRootElement"] input { color: #FFFFFF !important; }
        div.stButton { margin-top: 15px; }
    """)
    col_vacia1, col_centro, col_vacia2 = st.columns([1.2, 1.6, 1.2])
    with col_centro:
        render_html("<div style='margin-top: 70px; margin-bottom: 25px; text-align: center;'><h1 style='color: white; font-size: 2.2rem; letter-spacing: 1px;'>ACCESO STAFF</h1></div>")
        clave_usuario = st.text_input("Contraseña", type="password", label_visibility="collapsed", placeholder="Escribe la contraseña aquí...")
        if st.button("Entrar", width="stretch"):
            if clave_usuario == "lobo":
                st.session_state['logeado'] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()

# ==========================================
# 4. APP PRINCIPAL
# ==========================================
movil = controles_sidebar()

inyectar_css("""
    .cabecera-ini { display:flex; align-items:center; justify-content:space-between; gap:16px; }
    .cabecera-ini img { width: 110px; height:auto; }
    .cabecera-ini h1 { text-align:center; margin:0; color:white; font-size:2.5rem; letter-spacing:1.5px; line-height:1.15; flex:1; }
    .tarjeta-ini { background:#1E2633; border-radius:10px; padding:15px; height:100%; }
    @media (max-width: 768px) {
        .cabecera-ini img { width: 54px; }
        .cabecera-ini h1 { font-size: 1.35rem !important; }
    }
""")

def _img_b64(ruta):
    import base64
    if not os.path.exists(ruta): return ""
    with open(ruta, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

render_html(f"""
    <div class="cabecera-ini">
        <img src="{_img_b64(os.path.join(_dir_raiz, 'assets', 'Imagen2.png'))}">
        <h1>PREPARACIÓN FÍSICA TEMPORADA 2026/2027</h1>
        <img src="{_img_b64(os.path.join(_dir_raiz, 'assets', 'Imagen1.png'))}">
    </div>
""")
st.markdown("---")

# --- PRÓXIMO PARTIDO Y CUMPLEAÑOS ---
col_partido, col_cumples = st.columns(2)
with col_partido:
    st.markdown("### ⚽ PRÓXIMO PARTIDO")
    proximo, racha, error_partidos = obtener_datos_partidos()
    if error_partidos:
        st.error(error_partidos)
    elif proximo:
        colores_r = {"V": VERDE, "E": NEUTRO_TEXTO, "D": ROJO}
        html_racha = " ".join([f'<span style="display:inline-block; width:26px; height:26px; line-height:26px; border-radius:6px; '
                               f'background:{colores_r[x]}22; color:{colores_r[x]}; font-weight:800;">{x}</span>' for x in racha]) \
            if racha else "<span style='color: gray;'>Sin datos previos</span>"
        img_escudo = f'<img src="{proximo["escudo"]}" width="50" style="margin-bottom: 5px;">' if proximo["escudo"] else ""
        render_html(f"""
            <div class="tarjeta-ini" style="text-align:center;">
                <p style="color:#6C8EBF; font-weight:bold; margin-bottom:5px; font-size:0.85em;">DIVISIÓN DE HONOR JUVENIL</p>
                {img_escudo}
                <h3 style="margin:5px 0; color:white;">ADARVE JUVENIL DH <span style="font-weight:normal; font-size:0.8em; color:gray;">vs</span> {proximo["equipo"].upper()}</h3>
                <p style="margin:0; font-size:0.9em; color:#CCCCCC;">📍 <strong>{proximo["condicion"].upper()}</strong> | 📅 {proximo["fecha"]}</p>
                <div style="margin-top:12px; padding-top:12px; border-top:1px solid #2C384A;">
                    <p style="margin:0; font-size:0.75em; color:gray;">ÚLTIMOS 5 PARTIDOS (antiguo → reciente)</p>
                    <p style="margin:6px 0 0 0; letter-spacing:2px;">{html_racha}</p>
                </div>
            </div>
        """)
    else:
        st.info("No hay próximos partidos programados en el calendario.")

with col_cumples:
    st.markdown("### 🎂 CUMPLEAÑOS DE LA SEMANA")
    cumples, error_msg = obtener_cumpleaños_semana()
    html_c = "<div class='tarjeta-ini'><p style='margin:0; font-weight:bold; color:#50C878;'>Próximos 7 días:</p><ul style='margin-top:10px; padding-left:20px; color:#CCCCCC;'>"
    if cumples is None:
        html_c += f"<li><span style='color:{ROJO};'>Error: {error_msg}</span></li>"
    elif not cumples:
        html_c += "<li><i>No hay cumpleaños esta semana.</i></li>"
    else:
        for c in sorted(cumples, key=lambda x: x['dias']):
            txt = f"<span style='color:#50C878; font-weight:bold;'>¡ES HOY! 🎂</span>" if c['dias'] == 0 else f"en {c['dias']} días"
            html_c += f"<li style='margin-bottom:5px;'><strong>{nombre_bonito(c['nombre'])}</strong> ({c['fecha']}) - {txt}</li>"
    html_c += "</ul></div>"
    render_html(html_c)

st.markdown("---")

# --- PANEL DE CONTROL GENERAL ---
st.markdown("### PANEL DE CONTROL GENERAL")
d = analizar_datos_completos()
if d['error']:
    st.error(f"⚠️ No se pudieron leer los cuestionarios: {d['error']}")

total = d['total']
well_txt = f"{d['well_medio']:.1f}" if pd.notna(d['well_medio']) else "-"
color_well = ROJO if pd.notna(d['well_medio']) and d['well_medio'] < WELL_ALERTA else TEXTO
rpe_txt = f"{d['rpe_medio']:.1f}" if pd.notna(d['rpe_medio']) else "-"
# Si ha respondido menos de la mitad de la plantilla, se avisa de que la media es parcial
rpe_parcial = d['rpe_n_validos'] < max(1, total // 2)

tarjetas_kpi([
    {"titulo": f"Wellness medio ({fecha_es(d['fecha_well'], corta=True) if d['fecha_well'] else '-'})", "valor": well_txt,
     "sub": f"{d['well_respondieron']}/{total} respuestas", "color": color_well},
    {"titulo": f"RPE medio · {etiqueta_sesion(d['sesion_tipo'])}", "valor": rpe_txt,
     "sub": f"n = {d['rpe_n_validos']}" + (" · ⚠️ parcial" if rpe_parcial else ""),
     "color": NARANJA if rpe_parcial else TEXTO},
    {"titulo": "Bajas (enfermería / otros)", "valor": str(len(d['bajas'])), "color": ROJO if d['bajas'] else TEXTO},
    {"titulo": "Wellness en alerta", "valor": str(sum(1 for v in d['dict_wellness'].values() if pd.notna(v) and v < WELL_ALERTA)),
     "sub": f"media < {WELL_ALERTA:.1f}"},
])

def _detalle(titulo, nombres, color):
    if not nombres:
        return f"<div style='color:{NEUTRO_TEXTO}; font-size:.85rem; margin:6px 0'>✅ {titulo}: nadie pendiente</div>"
    return (f"<details class='desplegable' style='margin:6px 0'><summary>⏳ {titulo}: <b style='color:{color}'>{len(nombres)}</b> (pulsa para ver)</summary>"
            f"{chips_html(nombres, color)}</details>")

c1, c2, c3 = st.columns(3)
with c1:
    render_html(_detalle("Wellness sin rellenar", d['well_olvidados'], NARANJA))
with c2:
    render_html(_detalle("RPE sin rellenar", d['rpe_olvidados'], NARANJA))
with c3:
    if d['bajas']:
        render_html(f"<div style='margin:6px 0; font-size:.85rem; color:{NEUTRO_TEXTO}'>🚑 Bajas:</div>" + chips_html(d['bajas'], ROJO))
    else:
        render_html(f"<div style='color:{NEUTRO_TEXTO}; font-size:.85rem; margin:6px 0'>✅ Toda la plantilla disponible</div>")

st.markdown("---")

# ==========================================
# 5. DISPONIBILIDAD PRÓXIMA SESIÓN
# ==========================================
st.markdown("### DISPONIBILIDAD PRÓXIMA SESIÓN")
render_html(f"<div style='font-size:.85rem; color:{NEUTRO_TEXTO}'>Solo se resaltan los jugadores que requieren atención: "
            f"<b style='color:{NARANJA}'>● aviso</b> (wellness &lt; {WELL_AVISO} o algún ítem ≤ {ITEM_CRITICO}) · "
            f"<b style='color:{ROJO}'>● alerta</b> (wellness &lt; {WELL_ALERTA}). El resto aparece en gris.</div>")

ruta_posiciones = os.path.join(_dir_raiz, "data", "Posiciones.xlsx")
if not os.path.exists(ruta_posiciones):
    st.warning("⚠️ No se encontró el archivo 'Posiciones.xlsx' en la carpeta data/.")
else:
    df_pos = pd.read_excel(ruta_posiciones)
    df_pos.columns = df_pos.columns.str.strip()
    df_pos = quitar_exjugadores(df_pos, 'Jugador')
    df_disp = df_pos[~df_pos['Jugador'].isin(d['bajas'])].copy()
    dict_well_norm = {nombre_bonito(k).lower(): v for k, v in d['dict_wellness'].items()}
    dict_items_norm = {nombre_bonito(k).lower(): v for k, v in d['dict_items_bajos'].items()}

    def estado_jugador(nom):
        w = dict_well_norm.get(nom.lower())
        if w is None or pd.isna(w): return None, None
        if w < WELL_ALERTA: return "alerta", ROJO
        if w < WELL_AVISO or nom.lower() in dict_items_norm: return "aviso", NARANJA
        return "ok", NEUTRO_TEXTO

    LINEAS = [("Porteros", 92), ("Defensas", 74), ("Centrocampistas", 52), ("Mediapuntas / Extremos", 32), ("Delanteros", 15)]
    agrupados, por_linea = {}, {l: [] for l, _ in LINEAS}
    n_por, n_campo, n_sin_dato = 0, 0, 0

    for _, row_j in df_disp.iterrows():
        nom = nombre_bonito(row_j['Jugador'])
        estado, color = estado_jugador(nom)
        if estado is None:
            n_sin_dato += 1
            continue
        pos_low = str(row_j.get('Posicion', '')).strip().lower()
        lat_low = str(row_j.get('Lateralidad', '')).strip().lower()
        es_portero = 'porter' in pos_low
        n_por += es_portero; n_campo += (not es_portero)

        if es_portero: y, linea = 92, "Porteros"
        elif 'lateral' in pos_low or 'defensa l' in pos_low: y, linea = 70, "Defensas"
        elif 'central' in pos_low or 'defensa' in pos_low: y, linea = 78, "Defensas"
        elif 'mediapunta' in pos_low or 'interior' in pos_low: y, linea = 40, "Mediapuntas / Extremos"
        elif 'medio' in pos_low or 'centrocampista' in pos_low or 'pivote' in pos_low: y, linea = 55, "Centrocampistas"
        elif 'extremo' in pos_low or 'carrilero' in pos_low: y, linea = 25, "Mediapuntas / Extremos"
        elif 'delantero' in pos_low or 'punta' in pos_low or 'atacante' in pos_low: y, linea = 15, "Delanteros"
        else: y, linea = 55, "Centrocampistas"
        if 'izquierd' in lat_low: x = 85 if ('lateral' in pos_low or 'extremo' in pos_low) else 65
        elif 'derech' in lat_low: x = 15 if ('lateral' in pos_low or 'extremo' in pos_low) else 35
        else: x = 50

        peso_txt = "font-weight:700;" if estado != "ok" else ""
        color_txt = "white" if estado != "ok" else NEUTRO_TEXTO
        agrupados.setdefault((x, y), []).append(f"<span style='color:{color}; font-size:15px;'>●</span> "
                                                f"<span style='color:{color_txt}; {peso_txt}'>{nom}</span>")
        por_linea[linea].append((nom, estado, color))

    tarjetas_kpi([
        {"titulo": "Jugadores de campo", "valor": str(n_campo)},
        {"titulo": "Porteros disponibles", "valor": str(n_por)},
        {"titulo": "Bajas", "valor": str(len(d['bajas'])), "color": ROJO if d['bajas'] else TEXTO},
        {"titulo": "Sin wellness hoy", "valor": str(n_sin_dato), "color": NARANJA if n_sin_dato else TEXTO},
    ])

    # Lista por líneas: se ve en pantallas estrechas (o siempre, si "Vista móvil" está activada)
    html_lista = ""
    for linea, _ in LINEAS:
        jugs = por_linea[linea]
        if not jugs: continue
        orden = {"alerta": 0, "aviso": 1, "ok": 2}
        jugs = sorted(jugs, key=lambda t: (orden[t[1]], t[0]))
        filas = "".join([f"<div style='padding:4px 0; border-bottom:1px solid {BORDE}; color:{'white' if e != 'ok' else NEUTRO_TEXTO}'>"
                         f"<span style='color:{c}'>●</span> {n}</div>" for n, e, c in jugs])
        html_lista += f"<div style='margin:10px 0 4px 0; font-weight:800; color:{TEXTO}'>{linea} ({len(jugs)})</div>{filas}"
    render_html(f"<div class='{'' if movil else 'solo-movil'}'>{html_lista}</div>")

    if not movil:
      with st.container(key="solo_pc_campograma"):   # el campograma solo se dibuja en pantallas anchas
        fig_campo = go.Figure()
        lc = "rgba(255,255,255,0.25)"
        shapes = [
            dict(type="rect", x0=2, y0=2, x1=98, y1=98, line=dict(color=lc, width=2)),
            dict(type="line", x0=2, y0=50, x1=98, y1=50, line=dict(color=lc, width=2)),
            dict(type="circle", x0=40, y0=43, x1=60, y1=57, line=dict(color=lc, width=2)),
            dict(type="rect", x0=25, y0=2, x1=75, y1=18, line=dict(color=lc, width=1.5)),
            dict(type="rect", x0=25, y0=82, x1=75, y1=98, line=dict(color=lc, width=1.5)),
        ]
        anot = [dict(x=x, y=y, text="<br>".join(l), showarrow=False, align='left', font=dict(size=13, color="white"),
                     bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="rgba(255,255,255,0.15)", borderwidth=1, borderpad=6)
                for (x, y), l in agrupados.items()]
        fig_campo.update_layout(shapes=shapes, annotations=anot,
                                xaxis=dict(range=[0, 100], visible=False, fixedrange=True),
                                yaxis=dict(range=[0, 100], visible=False, fixedrange=True),
                                paper_bgcolor='rgba(15, 23, 42, 0.6)', plot_bgcolor='rgba(15, 23, 42, 0.6)',
                                height=640, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, hovermode=False)
        st.plotly_chart(fig_campo, width="stretch", config={'staticPlot': True})

st.markdown("---")
if st.button("Cerrar Sesión"):
    st.session_state['logeado'] = False
    st.rerun()
