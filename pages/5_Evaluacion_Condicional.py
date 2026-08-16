import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import base64
import requests
import io
from utils import aplicar_diseno_responsive

aplicar_diseno_responsive()

st.set_page_config(
    page_title="Evaluación Condicional - Adarve DH",
    page_icon="⚡",
    layout="wide"
)

# SELLO FIJO SIDEBAR
_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        _b64 = base64.b64encode(_f.read()).decode()
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{
            position: fixed; bottom: 20px; left: 10px; width: 260px;
            text-align: center; z-index: 999; padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
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
    div[data-testid="stHorizontalBlock"] button {
        font-size: 16px !important; font-weight: bold !important;
        border-radius: 8px !important; padding: 8px 12px !important;
    }
    .metric-card {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px; padding: 15px; text-align: center;
    }
    .podium-1 { color: #FFD700; font-weight: bold; font-size: 20px; }
    .podium-2 { color: #C0C0C0; font-weight: bold; font-size: 18px; }
    .podium-3 { color: #CD7F32; font-weight: bold; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

def aplicar_estilo_shadcn(fig):
    fig.update_layout(
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showline=False, tickfont=dict(color="#64748b", size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", griddash="solid", zeroline=False, showline=False, tickfont=dict(color="#64748b", size=11)),
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="#1e293b", font_size=13, font_family="Inter, sans-serif", font_color="#f8fafc"),
        bargap=0.25, bargroupgap=0.1
    )
    fig.update_traces(marker=dict(line=dict(width=0)), selector=dict(type='bar'))
    try: fig.update_traces(marker_cornerradius=4, selector=dict(type='bar'))
    except: pass
    return fig

SHADCN_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316', '#0ea5e9']

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.error("⚠️ Acceso no autorizado. Por favor, inicia sesión en la página principal.")
    st.stop()

RUTA_POSICIONES = os.path.join("data", "Posiciones.xlsx")
RUTA_MOVILIDAD = os.path.join("data", "EVALUACIONES", "MOVILIDAD", "MOVILIDAD.xlsx")
RUTA_REFERENCIAS_MOV = os.path.join("data", "EVALUACIONES", "MOVILIDAD", "Valores de referencia pruebas.xlsx")
RUTA_PESO = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
RUTA_VAM = os.path.join("data", "EVALUACIONES", "AEROBICO", "AEROBICO_5MIN.xlsx")
RUTA_REF_VAM = os.path.join("data", "EVALUACIONES", "AEROBICO", "Referencia por posiciones.xlsx")
DIR_FUERZA_ANALITICA = os.path.join("data", "EVALUACIONES", "FUERZA ANALITICA")
RUTA_SALTOS = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
RUTA_REF_SALTOS = os.path.join("data", "EVALUACIONES", "SALTOS", "Referencia salto por posiciones.xlsx")
RUTA_FUERZA_TS = os.path.join("data", "EVALUACIONES", "FUERZA TREN SUPERIOR", "FUERZA_TS.xlsx")
RUTA_CAMPO = os.path.join("data", "EVALUACIONES", "CAMPO", "CAMPO.xlsx")
RUTA_REF_CAMPO = os.path.join("data", "EVALUACIONES", "CAMPO", "Referencia campo por posiciones.xlsx")
URL_SHEET_DRI = "https://docs.google.com/spreadsheets/d/1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y/export?format=csv"

@st.cache_data(ttl=10)
def cargar_datos_evaluaciones():
    df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo = None, None, None, None, None, None, None, None, None, None, None, None, None
    
    if os.path.exists(RUTA_POSICIONES):
        df_pos = pd.read_excel(RUTA_POSICIONES)
        renomb_p = {}
        for c in df_pos.columns:
            c_clean = str(c).strip().lower()
            if 'jugador' in c_clean or 'nombre' in c_clean: renomb_p[c] = 'Nombre'
            elif 'posic' in c_clean: renomb_p[c] = 'Posicion'
        df_pos.rename(columns=renomb_p, inplace=True)
        if 'Nombre' in df_pos.columns: df_pos['Nombre'] = df_pos['Nombre'].astype(str).str.strip()
        if 'Posicion' in df_pos.columns: df_pos['Posicion'] = df_pos['Posicion'].astype(str).str.strip()

    if os.path.exists(RUTA_MOVILIDAD) and os.path.exists(RUTA_REFERENCIAS_MOV):
        df_mov = pd.read_excel(RUTA_MOVILIDAD)
        df_ref_mov = pd.read_excel(RUTA_REFERENCIAS_MOV)
        df_mov['Fecha_dt'] = pd.to_datetime(df_mov['Fecha'], dayfirst=True, errors='coerce')
        df_mov['Fecha'] = df_mov['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_mov['Nombre'] = df_mov['Nombre'].astype(str).str.strip()
        df_mov = df_mov.sort_values('Fecha_dt')

    if os.path.exists(RUTA_PESO):
        df_peso = pd.read_excel(RUTA_PESO)
        renombres_p = {}
        for col in df_peso.columns:
            c_clean = str(col).strip().lower()
            if 'fecha' in c_clean: renombres_p[col] = 'Fecha'
            elif 'nombre' in c_clean or 'jugador' in c_clean: renombres_p[col] = 'Nombre'
            elif 'peso' in c_clean or 'kg' in c_clean: renombres_p[col] = 'Peso'
        df_peso.rename(columns=renombres_p, inplace=True)
        df_peso['Nombre'] = df_peso['Nombre'].astype(str).str.strip()
        df_peso['Fecha_dt'] = pd.to_datetime(df_peso['Fecha'], dayfirst=True, errors='coerce')
        df_peso['Fecha'] = df_peso['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_peso = df_peso.sort_values('Fecha_dt')

    if os.path.exists(RUTA_VAM) and os.path.exists(RUTA_REF_VAM):
        df_vam = pd.read_excel(RUTA_VAM)
        df_ref_vam = pd.read_excel(RUTA_REF_VAM)
        renomb_v = {}
        for col in df_vam.columns:
            c_c = str(col).strip().lower()
            if 'fecha' in c_c: renomb_v[col] = 'Fecha'
            elif 'nombre' in c_c or 'jugador' in c_c: renomb_v[col] = 'Nombre'
            elif 'vam' in c_c: renomb_v[col] = 'VAM'
        df_vam.rename(columns=renomb_v, inplace=True)
        df_vam['Nombre'] = df_vam['Nombre'].astype(str).str.strip()
        df_vam['Fecha_dt'] = pd.to_datetime(df_vam['Fecha'], dayfirst=True, errors='coerce')
        df_vam['Fecha'] = df_vam['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_vam = df_vam.sort_values('Fecha_dt')
        
        renomb_rv = {}
        for col in df_ref_vam.columns:
            c_c = str(col).strip().lower()
            if 'posic' in c_c: renomb_rv[col] = 'Posicion'
            elif 'vam' in c_c: renomb_rv[col] = 'VAM_Ref'
        df_ref_vam.rename(columns=renomb_rv, inplace=True)
        if 'Posicion' in df_ref_vam.columns: df_ref_vam['Posicion'] = df_ref_vam['Posicion'].astype(str).str.strip()

        if df_pos is not None and 'Posicion' in df_pos.columns:
            df_vam = pd.merge(df_vam, df_pos[['Nombre', 'Posicion']], on='Nombre', how='left')

    ruta_dina_xlsx = os.path.join(DIR_FUERZA_ANALITICA, "DINAMOMETRIA_ANALITICO.xlsx")
    ruta_dina_csv = os.path.join(DIR_FUERZA_ANALITICA, "DINAMOMETRIA_ANALITICO.csv")
    archivo_encontrado = None
    if os.path.exists(ruta_dina_xlsx): archivo_encontrado = ruta_dina_xlsx
    elif os.path.exists(ruta_dina_csv): archivo_encontrado = ruta_dina_csv
    elif os.path.exists(DIR_FUERZA_ANALITICA):
        for arch in os.listdir(DIR_FUERZA_ANALITICA):
            if 'dinamometria' in arch.lower(): archivo_encontrado = os.path.join(DIR_FUERZA_ANALITICA, arch); break

    if archivo_encontrado:
        try:
            df_dina = pd.read_excel(archivo_encontrado) if archivo_encontrado.endswith(('.xlsx', '.xls')) else pd.read_csv(archivo_encontrado, sep=';', encoding='utf-8')
        except:
            df_dina = pd.read_csv(archivo_encontrado, sep=';', encoding='latin1')

    if df_dina is not None:
        df_dina.rename(columns={'Name': 'Nombre', 'Date': 'Fecha', 'Exercise': 'Exercise', 'MaxForce (raw)': 'Fmax_Abs'}, inplace=True)
        df_dina['Nombre'] = df_dina['Nombre'].astype(str).str.strip()
        df_dina['Exercise'] = df_dina['Exercise'].astype(str).str.replace(r'\\u00BA', '', regex=True).str.replace('°', '', regex=False).str.strip()
        df_dina['Fecha_dt'] = pd.to_datetime(df_dina['Fecha'], dayfirst=True, errors='coerce')
        df_dina['Fecha'] = df_dina['Fecha_dt'].dt.strftime('%d/%m/%Y')

    if os.path.exists(RUTA_SALTOS):
        df_saltos = pd.read_excel(RUTA_SALTOS)
        renomb_s = {}
        for col in df_saltos.columns:
            c_l = str(col).strip().lower()
            if 'nombre' in c_l or 'atlet' in c_l: renomb_s[col] = 'Nombre'
            elif 'tipo' in c_l: renomb_s[col] = 'Tipo'
            elif 'altura' in c_l: renomb_s[col] = 'Altura'
            elif 'fecha' in c_l: renomb_s[col] = 'Fecha_Hora'
        df_saltos.rename(columns=renomb_s, inplace=True)
        df_saltos['Nombre'] = df_saltos['Nombre'].astype(str).str.strip()
        df_saltos['Tipo'] = df_saltos['Tipo'].astype(str).str.strip()
        df_saltos['Fecha_dt'] = pd.to_datetime(df_saltos['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_saltos['Fecha'] = df_saltos['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_saltos = df_saltos.dropna(subset=['Fecha_dt']).sort_values('Fecha_dt')

        if df_pos is not None and 'Posicion' in df_pos.columns:
            df_saltos = pd.merge(df_saltos, df_pos[['Nombre', 'Posicion']], on='Nombre', how='left')

    if os.path.exists(RUTA_REF_SALTOS):
        df_ref_saltos = pd.read_excel(RUTA_REF_SALTOS)
        renomb_rs = {}
        for col in df_ref_saltos.columns:
            c_l = str(col).strip().lower()
            if 'posic' in c_l: renomb_rs[col] = 'Posicion'
            elif c_l == 'cmj': renomb_rs[col] = 'CMJ_Ref'
            elif 'right' in c_l: renomb_rs[col] = 'slCMJright_Ref'
            elif 'left' in c_l: renomb_rs[col] = 'slCMJleft_Ref'
        df_ref_saltos.rename(columns=renomb_rs, inplace=True)
        if 'Posicion' in df_ref_saltos.columns: df_ref_saltos['Posicion'] = df_ref_saltos['Posicion'].astype(str).str.strip()

    try:
        df_dri_sheet = pd.read_csv(URL_SHEET_DRI)
        renomb_dri = {}
        for col in df_dri_sheet.columns:
            c_l = str(col).strip().lower()
            if 'nombre' in c_l or 'atlet' in c_l: renomb_dri[col] = 'Nombre'
            elif c_l in ['tc', 'tiempo de contacto']: renomb_dri[col] = 'TC'
            elif 'caida' in c_l or 'caída' in c_l: renomb_dri[col] = 'Caida'
            elif 'altura' in c_l: renomb_dri[col] = 'Altura'
            elif 'fecha' in c_l: renomb_dri[col] = 'Fecha_Hora'
            elif 'tipo' in c_l: renomb_dri[col] = 'Tipo'
        df_dri_sheet.rename(columns=renomb_dri, inplace=True)
        df_dri_sheet['Nombre'] = df_dri_sheet['Nombre'].astype(str).str.strip()
        df_dri_sheet['Fecha_dt'] = pd.to_datetime(df_dri_sheet['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_dri_sheet['Fecha'] = df_dri_sheet['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_dri_sheet['TC'] = pd.to_numeric(df_dri_sheet['TC'].astype(str).str.replace(',', '.'), errors='coerce')
        df_dri_sheet['Altura'] = pd.to_numeric(df_dri_sheet['Altura'].astype(str).str.replace(',', '.'), errors='coerce')
        df_dri_sheet['Caida'] = pd.to_numeric(df_dri_sheet['Caida'].astype(str).str.replace(',', '.'), errors='coerce').fillna(50)
        df_dri_sheet['DRI'] = (df_dri_sheet['Altura'] / 100.0 + df_dri_sheet['Caida'] / 100.0) / (9.81 * (df_dri_sheet['TC'] ** 2))
        df_dri_sheet = df_dri_sheet.dropna(subset=['Fecha_dt', 'DRI']).sort_values('Fecha_dt')
    except: df_dri_sheet = None

    if os.path.exists(RUTA_FUERZA_TS):
        df_fts = pd.read_excel(RUTA_FUERZA_TS)
        renomb_fts = {}
        for col in df_fts.columns:
            c_l = str(col).strip().lower()
            if 'fecha' in c_l: renomb_fts[col] = 'Fecha'
            elif 'nombre' in c_l or 'jugador' in c_l: renomb_fts[col] = 'Nombre'
            elif 'press' in c_l or 'banca' in c_l: renomb_fts[col] = 'Press_Banca'
            elif 'dominad' in c_l: renomb_fts[col] = 'Dominada'
        df_fts.rename(columns=renomb_fts, inplace=True)
        df_fts['Nombre'] = df_fts['Nombre'].astype(str).str.strip()
        df_fts['Fecha_dt'] = pd.to_datetime(df_fts['Fecha'], dayfirst=True, errors='coerce')
        df_fts['Fecha'] = df_fts['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_fts['Press_Banca'] = pd.to_numeric(df_fts['Press_Banca'], errors='coerce')
        df_fts['Dominada'] = pd.to_numeric(df_fts['Dominada'], errors='coerce')
        df_fts = df_fts.dropna(subset=['Fecha_dt']).sort_values('Fecha_dt')

    if os.path.exists(RUTA_CAMPO):
        df_campo = pd.read_excel(RUTA_CAMPO)
        renomb_c = {}
        for col in df_campo.columns:
            c_l = str(col).strip().lower()
            if 'fecha' in c_l: renomb_c[col] = 'Fecha'
            elif 'nombre' in c_l or 'jugador' in c_l: renomb_c[col] = 'Nombre'
            elif c_l == 'v_max': renomb_c[col] = 'V_MAX'
            elif c_l == 'ac_max': renomb_c[col] = 'AC_MAX'
            elif c_l == 'dec_max': renomb_c[col] = 'DEC_MAX'
            elif 'sprint' in c_l: renomb_c[col] = 'Tecnica_Sprint'
            elif 'cod' in c_l: renomb_c[col] = 'Tecnica_COD'
        df_campo.rename(columns=renomb_c, inplace=True)
        df_campo['Nombre'] = df_campo['Nombre'].astype(str).str.strip()
        df_campo['Fecha_dt'] = pd.to_datetime(df_campo['Fecha'], dayfirst=True, errors='coerce')
        df_campo['Fecha'] = df_campo['Fecha_dt'].dt.strftime('%d/%m/%Y')
        for num_col in ['V_MAX', 'AC_MAX', 'DEC_MAX', 'Tecnica_Sprint', 'Tecnica_COD']:
            if num_col in df_campo.columns:
                df_campo[num_col] = pd.to_numeric(df_campo[num_col].astype(str).str.replace(',', '.'), errors='coerce')
        df_campo = df_campo.dropna(subset=['Fecha_dt']).sort_values('Fecha_dt')
        if df_pos is not None and 'Posicion' in df_pos.columns:
            df_campo = pd.merge(df_campo, df_pos[['Nombre', 'Posicion']], on='Nombre', how='left')

    if os.path.exists(RUTA_REF_CAMPO):
        df_ref_campo = pd.read_excel(RUTA_REF_CAMPO)
        renomb_rc = {}
        for col in df_ref_campo.columns:
            c_clean = str(col).strip().lower()
            if 'posic' in c_clean: renomb_rc[col] = 'Posicion'
            elif c_clean.startswith('vmax') or 'v_max' in c_clean or 'vmax' in c_clean: renomb_rc[col] = 'V_MAX_Ref'
            elif c_clean.startswith('acmax') or 'ac_max' in c_clean or 'acmax' in c_clean: renomb_rc[col] = 'AC_MAX_Ref'
            elif c_clean.startswith('decmax') or 'dec_max' in c_clean or 'decmax' in c_clean: renomb_rc[col] = 'DEC_MAX_Ref'
        df_ref_campo.rename(columns=renomb_rc, inplace=True)
        if 'Posicion' in df_ref_campo.columns: df_ref_campo['Posicion'] = df_ref_campo['Posicion'].astype(str).str.strip()

    return df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo

df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo = cargar_datos_evaluaciones()

st.title("EVALUACIÓN CONDICIONAL DE PLANTILLA")
st.markdown("---")

opciones_menu = ["🩺 Movilidad", "⚖️ Peso", "🫁 VAM / Aeróbico", "⚙️ Dinamometría", "🚀 Saltos (CMJ)", "🏋️ Tren Superior", "⚡ Velocidad & COD", "🏆 Ranking Global"]

if 'pestaña_activa' not in st.session_state:
    st.session_state['pestaña_activa'] = "🏆 Ranking Global"

cols_nav = st.columns(len(opciones_menu))
for i, opcion in enumerate(opciones_menu):
    with cols_nav[i]:
        es_activa = st.session_state['pestaña_activa'] == opcion
        tipo_boton = "primary" if es_activa else "secondary"
        if st.button(opcion, key=f"nav_btn_{i}", use_container_width=True, type=tipo_boton):
            st.session_state['pestaña_activa'] = opcion
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
pest_sel = st.session_state['pestaña_activa']

# MOVILIDAD (SIN LUMBAR)
if pest_sel == "🩺 Movilidad":
    if df_mov is None or df_ref_mov is None:
        st.error("❌ No se encontraron los archivos de movilidad.")
    else:
        ultima_fecha_mov = df_mov['Fecha'].iloc[-1]
        df_fecha_mov = df_mov[df_mov['Fecha'] == ultima_fecha_mov].copy()
        
        dict_alertas = {}
        for idx, row in df_fecha_mov.iterrows():
            nombre = row['Nombre']
            alertas_jugador = []
            
            df_d, df_i = row['DORSIFLEX_D'], row['DORSIFLEX_I']
            if df_d < 12 or df_i < 12: alertas_jugador.append("Dorsiflexión Tobillo")
            elif abs(df_d - df_i) >= 3: alertas_jugador.append("Asimetría Tobillo")
                
            rot_d, rot_i = row['ROT_INT_D'], row['ROT_INT_I']
            if rot_d < 35 or rot_i < 35: alertas_jugador.append("Rot. Interna Cadera")
            elif abs(rot_d - rot_i) >= 5: alertas_jugador.append("Asimetría Rot. Cadera")

            flx_d, flx_i = row['FLEX_CAD_D'], row['FLEX_CAD_I']
            if flx_d < 45 or flx_i < 45: alertas_jugador.append("Flexión Cadera")
            elif abs(flx_d - flx_i) >= 5: alertas_jugador.append("Asimetría Flex. Cadera")

            if alertas_jugador: dict_alertas[nombre] = alertas_jugador

        col_m1, col_m2 = st.columns(2)
        with col_m1: st.metric("Jugadores con Déficit/Asimetría", f"{len(dict_alertas)} / {len(df_fecha_mov)}")
        with col_m2: st.metric("Porcentaje Vestuario Óptimo", f"{((len(df_fecha_mov) - len(dict_alertas)) / len(df_fecha_mov) * 100):.0f}%")

        if dict_alertas:
            col_a1, col_a2 = st.columns(2)
            items = list(dict_alertas.items())
            mitad = (len(items) + 1) // 2
            with col_a1:
                for nom, defs in items[:mitad]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #ef4444;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_a2:
                for nom, defs in items[mitad:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #ef4444;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else: st.success("✅ Todo el vestuario se encuentra en rangos óptimos.")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        bloque_seleccionado = st.selectbox("Selec. Articulación para gráfico:", ["Dorsiflexión Tobillo", "Rotación Interna Cadera", "Flexión Cadera"])

        if bloque_seleccionado == "Dorsiflexión Tobillo": col_d, col_i, val_verde, unidad = 'DORSIFLEX_D', 'DORSIFLEX_I', 12, 'cm'
        elif bloque_seleccionado == "Rotación Interna Cadera": col_d, col_i, val_verde, unidad = 'ROT_INT_D', 'ROT_INT_I', 35, '°'
        else: col_d, col_i, val_verde, unidad = 'FLEX_CAD_D', 'FLEX_CAD_I', 45, '°'

        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(x=df_fecha_mov['Nombre'], y=df_fecha_mov[col_d], name='Derecha (D)', marker_color='#3b82f6', text=df_fecha_mov[col_d], textposition='outside', textfont=dict(color='white', size=11)))
        fig_barras.add_trace(go.Bar(x=df_fecha_mov['Nombre'], y=df_fecha_mov[col_i], name='Izquierda (I)', marker_color='#10b981', text=df_fecha_mov[col_i], textposition='outside', textfont=dict(color='white', size=11)))
        max_y = max(df_fecha_mov[col_d].max(), df_fecha_mov[col_i].max())

        fig_barras.add_shape(type="line", x0=-0.5, x1=len(df_fecha_mov)-0.5, y0=val_verde, y1=val_verde, line=dict(color="#22c55e", width=2, dash="dash"))
        fig_barras = aplicar_estilo_shadcn(fig_barras)
        fig_barras.update_layout(title=f"Comparativa Bilateral: {bloque_seleccionado} ({ultima_fecha_mov})", barmode='group', xaxis=dict(tickangle=-45), yaxis=dict(title=f"Valor ({unidad})", range=[0, max(max_y + 5, val_verde + 5)]), height=460, margin=dict(l=20, r=20, t=50, b=100))
        st.plotly_chart(fig_barras, use_container_width=True)

# RANKING GLOBAL (SIN LUMBAR EN MOVILIDAD)
elif pest_sel == "🏆 Ranking Global":
    if df_pos is None or df_pos.empty:
        st.warning("⚠️ No se encontró la lista de plantilla.")
    else:
        conjunto_fechas_dt = set()
        for df_t in [df_mov, df_vam, df_dina, df_saltos, df_dri_sheet, df_fts, df_campo]:
            if df_t is not None and 'Fecha_dt' in df_t.columns:
                conjunto_fechas_dt.update(df_t['Fecha_dt'].dropna().unique())

        fechas_unicas_dt = sorted(list(conjunto_fechas_dt))

        if not fechas_unicas_dt:
            st.warning("⚠️ No hay fechas registradas.")
        else:
            dict_fechas_str = {f_dt: pd.to_datetime(f_dt).strftime('%d/%m/%Y') for f_dt in fechas_unicas_dt}
            col_filt_f, _ = st.columns([2, 2])
            with col_filt_f:
                f_sel_dt = st.selectbox("📅 Selecciona Fecha para el Ranking:", options=fechas_unicas_dt, index=len(fechas_unicas_dt)-1, format_func=lambda x: dict_fechas_str[x])

            f_sel_str = dict_fechas_str[f_sel_dt]
            df_rank_base = df_pos[['Nombre', 'Posicion']].copy()

            def get_metric_hasta_fecha(df_origen, col_metric, agg_func='mean'):
                if df_origen is not None and not df_origen.empty and col_metric in df_origen.columns:
                    df_sub = df_origen[df_origen['Fecha_dt'] <= f_sel_dt].copy()
                    if not df_sub.empty:
                        ult_f_sub = df_sub['Fecha_dt'].max()
                        df_u = df_sub[df_sub['Fecha_dt'] == ult_f_sub]
                        return df_u.groupby('Nombre', as_index=False)[col_metric].agg(agg_func)
                return None

            if df_mov is not None and not df_mov.empty:
                df_m_sub = df_mov[df_mov['Fecha_dt'] <= f_sel_dt]
                if not df_m_sub.empty:
                    ult_f_m = df_m_sub['Fecha_dt'].max()
                    df_m_u = df_m_sub[df_m_sub['Fecha_dt'] == ult_f_m].copy()
                    mov_cols = [c for c in ['DORSIFLEX_D', 'DORSIFLEX_I', 'ROT_INT_D', 'ROT_INT_I', 'FLEX_CAD_D', 'FLEX_CAD_I'] if c in df_m_u.columns]
                    df_m_u['Movilidad_Score'] = df_m_u[mov_cols].mean(axis=1)
                    df_rank_base = pd.merge(df_rank_base, df_m_u[['Nombre', 'Movilidad_Score']], on='Nombre', how='left')

            df_v_met = get_metric_hasta_fecha(df_vam, 'VAM')
            if df_v_met is not None: df_rank_base = pd.merge(df_rank_base, df_v_met[['Nombre', 'VAM']], on='Nombre', how='left')

            dict_pesos = {}
            if df_peso is not None and not df_peso.empty:
                for nom in df_peso['Nombre'].unique():
                    df_p_j = df_peso[df_peso['Nombre'] == nom].sort_values('Fecha_dt')
                    dict_pesos[nom] = float(df_p_j.iloc[-1]['Peso'])

            if df_dina is not None and not df_dina.empty:
                df_d_sub = df_dina[df_dina['Fecha_dt'] <= f_sel_dt].copy()
                if not df_d_sub.empty:
                    ult_f_d = df_d_sub['Fecha_dt'].max()
                    df_d_u = df_d_sub[df_d_sub['Fecha_dt'] == ult_f_d].copy()
                    df_d_u['Peso_Jug'] = df_d_u['Nombre'].map(dict_pesos)
                    df_d_u['Fmax_Rel'] = df_d_u['Fmax_Abs'] / df_d_u['Peso_Jug']
                    df_d_agg = df_d_u.groupby('Nombre', as_index=False)['Fmax_Rel'].mean()
                    df_rank_base = pd.merge(df_rank_base, df_d_agg[['Nombre', 'Fmax_Rel']], on='Nombre', how='left')

            if df_saltos is not None and not df_saltos.empty:
                df_cmj_sub = df_saltos[(df_saltos['Tipo'].str.upper() == 'CMJ') & (df_saltos['Fecha_dt'] <= f_sel_dt)]
                if not df_cmj_sub.empty:
                    ult_f_s = df_cmj_sub['Fecha_dt'].max()
                    df_s_u = df_cmj_sub[df_cmj_sub['Fecha_dt'] == ult_f_s].groupby('Nombre', as_index=False)['Altura'].mean()
                    df_s_u.rename(columns={'Altura': 'CMJ_Altura'}, inplace=True)
                    df_rank_base = pd.merge(df_rank_base, df_s_u[['Nombre', 'CMJ_Altura']], on='Nombre', how='left')

            df_dri_met = get_metric_hasta_fecha(df_dri_sheet, 'DRI')
            if df_dri_met is not None: df_rank_base = pd.merge(df_rank_base, df_dri_met[['Nombre', 'DRI']], on='Nombre', how='left')

            if df_fts is not None and not df_fts.empty:
                df_ts_sub = df_fts[df_fts['Fecha_dt'] <= f_sel_dt].copy()
                if not df_ts_sub.empty:
                    ult_f_ts = df_ts_sub['Fecha_dt'].max()
                    df_ts_u = df_ts_sub[df_ts_sub['Fecha_dt'] == ult_f_ts].copy()
                    df_ts_u['Tren_Superior_Reps'] = df_ts_u['Press_Banca'].fillna(0) + df_ts_u['Dominada'].fillna(0)
                    df_rank_base = pd.merge(df_rank_base, df_ts_u[['Nombre', 'Tren_Superior_Reps']], on='Nombre', how='left')

            if df_campo is not None and not df_campo.empty:
                df_c_sub = df_campo[df_campo['Fecha_dt'] <= f_sel_dt]
                if not df_c_sub.empty:
                    ult_f_c = df_c_sub['Fecha_dt'].max()
                    df_c_u = df_c_sub[df_c_sub['Fecha_dt'] == ult_f_c]
                    df_rank_base = pd.merge(df_rank_base, df_c_u[['Nombre', 'V_MAX', 'AC_MAX']], on='Nombre', how='left')

            columnas_pruebas = {
                'Movilidad_Score': ('Movilidad', True),
                'VAM': ('VAM Aeróbico', True),
                'Fmax_Rel': ('Dinamometría', True),
                'CMJ_Altura': ('Salto CMJ', True),
                'DRI': ('DRI Drop Jump', True),
                'Tren_Superior_Reps': ('Tren Superior', True),
                'V_MAX': ('Velocidad VMAX', True),
                'AC_MAX': ('Aceleración ACMAX', True)
            }

            cols_puntos = []
            for col_raw, (col_nombre_clean, mayor_es_mejor) in columnas_pruebas.items():
                if col_raw in df_rank_base.columns:
                    col_rank_name = f"P_{col_nombre_clean}"
                    df_rank_base[col_rank_name] = df_rank_base[col_raw].rank(ascending=not mayor_es_mejor, method='min', na_option='bottom').astype(int)
                    cols_puntos.append(col_rank_name)

            df_rank_base['PUNTOS_TOTALES'] = df_rank_base[cols_puntos].sum(axis=1)
            df_rank_base = df_rank_base.sort_values('PUNTOS_TOTALES', ascending=True).reset_index(drop=True)
            df_rank_base['POSICION_GLOBAL'] = df_rank_base.index + 1

            st.markdown("<br>", unsafe_allow_html=True)
            c_p1, c_p2, c_p3 = st.columns(3)

            if len(df_rank_base) >= 1:
                j1 = df_rank_base.iloc[0]
                with c_p1: st.markdown(f'<div class="metric-card"><div class="podium-1">🥇 1º PUESTO</div><h2>{j1["Nombre"]}</h2><p style="color:#2ECC71; font-weight:bold;">{j1["PUNTOS_TOTALES"]} Pts</p><small>{j1["Posicion"]}</small></div>', unsafe_allow_html=True)
            if len(df_rank_base) >= 2:
                j2 = df_rank_base.iloc[1]
                with c_p2: st.markdown(f'<div class="metric-card"><div class="podium-2">🥈 2º PUESTO</div><h2>{j2["Nombre"]}</h2><p style="color:#00A8E8; font-weight:bold;">{j2["PUNTOS_TOTALES"]} Pts</p><small>{j2["Posicion"]}</small></div>', unsafe_allow_html=True)
            if len(df_rank_base) >= 3:
                j3 = df_rank_base.iloc[2]
                with c_p3: st.markdown(f'<div class="metric-card"><div class="podium-3">🥉 3º PUESTO</div><h2>{j3["Nombre"]}</h2><p style="color:#FF9F1C; font-weight:bold;">{j3["PUNTOS_TOTALES"]} Pts</p><small>{j3["Posicion"]}</small></div>', unsafe_allow_html=True)

            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown(f"### Clasificación Completa ({f_sel_str})")

            df_tabla = df_rank_base.copy()
            df_tabla['POSICION_GLOBAL'] = df_tabla['POSICION_GLOBAL'].apply(lambda pos: f"🥇 1º" if pos==1 else (f"🥈 2º" if pos==2 else (f"🥉 3º" if pos==3 else f"{pos}º")))

            if 'Movilidad_Score' in df_tabla.columns: df_tabla['Movilidad_Score'] = df_tabla['Movilidad_Score'].round(1)
            if 'VAM' in df_tabla.columns: df_tabla['VAM'] = df_tabla['VAM'].round(2)
            if 'Fmax_Rel' in df_tabla.columns: df_tabla['Fmax_Rel'] = df_tabla['Fmax_Rel'].round(2)
            if 'CMJ_Altura' in df_tabla.columns: df_tabla['CMJ_Altura'] = df_tabla['CMJ_Altura'].round(1)
            if 'DRI' in df_tabla.columns: df_tabla['DRI'] = df_tabla['DRI'].round(2)
            if 'Tren_Superior_Reps' in df_tabla.columns: df_tabla['Tren_Superior_Reps'] = df_tabla['Tren_Superior_Reps'].fillna(0).round(0).astype(int)
            if 'V_MAX' in df_tabla.columns: df_tabla['V_MAX'] = df_tabla['V_MAX'].round(1)
            if 'AC_MAX' in df_tabla.columns: df_tabla['AC_MAX'] = df_tabla['AC_MAX'].round(2)

            cols_mostrar = {
                'POSICION_GLOBAL': 'Posición', 'Nombre': 'Jugador', 'PUNTOS_TOTALES': '🏆 Puntos Totales',
                'Movilidad_Score': '🩺 Movilidad', 'VAM': '🫁 VAM', 'Fmax_Rel': '⚙️ Dinamometría',
                'CMJ_Altura': '🚀 CMJ', 'DRI': '⚡ DRI', 'Tren_Superior_Reps': '🏋️ Tren Sup.',
                'V_MAX': '⚡ V_MAX', 'AC_MAX': '⚡ AC_MAX'
            }

            cols_existentes = [c for c in cols_mostrar.keys() if c in df_tabla.columns]
            st.dataframe(df_tabla[cols_existentes].rename(columns=cols_mostrar), use_container_width=True, hide_index=True)