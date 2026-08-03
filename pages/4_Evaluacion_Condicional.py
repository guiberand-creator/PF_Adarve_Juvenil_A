import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from utils import aplicar_diseno_responsive

# Al principio de la página
aplicar_diseno_responsive()

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS (ÚNICA)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Evaluación Condicional - Adarve DH",
    page_icon="⚡",
    layout="wide"
)

# SELLO FIJO AL PIE DEL SIDEBAR
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

st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] button {
        font-size: 16px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
    }
    .metric-card {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .podium-1 { color: #FFD700; font-weight: bold; font-size: 20px; }
    .podium-2 { color: #C0C0C0; font-weight: bold; font-size: 18px; }
    .podium-3 { color: #CD7F32; font-weight: bold; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONTROL DE ACCESO
# -----------------------------------------------------------------------------
if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.error("⚠️ Acceso no autorizado. Por favor, inicia sesión en la página principal.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. CARGA DE DATOS LOCALES Y GOOGLE SHEETS
# -----------------------------------------------------------------------------
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

COLOR_ADARVE_GRANATE = "#800020"
COLOR_ADARVE_BORDER = "#B22222"

@st.cache_data(ttl=10)
def cargar_datos_evaluaciones():
    df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo = None, None, None, None, None, None, None, None, None, None, None, None, None
    
    # 0. Posiciones.xlsx
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

    # 1. Movilidad
    if os.path.exists(RUTA_MOVILIDAD) and os.path.exists(RUTA_REFERENCIAS_MOV):
        df_mov = pd.read_excel(RUTA_MOVILIDAD)
        df_ref_mov = pd.read_excel(RUTA_REFERENCIAS_MOV)
        df_mov['Fecha_dt'] = pd.to_datetime(df_mov['Fecha'], dayfirst=True, errors='coerce')
        df_mov['Fecha'] = df_mov['Fecha_dt'].dt.strftime('%d/%m/%Y')
        df_mov['Nombre'] = df_mov['Nombre'].astype(str).str.strip()
        df_mov = df_mov.sort_values('Fecha_dt')
        
    # 2. Peso
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

    # 3. VAM Aeróbico
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

    # 4. Dinamometría
    ruta_dina_xlsx = os.path.join(DIR_FUERZA_ANALITICA, "DINAMOMETRIA_ANALITICO.xlsx")
    ruta_dina_csv = os.path.join(DIR_FUERZA_ANALITICA, "DINAMOMETRIA_ANALITICO.csv")
    archivo_encontrado = None
    if os.path.exists(ruta_dina_xlsx): archivo_encontrado = ruta_dina_xlsx
    elif os.path.exists(ruta_dina_csv): archivo_encontrado = ruta_dina_csv
    else:
        if os.path.exists(DIR_FUERZA_ANALITICA):
            for arch in os.listdir(DIR_FUERZA_ANALITICA):
                if 'dinamometria' in arch.lower():
                    archivo_encontrado = os.path.join(DIR_FUERZA_ANALITICA, arch)
                    break

    if archivo_encontrado:
        if archivo_encontrado.endswith('.xlsx') or archivo_encontrado.endswith('.xls'):
            df_dina = pd.read_excel(archivo_encontrado)
        else:
            try:
                df_dina = pd.read_csv(archivo_encontrado, sep=';', encoding='utf-8')
                if len(df_dina.columns) <= 1: df_dina = pd.read_csv(archivo_encontrado, sep=',', encoding='utf-8')
            except Exception:
                df_dina = pd.read_csv(archivo_encontrado, sep=';', encoding='latin1')

    if df_dina is not None:
        renomb_d = {
            'Name': 'Nombre',
            'Date': 'Fecha',
            'Exercise': 'Exercise',
            'MaxForce (raw)': 'Fmax_Abs',
            'RFD_FITTED_BEST_AVG_RFD_IN_X_MS_150_-1': 'RFD_150'
        }
        df_dina.rename(columns=renomb_d, inplace=True)
        df_dina['Nombre'] = df_dina['Nombre'].astype(str).str.strip()
        df_dina['Exercise'] = df_dina['Exercise'].astype(str).str.strip()
        df_dina['Fecha_dt'] = pd.to_datetime(df_dina['Fecha'], dayfirst=True, errors='coerce')
        df_dina['Fecha'] = df_dina['Fecha_dt'].dt.strftime('%d/%m/%Y')

    # 5. Saltos CMJ
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
        if 'Posicion' in df_ref_saltos.columns:
            df_ref_saltos['Posicion'] = df_ref_saltos['Posicion'].astype(str).str.strip()

    # 6. Drop Jump / DRI
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

        g = 9.81
        h_m = df_dri_sheet['Altura'] / 100.0
        h_drop_m = df_dri_sheet['Caida'] / 100.0
        tc_s = df_dri_sheet['TC']

        df_dri_sheet['DRI'] = (h_m + h_drop_m) / (g * (tc_s ** 2))
        df_dri_sheet = df_dri_sheet.dropna(subset=['Fecha_dt', 'DRI']).sort_values('Fecha_dt')
    except Exception:
        df_dri_sheet = None

    # 7. Fuerza Tren Superior
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

    # 8. Velocidad & Campo
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

    # Referencias Campo
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
        if 'Posicion' in df_ref_campo.columns:
            df_ref_campo['Posicion'] = df_ref_campo['Posicion'].astype(str).str.strip()
            
        for num_c in ['V_MAX_Ref', 'AC_MAX_Ref', 'DEC_MAX_Ref']:
            if num_c in df_ref_campo.columns:
                df_ref_campo[num_c] = pd.to_numeric(
                    df_ref_campo[num_c].astype(str).str.replace(',', '.'), 
                    errors='coerce'
                )

    return df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo

df_pos, df_mov, df_ref_mov, df_peso, df_vam, df_ref_vam, df_dina, df_saltos, df_ref_saltos, df_dri_sheet, df_fts, df_campo, df_ref_campo = cargar_datos_evaluaciones()

# -----------------------------------------------------------------------------
# 4. CABECERA
# -----------------------------------------------------------------------------
st.title("EVALUACIÓN CONDICIONAL DE PLANTILLA")
st.markdown("---")

# -----------------------------------------------------------------------------
# 5. PESTAÑAS NAVEGABLES
# -----------------------------------------------------------------------------
opciones_menu = [
    "🩺 Movilidad", 
    "⚖️ Peso", 
    "🫁 VAM / Aeróbico", 
    "⚙️ Dinamometría", 
    "🚀 Saltos (CMJ)", 
    "🏋️ Tren Superior", 
    "⚡ Velocidad & COD",
    "🏆 Ranking Global"
]

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

# =============================================================================
# ÁREA 1: MOVILIDAD
# =============================================================================
if pest_sel == "🩺 Movilidad":
    if df_mov is None or df_ref_mov is None:
        st.error("❌ No se encontraron los archivos de movilidad en 'data/EVALUACIONES/MOVILIDAD/'.")
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

            if row['LUMBAR'] < 80: alertas_jugador.append("Movilidad Lumbar")
            if alertas_jugador: dict_alertas[nombre] = alertas_jugador

        col_m1, col_m2 = st.columns(2)
        with col_m1: st.metric("Jugadores con algún Déficit/Asimetría", f"{len(dict_alertas)} / {len(df_fecha_mov)}")
        with col_m2: st.metric("Porcentaje del Vestuario Óptimo", f"{((len(df_fecha_mov) - len(dict_alertas)) / len(df_fecha_mov) * 100):.0f}%")

        if dict_alertas:
            col_a1, col_a2 = st.columns(2)
            items = list(dict_alertas.items())
            mitad = (len(items) + 1) // 2
            with col_a1:
                for nom, defs in items[:mitad]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_a2:
                for nom, defs in items[mitad:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else: st.success("✅ ¡Excelente! Todo el vestuario se encuentra en rangos óptimos.")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        bloque_seleccionado = st.selectbox("Selec. Articulación para inspeccionar en gráfico:", ["Dorsiflexión Tobillo", "Rotación Interna Cadera", "Flexión Cadera", "Movilidad Lumbar"])

        if bloque_seleccionado == "Dorsiflexión Tobillo": col_d, col_i, val_verde, unidad = 'DORSIFLEX_D', 'DORSIFLEX_I', 12, 'cm'
        elif bloque_seleccionado == "Rotación Interna Cadera": col_d, col_i, val_verde, unidad = 'ROT_INT_D', 'ROT_INT_I', 35, '°'
        elif bloque_seleccionado == "Flexión Cadera": col_d, col_i, val_verde, unidad = 'FLEX_CAD_D', 'FLEX_CAD_I', 45, '°'
        else: col_d, col_i, val_verde, unidad = 'LUMBAR', None, 80, '°'

        fig_barras = go.Figure()
        if col_i is not None:
            fig_barras.add_trace(go.Bar(x=df_fecha_mov['Nombre'], y=df_fecha_mov[col_d], name='Derecha (D)', marker_color='#00A8E8', text=df_fecha_mov[col_d], textposition='outside'))
            fig_barras.add_trace(go.Bar(x=df_fecha_mov['Nombre'], y=df_fecha_mov[col_i], name='Izquierda (I)', marker_color='#FF9F1C', text=df_fecha_mov[col_i], textposition='outside'))
            max_y = max(df_fecha_mov[col_d].max(), df_fecha_mov[col_i].max())
        else:
            fig_barras.add_trace(go.Bar(x=df_fecha_mov['Nombre'], y=df_fecha_mov[col_d], name='Lumbar', marker_color='#2ECC71', text=df_fecha_mov[col_d], textposition='outside'))
            max_y = df_fecha_mov[col_d].max()

        fig_barras.add_shape(type="line", x0=-0.5, x1=len(df_fecha_mov)-0.5, y0=val_verde, y1=val_verde, line=dict(color="#2ECC71", width=3, dash="dash"))
        fig_barras.update_layout(title=f"Comparativa Bilateral: {bloque_seleccionado} ({ultima_fecha_mov})", barmode='group', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(tickangle=-45), yaxis=dict(title=f"Valor ({unidad})", range=[0, max(max_y + 5, val_verde + 5)]), height=460, margin=dict(l=20, r=20, t=50, b=100))
        st.plotly_chart(fig_barras, use_container_width=True)

# =============================================================================
# ÁREA 2: PESO
# =============================================================================
elif pest_sel == "⚖️ Peso":
    if df_peso is None or df_peso.empty:
        st.warning("⚠️ No se encontró el archivo 'PESO.xlsx' dentro de 'data/EVALUACIONES/PESO/'.")
    else:
        df_p_equipo = df_peso.sort_values(['Nombre', 'Fecha_dt']).copy()
        df_p_equipo['Peso_Ant'] = df_p_equipo.groupby('Nombre')['Peso'].shift(1)
        df_p_equipo['Var_Pct'] = ((df_p_equipo['Peso'] - df_p_equipo['Peso_Ant']) / df_p_equipo['Peso_Ant']) * 100
        fechas_ordenadas = sorted(list(df_p_equipo['Fecha'].unique()))
        colores_fechas = ['#FF9F1C', '#00A8E8', '#2ECC71', '#9B59B6', '#E74C3C', '#F1C40F']
        
        fig_p_equipo = go.Figure()
        for i, f in enumerate(fechas_ordenadas):
            df_f = df_p_equipo[df_p_equipo['Fecha'] == f]
            etiquetas_equipo = [f"<b>{row['Peso']:.1f} kg</b>" if pd.isna(row['Var_Pct']) else f"<b>{row['Peso']:.1f} kg</b><br><i>{'+' if row['Var_Pct']>0 else ''}{row['Var_Pct']:.1f}%</i>" for _, row in df_f.iterrows()]
            fig_p_equipo.add_trace(go.Bar(x=df_f['Nombre'], y=df_f['Peso'], name=f"Fecha {f}", text=etiquetas_equipo, textposition='outside', marker_color=colores_fechas[i % len(colores_fechas)]))

        fig_p_equipo.update_layout(title="Evolución del Peso por Jugador en Todas las Fechas Registradas", barmode='group', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(tickangle=-45), yaxis=dict(title="Peso (kg)", range=[max(0, df_p_equipo['Peso'].min() - 5), df_p_equipo['Peso'].max() + 7]), height=500, margin=dict(l=20, r=20, t=50, b=110))
        st.plotly_chart(fig_p_equipo, use_container_width=True)

# =============================================================================
# ÁREA 3: VAM / AERÓBICO
# =============================================================================
elif pest_sel == "🫁 VAM / Aeróbico":
    if df_vam is None or df_vam.empty:
        st.warning("⚠️ No se encontraron los archivos de VAM en 'data/EVALUACIONES/AEROBICO/'.")
    else:
        df_v_valid = df_vam[df_vam['VAM'] > 0].copy()
        
        ult_fecha_vam = df_v_valid['Fecha_dt'].max()
        ult_fecha_vam_str = df_v_valid[df_v_valid['Fecha_dt'] == ult_fecha_vam]['Fecha'].iloc[0]
        df_v_ult = df_v_valid[df_v_valid['Fecha_dt'] == ult_fecha_vam].copy()

        dict_alertas_vam = {}
        for _, r_j in df_v_ult.iterrows():
            nom_j = r_j['Nombre']
            pos_j = r_j['Posicion']
            vam_val = r_j['VAM']

            if df_ref_vam is not None and not df_ref_vam.empty:
                r_ref = df_ref_vam[df_ref_vam['Posicion'] == pos_j]
                if not r_ref.empty:
                    ref_val = r_ref.iloc[0]['VAM_Ref']
                    if pd.notna(vam_val) and pd.notna(ref_val) and vam_val < ref_val:
                        dict_alertas_vam[nom_j] = ["Trabajo Aeróbico"]

        c_v1, c_v2 = st.columns(2)
        with c_v1: 
            st.metric("Jugadores con Prescripción de Trabajo Individual", f"{len(dict_alertas_vam)} / {len(df_v_ult)}")
        with c_v2: 
            pct_optimo = ((len(df_v_ult) - len(dict_alertas_vam)) / len(df_v_ult) * 100) if len(df_v_ult) > 0 else 100
            st.metric("Porcentaje del Vestuario en Objetivo", f"{pct_optimo:.0f}%")

        if dict_alertas_vam:
            col_va1, col_va2 = st.columns(2)
            items_v = list(dict_alertas_vam.items())
            mitad_v = (len(items_v) + 1) // 2
            
            with col_va1:
                for nom, defs in items_v[:mitad_v]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_va2:
                for nom, defs in items_v[mitad_v:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else:
            st.success("✅ ¡Excelente! Todo el vestuario cumple o supera la VAM de referencia para su posición.")

        st.markdown("<br><hr>", unsafe_allow_html=True)

        posiciones_unicas = sorted([p for p in df_v_valid['Posicion'].dropna().unique() if str(p).strip() not in ['nan', '']]) if 'Posicion' in df_v_valid.columns else []
        colores_fechas = ['#2ECC71', '#00A8E8', '#FF9F1C', '#9B59B6', '#E74C3C']

        opciones_pos = ["Todas las Demarcaciones"] + posiciones_unicas
        col_filtro, col_vacio = st.columns([1, 2])
        with col_filtro:
            pos_seleccionada = st.selectbox("⚽ Filtrar por Demarcación:", opciones_pos)

        pos_a_mostrar = posiciones_unicas if pos_seleccionada == "Todas las Demarcaciones" else [pos_seleccionada]

        st.markdown("<br>", unsafe_allow_html=True)

        for i in range(0, len(pos_a_mostrar), 2):
            col_g1, col_g2 = st.columns(2) if len(pos_a_mostrar) > 1 else (st.container(), None)
            columnas_iter = [col_g1, col_g2] if len(pos_a_mostrar) > 1 else [col_g1]

            for idx_c, col_curr in enumerate(columnas_iter):
                if col_curr is not None and (i + idx_c < len(pos_a_mostrar)):
                    pos_curr = pos_a_mostrar[i + idx_c]
                    with col_curr:
                        df_p = df_v_valid[df_v_valid['Posicion'] == pos_curr].sort_values(['Nombre', 'Fecha_dt']).copy()
                        df_p['VAM_Ant'] = df_p.groupby('Nombre')['VAM'].shift(1)
                        df_p['Var_Pct'] = ((df_p['VAM'] - df_p['VAM_Ant']) / df_p['VAM_Ant']) * 100
                        fechas_p = sorted(list(df_p['Fecha'].unique()))
                        fig_p = go.Figure()
                        
                        for idx_f, f in enumerate(fechas_p):
                            df_f = df_p[df_p['Fecha'] == f]
                            etiquetas = [f"<b>{r['VAM']:.2f}</b>" if pd.isna(r['Var_Pct']) else f"<b>{r['VAM']:.2f}</b><br><i>{'+' if r['Var_Pct']>0 else ''}{r['Var_Pct']:.1f}%</i>" for _, r in df_f.iterrows()]
                            fig_p.add_trace(go.Bar(
                                x=df_f['Nombre'], 
                                y=df_f['VAM'], 
                                name=f"Fecha {f}", 
                                text=etiquetas, 
                                textposition='outside', 
                                marker_color=colores_fechas[idx_f % len(colores_fechas)]
                            ))

                        ref_val = None
                        if df_ref_vam is not None:
                            row_r = df_ref_vam[df_ref_vam['Posicion'] == pos_curr]
                            if not row_r.empty:
                                ref_val = row_r.iloc[0]['VAM_Ref']
                                fig_p.add_shape(
                                    type="line", 
                                    x0=-0.5, 
                                    x1=len(df_p['Nombre'].unique())-0.5, 
                                    y0=ref_val, 
                                    y1=ref_val, 
                                    line=dict(color="#E74C3C", width=3, dash="dash")
                                )

                        fig_p.update_layout(
                            title=f"⚽ Demarcación: {pos_curr}", 
                            barmode='group', 
                            template="plotly_dark", 
                            paper_bgcolor='rgba(0,0,0,0)', 
                            plot_bgcolor='rgba(0,0,0,0)', 
                            xaxis=dict(tickangle=-45), 
                            yaxis=dict(title="VAM (km/h)", range=[0, max(df_p['VAM'].max() if not df_p.empty else 20, (ref_val or 0)) + 3]), 
                            height=420, 
                            margin=dict(l=20, r=20, t=50, b=90), 
                            showlegend=True
                        )
                        st.plotly_chart(fig_p, use_container_width=True)

# =============================================================================
# ÁREA 4: DINAMOMETRÍA
# =============================================================================
elif pest_sel == "⚙️ Dinamometría":
    
    if df_dina is None or df_dina.empty:
        st.warning("⚠️ No se encontró el archivo 'DINAMOMETRIA_ANALITICO.xlsx' en 'data/EVALUACIONES/FUERZA ANALITICA/'.")
    else:
        dict_pesos = {}
        if df_peso is not None and not df_peso.empty:
            for nom in df_peso['Nombre'].unique():
                df_p_j = df_peso[df_peso['Nombre'] == nom].sort_values('Fecha_dt')
                dict_pesos[nom] = float(df_p_j.iloc[-1]['Peso'])

        df_dina_agg = df_dina.groupby(['Fecha', 'Fecha_dt', 'Nombre', 'Exercise'], as_index=False).agg({
            'Fmax_Abs': 'mean',
            'RFD_150': 'mean'
        })

        df_dina_agg['Peso_Jug'] = df_dina_agg['Nombre'].map(dict_pesos)
        df_dina_agg['Fmax_Rel'] = df_dina_agg['Fmax_Abs'] / df_dina_agg['Peso_Jug']

        ult_fecha_dina = df_dina_agg['Fecha_dt'].max()
        ult_fecha_str = df_dina_agg[df_dina_agg['Fecha_dt'] == ult_fecha_dina]['Fecha'].iloc[0]
        df_d_ult = df_dina_agg[df_dina_agg['Fecha_dt'] == ult_fecha_dina].copy()

        piv_frel = df_d_ult.pivot_table(index='Nombre', columns='Exercise', values='Fmax_Rel', aggfunc='mean')
        piv_rfd = df_d_ult.pivot_table(index='Nombre', columns='Exercise', values='RFD_150', aggfunc='mean')
        
        dict_prescripciones = {}
        for jug in piv_frel.index:
            prescripciones_j = []
            
            def val(piv, ej_name):
                if ej_name in piv.columns:
                    v = piv.loc[jug, ej_name]
                    return float(v) if pd.notna(v) else None
                return None

            ext_d, ext_i = val(piv_frel, 'Extension_rodilla_90_Derecha'), val(piv_frel, 'Extension_rodilla_90_Izquierda')
            flx_d, flx_i = val(piv_frel, 'Flexion_rodilla_90_Derecha'), val(piv_frel, 'Flexion_rodilla_90_Izquierda')
            add_d, add_i = val(piv_frel, 'ADD_Cadera_De_Pie_Derecha'), val(piv_frel, 'ADD_Cadera_De_Pie_Izquierda')
            abd_d, abd_i = val(piv_frel, 'ABD_Cadera_De_Pie_Derecha'), val(piv_frel, 'ABD_Cadera_De_Pie_Izquierda')

            rfd_ext_d, rfd_ext_i = val(piv_rfd, 'Extension_rodilla_90_Derecha'), val(piv_rfd, 'Extension_rodilla_90_Izquierda')
            rfd_flx_d, rfd_flx_i = val(piv_rfd, 'Flexion_rodilla_90_Derecha'), val(piv_rfd, 'Flexion_rodilla_90_Izquierda')
            rfd_add_d, rfd_add_i = val(piv_rfd, 'ADD_Cadera_De_Pie_Derecha'), val(piv_rfd, 'ADD_Cadera_De_Pie_Izquierda')
            rfd_abd_d, rfd_abd_i = val(piv_rfd, 'ABD_Cadera_De_Pie_Derecha'), val(piv_rfd, 'ABD_Cadera_De_Pie_Izquierda')

            def_fmax = False
            if ext_d and ext_i and ((ext_d + ext_i) / 2 < 8.0): def_fmax = True
            if flx_d and flx_i and ((flx_d + flx_i) / 2 < 4.0): def_fmax = True
            if add_d and add_i and ((add_d + add_i) / 2 < 4.0): def_fmax = True
            if abd_d and abd_i and ((abd_d + abd_i) / 2 < 3.8): def_fmax = True
            if def_fmax: prescripciones_j.append("Trabajo de Fuerza Máxima")

            def_rfd = False
            if rfd_ext_d and rfd_ext_i and ((rfd_ext_d + rfd_ext_i) / 2 < 8000): def_rfd = True
            if rfd_flx_d and rfd_flx_i and ((rfd_flx_d + rfd_flx_i) / 2 < 4000): def_rfd = True
            if rfd_add_d and rfd_add_i and ((rfd_add_d + rfd_add_i) / 2 < 1500): def_rfd = True
            if rfd_abd_d and rfd_abd_i and ((rfd_abd_d + rfd_abd_i) / 2 < 1300): def_rfd = True
            if def_rfd: prescripciones_j.append("Trabajo de Velocidad")

            has_asim = False
            if ext_d and ext_i and (abs(ext_d - ext_i) / max(ext_d, ext_i) * 100 > 10): has_asim = True
            if flx_d and flx_i and (abs(flx_d - flx_i) / max(flx_d, flx_i) * 100 > 10): has_asim = True
            if add_d and add_i and (abs(add_d - add_i) / max(add_d, add_i) * 100 > 10): has_asim = True
            if abd_d and abd_i and (abs(abd_d - abd_i) / max(abd_d, abd_i) * 100 > 10): has_asim = True
            if has_asim: prescripciones_j.append("Corregir Asimetrías")

            has_descomp = False
            if ext_d and ext_i and flx_d and flx_i and (((flx_d + flx_i) / 2) / ((ext_d + ext_i) / 2) < 0.60): has_descomp = True
            if add_d and add_i and abd_d and abd_i and (((abd_d + abd_i) / 2) / ((add_d + add_i) / 2) < 0.90): has_descomp = True
            if has_descomp: prescripciones_j.append("Corregir Descompensaciones")

            if prescripciones_j: dict_prescripciones[jug] = prescripciones_j

        c_d1, c_d2 = st.columns(2)
        with c_d1: st.metric("Jugadores con Prescripción de Trabajo Individual", f"{len(dict_prescripciones)} / {len(piv_frel)}")
        with c_d2: st.metric("Porcentaje del Vestuario en Objetivo", f"{((len(piv_frel) - len(dict_prescripciones)) / len(piv_frel) * 100):.0f}%")

        if dict_prescripciones:
            col_da1, col_da2 = st.columns(2)
            items_d = list(dict_prescripciones.items())
            mitad_d = (len(items_d) + 1) // 2
            
            with col_da1:
                for nom, defs in items_d[:mitad_d]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_da2:
                for nom, defs in items_d[mitad_d:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else:
            st.success("✅ ¡Formidable! Todo el vestuario cumple los umbrales óptimos.")

        st.markdown("<br><hr>", unsafe_allow_html=True)

        bloque_ejercicio = st.selectbox(
            "🎯 Selecciona Ejercicio / Articulación:",
            ["Extensión Rodilla 90°", "Flexión Rodilla 90°", "ABD Cadera de Pie", "ADD Cadera de Pie"]
        )

        if bloque_ejercicio == "Extensión Rodilla 90°": ej_d, ej_i, umbral_frel, umbral_rfd = 'Extension_rodilla_90_Derecha', 'Extension_rodilla_90_Izquierda', 8.0, 8000
        elif bloque_ejercicio == "Flexión Rodilla 90°": ej_d, ej_i, umbral_frel, umbral_rfd = 'Flexion_rodilla_90_Derecha', 'Flexion_rodilla_90_Izquierda', 4.0, 4000
        elif bloque_ejercicio == "ABD Cadera de Pie": ej_d, ej_i, umbral_frel, umbral_rfd = 'ABD_Cadera_De_Pie_Derecha', 'ABD_Cadera_De_Pie_Izquierda', 3.8, 1300
        else: ej_d, ej_i, umbral_frel, umbral_rfd = 'ADD_Cadera_De_Pie_Derecha', 'ADD_Cadera_De_Pie_Izquierda', 4.0, 1500

        col_izq, col_der = st.columns([7, 3])

        with col_izq:
            if ej_d in piv_frel.columns and ej_i in piv_frel.columns:
                df_g_frel = piv_frel[[ej_d, ej_i]].dropna().reset_index()
                df_g_frel['Asimetria_Pct'] = (abs(df_g_frel[ej_d] - df_g_frel[ej_i]) / df_g_frel[[ej_d, ej_i]].max(axis=1)) * 100

                fig_frel = go.Figure()
                fig_frel.add_trace(go.Bar(
                    x=df_g_frel['Nombre'], y=df_g_frel[ej_d], name='Derecha (D)', marker_color='#00A8E8',
                    text=[f"<b>{v:.2f}</b>" for v in df_g_frel[ej_d]], textposition='outside'
                ))
                fig_frel.add_trace(go.Bar(
                    x=df_g_frel['Nombre'], y=df_g_frel[ej_i], name='Izquierda (I)', marker_color='#FF9F1C',
                    text=[f"<b>{v:.2f}</b>" for v in df_g_frel[ej_i]], textposition='outside'
                ))

                max_alturas_f = df_g_frel[[ej_d, ej_i]].max(axis=1)
                for idx_f, row_f in df_g_frel.iterrows():
                    asim_val = row_f['Asimetria_Pct']
                    color_texto = "#E74C3C" if asim_val > 10 else "#2ECC71"
                    pos_y = max_alturas_f.iloc[idx_f] + 0.20

                    fig_frel.add_annotation(
                        x=row_f['Nombre'], y=pos_y,
                        text=f"<b>{asim_val:.1f}%</b>",
                        showarrow=False,
                        font=dict(color=color_texto, size=15)
                    )

                fig_frel.add_shape(type="line", x0=-0.5, x1=len(df_g_frel)-0.5, y0=umbral_frel, y1=umbral_frel, line=dict(color="#2ECC71", width=3, dash="dash"))
                fig_frel.add_annotation(x=len(df_g_frel)-1, y=umbral_frel, text=f"Ref. Óptima (>{umbral_frel} N/kg)", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                fig_frel.update_layout(
                    title=f"💪 Pico de Fuerza Relativo (N/kg) y % Asimetría - {bloque_ejercicio}",
                    barmode='group', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(tickangle=-45), yaxis=dict(title="Fuerza Relativa (N/kg)", range=[0, max(df_g_frel[ej_d].max(), df_g_frel[ej_i].max()) + 1.2]),
                    height=420, margin=dict(l=20, r=20, t=50, b=90), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_frel, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if ej_d in piv_rfd.columns and ej_i in piv_rfd.columns:
                    df_g_rfd = piv_rfd[[ej_d, ej_i]].dropna().reset_index()
                    df_g_rfd['Asimetria_RFD_Pct'] = (abs(df_g_rfd[ej_d] - df_g_rfd[ej_i]) / df_g_rfd[[ej_d, ej_i]].max(axis=1)) * 100

                    fig_rfd = go.Figure()
                    fig_rfd.add_trace(go.Bar(
                        x=df_g_rfd['Nombre'], y=df_g_rfd[ej_d], name='RFD D (N/s)', marker_color='#00A8E8',
                        text=[f"<b>{v:.0f}</b>" for v in df_g_rfd[ej_d]], textposition='outside'
                    ))
                    fig_rfd.add_trace(go.Bar(
                        x=df_g_rfd['Nombre'], y=df_g_rfd[ej_i], name='RFD I (N/s)', marker_color='#FF9F1C',
                        text=[f"<b>{v:.0f}</b>" for v in df_g_rfd[ej_i]], textposition='outside'
                    ))

                    max_alturas_r = df_g_rfd[[ej_d, ej_i]].max(axis=1)
                    for idx_r, row_r in df_g_rfd.iterrows():
                        asim_rfd_val = row_r['Asimetria_RFD_Pct']
                        color_texto_rfd = "#E74C3C" if asim_rfd_val > 10 else "#2ECC71"
                        pos_y_r = max_alturas_r.iloc[idx_r] + 250

                        fig_rfd.add_annotation(
                            x=row_r['Nombre'], y=pos_y_r,
                            text=f"<b>{asim_rfd_val:.1f}%</b>",
                            showarrow=False,
                            font=dict(color=color_texto_rfd, size=15)
                        )

                    fig_rfd.add_shape(type="line", x0=-0.5, x1=len(df_g_rfd)-0.5, y0=umbral_rfd, y1=umbral_rfd, line=dict(color="#2ECC71", width=3, dash="dash"))
                    fig_rfd.add_annotation(x=len(df_g_rfd)-1, y=umbral_rfd, text=f"Ref. Óptima (>{umbral_rfd} N/s)", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                    fig_rfd.update_layout(
                        title=f"⚡ Tasa de Desarrollo de Fuerza (RFD a 150ms N/s) y % Asimetría - {bloque_ejercicio}",
                        barmode='group', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-45), yaxis=dict(title="RFD (N/s)", range=[0, max(df_g_rfd[ej_d].max(), df_g_rfd[ej_i].max()) + 1800]),
                        height=420, margin=dict(l=20, r=20, t=50, b=90), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_rfd, use_container_width=True)

        with col_der:
            if "Rodilla" in bloque_ejercicio:
                ratios_fe, nombres_fe = [], []
                for jug in piv_frel.index:
                    def v(ej): return float(piv_frel.loc[jug, ej]) if ej in piv_frel.columns and pd.notna(piv_frel.loc[jug, ej]) else None
                    ext_d, ext_i = v('Extension_rodilla_90_Derecha'), v('Extension_rodilla_90_Izquierda')
                    flx_d, flx_i = v('Flexion_rodilla_90_Derecha'), v('Flexion_rodilla_90_Izquierda')
                    if ext_d and ext_i and flx_d and flx_i:
                        ratios_fe.append(((flx_d + flx_i) / 2) / ((ext_d + ext_i) / 2))
                        nombres_fe.append(jug)

                if ratios_fe:
                    fig_r_fe = go.Figure()
                    fig_r_fe.add_trace(go.Bar(
                        x=nombres_fe, y=ratios_fe,
                        marker_color=['#2ECC71' if v >= 0.60 else '#E74C3C' for v in ratios_fe],
                        text=[f"<b>{v:.2f}</b>" for v in ratios_fe], textposition='outside'
                    ))
                    fig_r_fe.add_shape(type="line", x0=-0.5, x1=len(nombres_fe)-0.5, y0=0.60, y1=0.60, line=dict(color="#2ECC71", width=3, dash="dash"))
                    fig_r_fe.add_annotation(x=len(nombres_fe)-1, y=0.60, text="Ref. (>0.60)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)
                    
                    fig_r_fe.update_layout(
                        title="⚖️ Ratio Flexión / Extensión Rodilla (Índice)",
                        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-45), yaxis=dict(title="Ratio Índice", range=[0, max(max(ratios_fe)+0.25, 1.0)]),
                        height=860, margin=dict(l=10, r=10, t=50, b=90)
                    )
                    st.plotly_chart(fig_r_fe, use_container_width=True)

            else:
                ratios_aa, nombres_aa = [], []
                for jug in piv_frel.index:
                    def v(ej): return float(piv_frel.loc[jug, ej]) if ej in piv_frel.columns and pd.notna(piv_frel.loc[jug, ej]) else None
                    add_d, add_i = v('ADD_Cadera_De_Pie_Derecha'), v('ADD_Cadera_De_Pie_Izquierda')
                    abd_d, abd_i = v('ABD_Cadera_De_Pie_Derecha'), v('ABD_Cadera_De_Pie_Izquierda')
                    if add_d and add_i and abd_d and abd_i:
                        ratios_aa.append(((abd_d + abd_i) / 2) / ((add_d + add_i) / 2))
                        nombres_aa.append(jug)

                if ratios_aa:
                    fig_r_aa = go.Figure()
                    fig_r_aa.add_trace(go.Bar(
                        x=nombres_aa, y=ratios_aa,
                        marker_color=['#2ECC71' if v >= 0.90 else '#E74C3C' for v in ratios_aa],
                        text=[f"<b>{v:.2f}</b>" for v in ratios_aa], textposition='outside'
                    ))
                    fig_r_aa.add_shape(type="line", x0=-0.5, x1=len(nombres_aa)-0.5, y0=0.90, y1=0.90, line=dict(color="#2ECC71", width=3, dash="dash"))
                    fig_r_aa.add_annotation(x=len(nombres_aa)-1, y=0.90, text="Ref. (>0.90)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=12)
                    
                    fig_r_aa.update_layout(
                        title="⚖️ Ratio ABD / ADD Cadera (Índice)",
                        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-45), yaxis=dict(title="Ratio Índice", range=[0, max(max(ratios_aa)+0.3, 1.3)]),
                        height=860, margin=dict(l=10, r=10, t=50, b=90)
                    )
                    st.plotly_chart(fig_r_aa, use_container_width=True)

# =============================================================================
# ÁREA 5: SALTOS
# =============================================================================
elif pest_sel == "🚀 Saltos (CMJ)":
    
    if df_saltos is not None and not df_saltos.empty:
        ult_f_saltos = df_saltos['Fecha_dt'].max()
        ult_f_saltos_str = df_saltos[df_saltos['Fecha_dt'] == ult_f_saltos]['Fecha'].iloc[0]
        df_s_ult = df_saltos[df_saltos['Fecha_dt'] == ult_f_saltos].copy()

        df_piv_s = df_s_ult.groupby(['Nombre', 'Posicion', 'Tipo'], as_index=False)['Altura'].mean()
        piv_total_j = df_piv_s.pivot_table(index=['Nombre', 'Posicion'], columns='Tipo', values='Altura', aggfunc='mean').reset_index()

        dict_prescripciones_saltos = {}

        for _, row_j in piv_total_j.iterrows():
            nom_j = row_j['Nombre']
            pos_j = row_j['Posicion']
            cmj_val = row_j.get('CMJ', None)
            sr_val = row_j.get('slCMJright', None)
            sl_val = row_j.get('slCMJleft', None)

            prescripciones_j = []

            ref_cmj_val, ref_sl_val = None, None
            if df_ref_saltos is not None and not df_ref_saltos.empty:
                r_ref = df_ref_saltos[df_ref_saltos['Posicion'] == pos_j]
                if not r_ref.empty:
                    ref_cmj_val = r_ref.iloc[0].get('CMJ_Ref', None)
                    sr_r = r_ref.iloc[0].get('slCMJright_Ref', None)
                    sl_r = r_ref.iloc[0].get('slCMJleft_Ref', None)
                    if pd.notna(sr_r) and pd.notna(sl_r): ref_sl_val = (float(sr_r) + float(sl_r)) / 2
                    elif pd.notna(sr_r): ref_sl_val = float(sr_r)
                    elif pd.notna(sl_r): ref_sl_val = float(sl_r)

            needs_potencia = False
            if pd.notna(cmj_val) and ref_cmj_val and pd.notna(ref_cmj_val) and cmj_val < ref_cmj_val:
                needs_potencia = True
            if ref_sl_val and pd.notna(ref_sl_val):
                if (pd.notna(sr_val) and sr_val < ref_sl_val) or (pd.notna(sl_val) and sl_val < ref_sl_val):
                    needs_potencia = True

            if needs_potencia:
                prescripciones_j.append("Trabajo de Potencia")

            if pd.notna(sr_val) and pd.notna(sl_val) and max(sr_val, sl_val) > 0:
                asim_val = (abs(sr_val - sl_val) / max(sr_val, sl_val)) * 100
                if asim_val > 10:
                    prescripciones_j.append("Corregir Asimetrías")

            if prescripciones_j:
                dict_prescripciones_saltos[nom_j] = prescripciones_j

        c_s1, c_s2 = st.columns(2)
        with c_s1: st.metric("Jugadores con Prescripción de Trabajo Individual", f"{len(dict_prescripciones_saltos)} / {len(piv_total_j)}")
        with c_s2: st.metric("Porcentaje del Vestuario en Objetivo", f"{((len(piv_total_j) - len(dict_prescripciones_saltos)) / len(piv_total_j) * 100):.0f}%")

        if dict_prescripciones_saltos:
            col_sa1, col_sa2 = st.columns(2)
            items_s = list(dict_prescripciones_saltos.items())
            mitad_s = (len(items_s) + 1) // 2
            
            with col_sa1:
                for nom, defs in items_s[:mitad_s]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_sa2:
                for nom, defs in items_s[mitad_s:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else:
            st.success("✅ ¡Excelente! Todo el vestuario cumple las referencias de saltabilidad y simetría.")

        st.markdown("<br><hr>", unsafe_allow_html=True)

    # 1. FILTRO Y SECCIÓN: EVOLUCIÓN GENERAL DE LA PLANTILLA
    col_f_evo, col_sp_evo = st.columns([1, 2])
    with col_f_evo:
        sel_tipo_evo = st.selectbox(
            "📈 Selecciona Métrica para Evolución de Equipo:",
            ["Ambos Gráficos", "Evolución CMJ (Media de Equipo)", "Evolución DRI (Drop Jump 50cm)"]
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if sel_tipo_evo == "Ambos Gráficos":
        col_cmj_g, col_dri_g = st.columns(2)
    else:
        col_cmj_g = st.container()
        col_dri_g = st.container()

    # --- GRÁFICO 1: EVOLUCIÓN CMJ ---
    if sel_tipo_evo in ["Ambos Gráficos", "Evolución CMJ (Media de Equipo)"]:
        with col_cmj_g:
            st.markdown("### 📈 Evolución CMJ (Media de Equipo)")
            if df_saltos is None or df_saltos.empty:
                st.warning("⚠️ No se encontró el archivo 'SALTOS.xlsx' local.")
            else:
                df_cmj = df_saltos[df_saltos['Tipo'].str.upper() == 'CMJ'].copy()
                if df_cmj.empty:
                    st.info("No hay datos de CMJ.")
                else:
                    idx_max_cmj = df_cmj['Altura'].idxmax()
                    row_max_cmj = df_cmj.loc[idx_max_cmj]
                    st.info(f"🏆 **Récord Histórico CMJ:** `{row_max_cmj['Nombre']}` con **{row_max_cmj['Altura']:.1f} cm**")

                    df_jug_cmj = df_cmj.groupby(['Fecha', 'Fecha_dt', 'Nombre'], as_index=False)['Altura'].mean()
                    df_cmj_eq = df_jug_cmj.groupby(['Fecha', 'Fecha_dt'], as_index=False).agg(
                        Media_Equipo=('Altura', 'mean'),
                        SD_Equipo=('Altura', 'std')
                    ).sort_values('Fecha_dt')

                    df_cmj_eq['SD_Equipo'] = df_cmj_eq['SD_Equipo'].fillna(0)
                    fechas_cmj_str = df_cmj_eq['Fecha'].tolist()
                    fig_cmj = go.Figure()

                    fig_cmj.add_trace(go.Bar(
                        x=fechas_cmj_str, 
                        y=df_cmj_eq['Media_Equipo'],
                        error_y=dict(type='data', array=df_cmj_eq['SD_Equipo'], visible=True, color='#FFFFFF', thickness=1.5, width=6),
                        name='Media Equipo CMJ',
                        marker_color=COLOR_ADARVE_GRANATE,
                        marker_line_color=COLOR_ADARVE_BORDER,
                        marker_line_width=2,
                        text=[f"<b>{v:.1f} cm</b>" for v in df_cmj_eq['Media_Equipo']],
                        textposition='inside',
                        insidetextanchor='middle'
                    ))

                    for k in range(len(df_cmj_eq)):
                        f_curr = fechas_cmj_str[k]
                        val_curr = df_cmj_eq['Media_Equipo'].iloc[k]
                        sd_curr = df_cmj_eq['SD_Equipo'].iloc[k]
                        pos_y = val_curr + sd_curr + 2.5

                        if k == 0:
                            fig_cmj.add_annotation(
                                x=f_curr, y=pos_y,
                                text=f"<b>{val_curr:.1f} cm</b>",
                                showarrow=False, font=dict(color="white", size=13)
                            )
                        else:
                            m_prev = df_cmj_eq['Media_Equipo'].iloc[k-1]
                            pct_v = ((val_curr - m_prev) / m_prev) * 100
                            col_v = "#2ECC71" if pct_v >= 0 else "#E74C3C"
                            signo = "+" if pct_v > 0 else ""

                            fig_cmj.add_annotation(
                                x=f_curr, y=pos_y,
                                text=f"<b>{signo}{pct_v:.1f}%</b>",
                                showarrow=False, font=dict(color=col_v, size=15)
                            )

                    max_y_cmj = (df_cmj_eq['Media_Equipo'] + df_cmj_eq['SD_Equipo']).max() + 7
                    fig_cmj.update_layout(
                        title="Evolución CMJ (cm) - Media ± SD Granate",
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-30), yaxis=dict(title="Altura Salto (cm)", range=[0, max_y_cmj]),
                        height=460, margin=dict(l=10, r=10, t=50, b=80), showlegend=False
                    )
                    st.plotly_chart(fig_cmj, use_container_width=True)

    # --- GRÁFICO 2: EVOLUCIÓN DRI ---
    if sel_tipo_evo in ["Ambos Gráficos", "Evolución DRI (Drop Jump 50cm)"]:
        with col_dri_g:
            st.markdown("### ⚡ Evolución DRI (Drop Jump 50cm)")
            if df_dri_sheet is None or df_dri_sheet.empty:
                st.warning("⚠️ No se pudo conectar al Google Sheet de Drop Jump.")
            else:
                df_dri = df_dri_sheet[df_dri_sheet['Tipo'].str.upper().str.startswith('DJ')].copy()
                if df_dri.empty:
                    df_dri = df_dri_sheet.copy()

                if df_dri.empty:
                    st.info("No hay registros de Drop Jump.")
                else:
                    idx_max_dri = df_dri['DRI'].idxmax()
                    row_max_dri = df_dri.loc[idx_max_dri]
                    st.info(f"🏆 **Récord Histórico DRI:** `{row_max_dri['Nombre']}` con **{row_max_dri['DRI']:.2f}**")

                    df_jug_dri = df_dri.groupby(['Fecha', 'Fecha_dt', 'Nombre'], as_index=False)['DRI'].mean()
                    df_dri_eq = df_jug_dri.groupby(['Fecha', 'Fecha_dt'], as_index=False).agg(
                        Media_Equipo=('DRI', 'mean'),
                        SD_Equipo=('DRI', 'std')
                    ).sort_values('Fecha_dt')

                    df_dri_eq['SD_Equipo'] = df_dri_eq['SD_Equipo'].fillna(0)
                    fechas_dri_str = df_dri_eq['Fecha'].tolist()
                    fig_dri = go.Figure()

                    fig_dri.add_trace(go.Bar(
                        x=fechas_dri_str, 
                        y=df_dri_eq['Media_Equipo'],
                        error_y=dict(type='data', array=df_dri_eq['SD_Equipo'], visible=True, color='#FFFFFF', thickness=1.5, width=6),
                        name='Media Equipo DRI',
                        marker_color=COLOR_ADARVE_GRANATE,
                        marker_line_color=COLOR_ADARVE_BORDER,
                        marker_line_width=2,
                        text=[f"<b>{v:.2f}</b>" for v in df_dri_eq['Media_Equipo']],
                        textposition='inside',
                        insidetextanchor='middle'
                    ))

                    for k in range(len(df_dri_eq)):
                        f_curr = fechas_dri_str[k]
                        val_curr = df_dri_eq['Media_Equipo'].iloc[k]
                        sd_curr = df_dri_eq['SD_Equipo'].iloc[k]
                        pos_y = val_curr + sd_curr + 0.15

                        if k == 0:
                            fig_dri.add_annotation(
                                x=f_curr, y=pos_y,
                                text=f"<b>{val_curr:.2f}</b>",
                                showarrow=False, font=dict(color="white", size=13)
                            )
                        else:
                            m_prev = df_dri_eq['Media_Equipo'].iloc[k-1]
                            pct_v = ((val_curr - m_prev) / m_prev) * 100
                            col_v = "#2ECC71" if pct_v >= 0 else "#E74C3C"
                            signo = "+" if pct_v > 0 else ""

                            fig_dri.add_annotation(
                                x=f_curr, y=pos_y,
                                text=f"<b>{signo}{pct_v:.1f}%</b>",
                                showarrow=False, font=dict(color=col_v, size=15)
                            )

                    max_y_dri = (df_dri_eq['Media_Equipo'] + df_dri_eq['SD_Equipo']).max() + 0.45
                    fig_dri.update_layout(
                        title="Evolución DRI Exacto - Media ± SD Granate",
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-30), yaxis=dict(title="DRI (Índice)", range=[0, max_y_dri]),
                        height=460, margin=dict(l=10, r=10, t=50, b=80), showlegend=False
                    )
                    st.plotly_chart(fig_dri, use_container_width=True)

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # 2. FILTRO Y SECCIÓN: PERFIL POR DEMARCACIONES
    st.markdown("### Evolución individual del salto")

    if df_saltos is None or df_saltos.empty:
        st.warning("⚠️ No se encontraron los datos locales de saltos para desglosar por posición.")
    else:
        ult_f_saltos = df_saltos['Fecha_dt'].max()
        ult_f_saltos_str = df_saltos[df_saltos['Fecha_dt'] == ult_f_saltos]['Fecha'].iloc[0]
        df_s_ult = df_saltos[df_saltos['Fecha_dt'] == ult_f_saltos].copy()

        df_piv_s = df_s_ult.groupby(['Nombre', 'Posicion', 'Tipo'], as_index=False)['Altura'].mean()
        posiciones_s = sorted([p for p in df_piv_s['Posicion'].dropna().unique() if str(p).strip() not in ['nan', '']])

        if not posiciones_s:
            st.info("No se hallaron demarcaciones asociadas en Posiciones.xlsx para esta sesión.")
        else:
            col_f_pos, col_sp_pos = st.columns([1, 2])
            with col_f_pos:
                pos_sel_saltos = st.selectbox("⚽ Filtrar por Demarcación:", ["Todas las Demarcaciones"] + posiciones_s, key="sb_pos_saltos")

            pos_a_mostrar_s = posiciones_s if pos_sel_saltos == "Todas las Demarcaciones" else [pos_sel_saltos]

            st.markdown("<br>", unsafe_allow_html=True)

            for i in range(0, len(pos_a_mostrar_s), 2):
                col_sp1, col_sp2 = st.columns(2) if len(pos_a_mostrar_s) > 1 else (st.container(), None)
                cols_iter_s = [col_sp1, col_sp2] if len(pos_a_mostrar_s) > 1 else [col_sp1]

                for idx_c, col_curr in enumerate(cols_iter_s):
                    if col_curr is not None and (i + idx_c < len(pos_a_mostrar_s)):
                        pos_curr = pos_a_mostrar_s[i + idx_c]
                        with col_curr:
                            df_pos_data = df_piv_s[df_piv_s['Posicion'] == pos_curr].copy()
                            piv_j = df_pos_data.pivot_table(index='Nombre', columns='Tipo', values='Altura', aggfunc='mean').reset_index()

                            for col_tipo in ['CMJ', 'slCMJright', 'slCMJleft']:
                                if col_tipo not in piv_j.columns:
                                    piv_j[col_tipo] = None

                            fig_pos = go.Figure()

                            fig_pos.add_trace(go.Bar(
                                x=piv_j['Nombre'], y=piv_j['CMJ'], name='CMJ', marker_color='#00A8E8',
                                text=[f"<b>{v:.1f}</b>" if pd.notna(v) else "" for v in piv_j['CMJ']], textposition='outside'
                            ))

                            fig_pos.add_trace(go.Bar(
                                x=piv_j['Nombre'], y=piv_j['slCMJright'], name='slCMJ Right', marker_color='#FF9F1C',
                                text=[f"<b>{v:.1f}</b>" if pd.notna(v) else "" for v in piv_j['slCMJright']], textposition='outside'
                            ))

                            fig_pos.add_trace(go.Bar(
                                x=piv_j['Nombre'], y=piv_j['slCMJleft'], name='slCMJ Left', marker_color='#2ECC71',
                                text=[f"<b>{v:.1f}</b>" if pd.notna(v) else "" for v in piv_j['slCMJleft']], textposition='outside'
                            ))

                            for idx_r, row_j in piv_j.iterrows():
                                vr, vl = row_j['slCMJright'], row_j['slCMJleft']
                                if pd.notna(vr) and pd.notna(vl) and max(vr, vl) > 0:
                                    asim_s = (abs(vr - vl) / max(vr, vl)) * 100
                                    color_as = "#E74C3C" if asim_s > 10 else "#2ECC71"
                                    pos_y_s = max(vr, vl) + 3.8

                                    fig_pos.add_annotation(
                                        x=idx_r + 0.16,
                                        y=pos_y_s,
                                        text=f"<b>{asim_s:.1f}%</b>",
                                        showarrow=False,
                                        font=dict(color=color_as, size=15)
                                    )

                            ref_cmj_val, ref_sl_val = None, None
                            if df_ref_saltos is not None and not df_ref_saltos.empty:
                                row_ref = df_ref_saltos[df_ref_saltos['Posicion'] == pos_curr]
                                if not row_ref.empty:
                                    ref_cmj_val = row_ref.iloc[0].get('CMJ_Ref', None)
                                    sr = row_ref.iloc[0].get('slCMJright_Ref', None)
                                    sl = row_ref.iloc[0].get('slCMJleft_Ref', None)
                                    if pd.notna(sr) and pd.notna(sl):
                                        ref_sl_val = (float(sr) + float(sl)) / 2
                                    elif pd.notna(sr): ref_sl_val = float(sr)
                                    elif pd.notna(sl): ref_sl_val = float(sl)

                            if ref_cmj_val and pd.notna(ref_cmj_val):
                                fig_pos.add_shape(type="line", x0=-0.5, x1=len(piv_j)-0.5, y0=ref_cmj_val, y1=ref_cmj_val, line=dict(color="#2ECC71", width=2.5, dash="dash"))
                                fig_pos.add_annotation(x=len(piv_j)-1, y=ref_cmj_val, text=f"Ref CMJ ({ref_cmj_val:.1f} cm)", showarrow=False, font=dict(color="#2ECC71", size=11), align="right", yshift=10)

                            if ref_sl_val and pd.notna(ref_sl_val):
                                fig_pos.add_shape(type="line", x0=-0.5, x1=len(piv_j)-0.5, y0=ref_sl_val, y1=ref_sl_val, line=dict(color="#F1C40F", width=2.5, dash="dash"))
                                fig_pos.add_annotation(x=len(piv_j)-1, y=ref_sl_val, text=f"Ref slCMJ ({ref_sl_val:.1f} cm)", showarrow=False, font=dict(color="#F1C40F", size=11), align="right", yshift=-12)

                            max_y_p = max(piv_j[['CMJ', 'slCMJright', 'slCMJleft']].max().max(), (ref_cmj_val or 0)) + 7

                            fig_pos.update_layout(
                                title=f"⚽ Demarcación: {pos_curr} ({ult_f_saltos_str})",
                                barmode='group', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(tickangle=-45), yaxis=dict(title="Altura Salto (cm)", range=[0, max_y_p]),
                                height=460, margin=dict(l=20, r=20, t=50, b=90),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                            )
                            st.plotly_chart(fig_pos, use_container_width=True)

            st.markdown("<br><hr>", unsafe_allow_html=True)

            # --- NUEVA SECCIÓN: EVOLUCIÓN INDIVIDUAL DRI ---
            st.markdown("### ⚡ Evolución Individual de DRI (Drop Jump)")
            
            if df_dri_sheet is None or df_dri_sheet.empty:
                st.warning("⚠️ No hay datos de DRI registrados en la base de datos.")
            else:
                jugadores_dri = sorted(df_dri_sheet['Nombre'].dropna().unique())
                
                col_f_dri, col_vacio_dri = st.columns([1, 2])
                with col_f_dri:
                    jug_sel_dri = st.selectbox("🏃 Filtrar por Jugador:", jugadores_dri, key="sb_jug_dri")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                df_dri_jug = df_dri_sheet[df_dri_sheet['Nombre'] == jug_sel_dri].groupby(['Fecha', 'Fecha_dt'], as_index=False)['DRI'].mean().sort_values('Fecha_dt')
                
                if df_dri_jug.empty:
                    st.info(f"No hay saltos DRI registrados para {jug_sel_dri}.")
                else:
                    media_equipo_dri = df_dri_sheet['DRI'].mean()
                    
                    df_dri_jug['DRI_Ant'] = df_dri_jug['DRI'].shift(1)
                    df_dri_jug['Var_Pct'] = ((df_dri_jug['DRI'] - df_dri_jug['DRI_Ant']) / df_dri_jug['DRI_Ant']) * 100
                    
                    fig_dri_ind = go.Figure()
                    
                    etiquetas_dri = [f"<b>{r['DRI']:.2f}</b>" if pd.isna(r['Var_Pct']) else f"<b>{r['DRI']:.2f}</b><br><i>{'+' if r['Var_Pct']>0 else ''}{r['Var_Pct']:.1f}%</i>" for _, r in df_dri_jug.iterrows()]

                    fig_dri_ind.add_trace(go.Bar(
                        x=df_dri_jug['Fecha'], y=df_dri_jug['DRI'],
                        name=f"DRI - {jug_sel_dri}", marker_color='#00A8E8',
                        text=etiquetas_dri, textposition='outside'
                    ))
                    
                    fig_dri_ind.add_shape(type="line", x0=-0.5, x1=len(df_dri_jug)-0.5, y0=media_equipo_dri, y1=media_equipo_dri, line=dict(color="#FFC107", width=2.5, dash="dash"))
                    fig_dri_ind.add_annotation(x=len(df_dri_jug)-1, y=media_equipo_dri, text=f"Media Equipo ({media_equipo_dri:.2f})", showarrow=False, font=dict(color="#FFC107", size=12), align="right", yshift=12)
                    
                    max_y_dri_ind = max(df_dri_jug['DRI'].max(), media_equipo_dri) + 0.4
                    
                    fig_dri_ind.update_layout(
                        title=f"Evolución DRI: {jug_sel_dri}",
                        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickangle=-45), yaxis=dict(title="DRI (Índice)", range=[0, max_y_dri_ind]),
                        height=420, margin=dict(l=20, r=20, t=50, b=90), showlegend=False
                    )
                    st.plotly_chart(fig_dri_ind, use_container_width=True)

# =============================================================================
# ÁREA 6: TREN SUPERIOR
# =============================================================================
elif pest_sel == "🏋️ Tren Superior":
    st.subheader("🏋️ Evaluación de Fuerza de Tren Superior")
    
    if df_fts is None or df_fts.empty:
        st.warning("⚠️ No se encontró el archivo 'FUERZA_TS.xlsx' en 'data/EVALUACIONES/FUERZA TREN SUPERIOR/'.")
    else:
        fechas_ts_dt = sorted(df_fts['Fecha_dt'].unique())
        ult_fecha_ts_dt = fechas_ts_dt[-1]
        ult_fecha_ts_str = df_fts[df_fts['Fecha_dt'] == ult_fecha_ts_dt]['Fecha'].iloc[0]

        df_fts_ult = df_fts[df_fts['Fecha_dt'] == ult_fecha_ts_dt].copy()

        dict_prescripciones_ts = {}
        REF_PRESS_BANCA = 20.0
        REF_DOMINADAS = 10.0

        for _, row_j in df_fts_ult.iterrows():
            nom_j = row_j['Nombre']
            pb_val = row_j.get('Press_Banca', None)
            dom_val = row_j.get('Dominada', None)

            prescripciones_j = []
            needs_ts = False

            if pd.notna(pb_val) and pb_val < REF_PRESS_BANCA:
                needs_ts = True
            if pd.notna(dom_val) and dom_val < REF_DOMINADAS:
                needs_ts = True

            if needs_ts:
                prescripciones_j.append("Trabajo de Fuerza Tren Superior")
                dict_prescripciones_ts[nom_j] = prescripciones_j

        st.markdown(f"### 📋 Informe de Necesidades y Alertas ({ult_fecha_ts_str})")
        c_ts1, c_ts2 = st.columns(2)
        with c_ts1: st.metric("Jugadores con Prescripción de Trabajo Individual", f"{len(dict_prescripciones_ts)} / {len(df_fts_ult)}")
        with c_ts2: st.metric("Porcentaje del Vestuario en Objetivo", f"{((len(df_fts_ult) - len(dict_prescripciones_ts)) / len(df_fts_ult) * 100):.0f}%")

        st.markdown("#### 🎯 Prescripción Metodológica por Jugador:")
        if dict_prescripciones_ts:
            col_tsa1, col_tsa2 = st.columns(2)
            items_ts = list(dict_prescripciones_ts.items())
            mitad_ts = (len(items_ts) + 1) // 2
            
            with col_tsa1:
                for nom, defs in items_ts[:mitad_ts]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_tsa2:
                for nom, defs in items_ts[mitad_ts:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else:
            st.success("✅ ¡Excelente! Todo el vestuario cumple los umbrales mínimos de fuerza de tren superior.")

        st.markdown("<br><hr>", unsafe_allow_html=True)

        col_pb, col_dom = st.columns(2)

        with col_pb:
            st.markdown("### 🏋️‍♂️ Press Banca (40 kg en 40s)")
            df_pb = df_fts.dropna(subset=['Press_Banca']).copy()
            
            if df_pb.empty:
                st.info("No hay registros de Press Banca.")
            else:
                max_pb_val = df_pb['Press_Banca'].max()
                df_max_pb = df_pb[df_pb['Press_Banca'] == max_pb_val]
                nom_max_pb = df_max_pb.iloc[0]['Nombre']
                
                st.info(f"🏆 **Récord Histórico:** `{nom_max_pb}` con **{max_pb_val:.0f} reps**")

                df_pb_ult = df_pb[df_pb['Fecha_dt'] == ult_fecha_ts_dt].sort_values('Press_Banca', ascending=False)
                jugadores_ord_pb = df_pb_ult['Nombre'].tolist()

                for j in df_pb['Nombre'].unique():
                    if j not in jugadores_ord_pb:
                        jugadores_ord_pb.append(j)

                fig_pb = go.Figure()
                fechas_pb_ord = sorted(df_pb['Fecha_dt'].unique())
                colores_pb = ['#00A8E8', '#FF9F1C', '#2ECC71', '#9B59B6', '#E74C3C', '#F1C40F']

                for idx_f, f_dt in enumerate(fechas_pb_ord):
                    f_str = df_pb[df_pb['Fecha_dt'] == f_dt]['Fecha'].iloc[0]
                    df_f_data = df_pb[df_pb['Fecha_dt'] == f_dt].set_index('Nombre')

                    val_y = [df_f_data.loc[j, 'Press_Banca'] if j in df_f_data.index else None for j in jugadores_ord_pb]

                    fig_pb.add_trace(go.Bar(
                        x=jugadores_ord_pb, y=val_y,
                        name=f"Fecha {f_str}",
                        marker_color=colores_pb[idx_f % len(colores_pb)],
                        text=[f"<b>{v:.0f}</b>" if pd.notna(v) else "" for v in val_y],
                        textposition='outside'
                    ))

                fig_pb.add_shape(type="line", x0=-0.5, x1=len(jugadores_ord_pb)-0.5, y0=REF_PRESS_BANCA, y1=REF_PRESS_BANCA, line=dict(color="#2ECC71", width=3, dash="dash"))
                fig_pb.add_annotation(x=len(jugadores_ord_pb)-1, y=REF_PRESS_BANCA, text=f"Ref. Óptima (≥{REF_PRESS_BANCA:.0f} reps)", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                fig_pb.update_layout(
                    title=f"Ranking Press Banca (Ordenado por última sesión: {ult_fecha_ts_str})",
                    barmode='group', template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(tickangle=-45), yaxis=dict(title="Repeticiones", range=[0, max(max_pb_val, REF_PRESS_BANCA) + 5]),
                    height=520, margin=dict(l=10, r=10, t=50, b=100),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_pb, use_container_width=True)

        with col_dom:
            st.markdown("### 🤸‍♂️ Dominadas (30s)")
            df_dom = df_fts.dropna(subset=['Dominada']).copy()
            
            if df_dom.empty:
                st.info("No hay registros de Dominadas.")
            else:
                max_dom_val = df_dom['Dominada'].max()
                df_max_dom = df_dom[df_dom['Dominada'] == max_dom_val]
                nom_max_dom = df_max_dom.iloc[0]['Nombre']
                
                st.info(f"🏆 **Récord Histórico:** `{nom_max_dom}` con **{max_dom_val:.0f} reps**")

                df_dom_ult = df_dom[df_dom['Fecha_dt'] == ult_fecha_ts_dt].sort_values('Dominada', ascending=False)
                jugadores_ord_dom = df_dom_ult['Nombre'].tolist()

                for j in df_dom['Nombre'].unique():
                    if j not in jugadores_ord_dom:
                        jugadores_ord_dom.append(j)

                fig_dom = go.Figure()
                fechas_dom_ord = sorted(df_dom['Fecha_dt'].unique())
                colores_dom = ['#2ECC71', '#00A8E8', '#FF9F1C', '#9B59B6', '#E74C3C', '#F1C40F']

                for idx_f, f_dt in enumerate(fechas_dom_ord):
                    f_str = df_dom[df_dom['Fecha_dt'] == f_dt]['Fecha'].iloc[0]
                    df_f_data = df_dom[df_dom['Fecha_dt'] == f_dt].set_index('Nombre')

                    val_y = [df_f_data.loc[j, 'Dominada'] if j in df_f_data.index else None for j in jugadores_ord_dom]

                    fig_dom.add_trace(go.Bar(
                        x=jugadores_ord_dom, y=val_y,
                        name=f"Fecha {f_str}",
                        marker_color=colores_dom[idx_f % len(colores_dom)],
                        text=[f"<b>{v:.0f}</b>" if pd.notna(v) else "" for v in val_y],
                        textposition='outside'
                    ))

                fig_dom.add_shape(type="line", x0=-0.5, x1=len(jugadores_ord_dom)-0.5, y0=REF_DOMINADAS, y1=REF_DOMINADAS, line=dict(color="#2ECC71", width=3, dash="dash"))
                fig_dom.add_annotation(x=len(jugadores_ord_dom)-1, y=REF_DOMINADAS, text=f"Ref. Óptima (≥{REF_DOMINADAS:.0f} reps)", showarrow=False, font=dict(color="#2ECC71", size=12), align="right", yshift=12)

                fig_dom.update_layout(
                    title=f"Ranking Dominadas (Ordenado por última sesión: {ult_fecha_ts_str})",
                    barmode='group', template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(tickangle=-45), yaxis=dict(title="Repeticiones", range=[0, max(max_dom_val, REF_DOMINADAS) + 5]),
                    height=520, margin=dict(l=10, r=10, t=50, b=100),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_dom, use_container_width=True)

# =============================================================================
# ÁREA 7: VELOCIDAD & COD
# =============================================================================
elif pest_sel == "⚡ Velocidad & COD":
    st.subheader("⚡ Evaluación de Velocidad, Aceleración & COD en Campo")
    
    if df_campo is None or df_campo.empty:
        st.warning("⚠️ No se encontró el archivo 'CAMPO.xlsx' en 'data/EVALUACIONES/CAMPO/'.")
    else:
        ult_f_campo_dt = df_campo['Fecha_dt'].max()
        ult_f_campo_str = df_campo[df_campo['Fecha_dt'] == ult_f_campo_dt]['Fecha'].iloc[0]
        df_c_ult = df_campo[df_campo['Fecha_dt'] == ult_f_campo_dt].copy()

        # 1. INFORME DE ALERTAS Y PRESCRIPCIÓN
        dict_prescripciones_campo = {}
        for _, row_j in df_c_ult.iterrows():
            nom_j = row_j['Nombre']
            pos_j = row_j['Posicion']
            v_val = row_j.get('V_MAX', None)
            ac_val = row_j.get('AC_MAX', None)
            dec_val = row_j.get('DEC_MAX', None)
            ts_val = row_j.get('Tecnica_Sprint', None)
            tcod_val = row_j.get('Tecnica_COD', None)

            prescripciones_j = []

            ref_v, ref_ac, ref_dec = None, None, None
            if df_ref_campo is not None and not df_ref_campo.empty:
                r_ref = df_ref_campo[df_ref_campo['Posicion'] == pos_j]
                if not r_ref.empty:
                    ref_v = r_ref.iloc[0].get('V_MAX_Ref', None)
                    ref_ac = r_ref.iloc[0].get('AC_MAX_Ref', None)
                    ref_dec = r_ref.iloc[0].get('DEC_MAX_Ref', None)

            if (pd.notna(v_val) and pd.notna(ref_v) and v_val < ref_v) or \
               (pd.notna(ac_val) and pd.notna(ref_ac) and ac_val < ref_ac):
                prescripciones_j.append("Trabajo de Velocidad / Aceleración")

            if pd.notna(dec_val) and pd.notna(ref_dec) and dec_val > ref_dec:
                prescripciones_j.append("Trabajo de Capacidad COD")

            if (pd.notna(ts_val) and ts_val <= 2) or (pd.notna(tcod_val) and tcod_val <= 2):
                prescripciones_j.append("Optimización Biomecánica")

            if prescripciones_j:
                dict_prescripciones_campo[nom_j] = prescripciones_j

        st.markdown(f"### 📋 Informe de Necesidades y Alertas ({ult_f_campo_str})")
        c_c1, c_c2 = st.columns(2)
        with c_c1: st.metric("Jugadores con Prescripción de Trabajo Individual", f"{len(dict_prescripciones_campo)} / {len(df_c_ult)}")
        with c_c2: 
            pct_opt_c = ((len(df_c_ult) - len(dict_prescripciones_campo)) / len(df_c_ult) * 100) if len(df_c_ult) > 0 else 100
            st.metric("Porcentaje del Vestuario en Objetivo", f"{pct_opt_c:.0f}%")

        st.markdown("#### 🎯 Prescripción Metodológica por Jugador:")
        if dict_prescripciones_campo:
            col_ca1, col_ca2 = st.columns(2)
            items_c = list(dict_prescripciones_campo.items())
            mitad_c = (len(items_c) + 1) // 2
            
            with col_ca1:
                for nom, defs in items_c[:mitad_c]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
            with col_ca2:
                for nom, defs in items_c[mitad_c:]:
                    st.markdown(f"🔴 **{nom}**: <span style='color: #E74C3C;'>{' • '.join(defs)}</span>", unsafe_allow_html=True)
        else:
            st.success("✅ ¡Excelente! Todo el vestuario cumple los objetivos cinemáticos y biomecánicos.")

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. RÉCORDS HISTÓRICOS DE LA PLANTILLA
        c_rec1, c_rec2, c_rec3 = st.columns(3)
        
        if 'V_MAX' in df_campo.columns and not df_campo['V_MAX'].dropna().empty:
            idx_vmax = df_campo['V_MAX'].idxmax()
            row_vmax = df_campo.loc[idx_vmax]
            with c_rec1:
                st.info(f"⚡ **Máx. Velocidad (V_MAX):**\n`{row_vmax['Nombre']}` - **{row_vmax['V_MAX']:.1f} km/h**")
        
        if 'AC_MAX' in df_campo.columns and not df_campo['AC_MAX'].dropna().empty:
            idx_acmax = df_campo['AC_MAX'].idxmax()
            row_acmax = df_campo.loc[idx_acmax]
            with c_rec2:
                st.info(f"🚀 **Máx. Aceleración (AC_MAX):**\n`{row_acmax['Nombre']}` - **{row_acmax['AC_MAX']:.2f} m/s²**")

        if 'DEC_MAX' in df_campo.columns and not df_campo['DEC_MAX'].dropna().empty:
            idx_decmax = df_campo['DEC_MAX'].idxmin()
            row_decmax = df_campo.loc[idx_decmax]
            with c_rec3:
                st.info(f"🛑 **Máx. Desaceleración (DEC_MAX):**\n`{row_decmax['Nombre']}` - **{row_decmax['DEC_MAX']:.2f} m/s²**")

        st.markdown("<br><hr>", unsafe_allow_html=True)

        # 3. FILTROS PARALELOS
        posiciones_campo = sorted([p for p in df_campo['Posicion'].dropna().unique() if str(p).strip() not in ['nan', '']])
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            prueba_sel = st.selectbox(
                "🎯 Selecciona Métrica / Test de Campo:",
                ["Velocidad Máxima (V_MAX)", "Aceleración Máxima (AC_MAX)", "Desaceleración / COD (DEC_MAX)"]
            )
        with col_f2:
            pos_sel_campo = st.selectbox(
                "⚽ Filtrar por Demarcación:",
                ["Todas las Demarcaciones"] + posiciones_campo
            )

        if "Velocidad" in prueba_sel:
            col_metrica, col_ref, col_tec = 'V_MAX', 'V_MAX_Ref', 'Tecnica_Sprint'
            titulo_m = "Velocidad Máxima (V_MAX)"
            unidad_m = "km/h"
        elif "Aceleración" in prueba_sel:
            col_metrica, col_ref, col_tec = 'AC_MAX', 'AC_MAX_Ref', 'Tecnica_Sprint'
            titulo_m = "Aceleración Máxima (AC_MAX)"
            unidad_m = "m/s²"
        else:
            col_metrica, col_ref, col_tec = 'DEC_MAX', 'DEC_MAX_Ref', 'Tecnica_COD'
            titulo_m = "Desaceleración / COD (DEC_MAX)"
            unidad_m = "m/s²"

        st.markdown(f"### ⚽ Análisis por Demarcaciones: {titulo_m}")

        pos_a_mostrar_campo = posiciones_campo if pos_sel_campo == "Todas las Demarcaciones" else [pos_sel_campo]

        if not pos_a_mostrar_campo:
            st.info("No se hallaron demarcaciones asociadas en Posiciones.xlsx para las pruebas de campo.")
        else:
            colores_fechas = ['#00A8E8', '#FF9F1C', '#2ECC71', '#9B59B6', '#E74C3C', '#F1C40F']

            for pos_curr in pos_a_mostrar_campo:
                df_p_c = df_campo[df_campo['Posicion'] == pos_curr].sort_values(['Nombre', 'Fecha_dt']).copy()

                if not df_p_c.empty:
                    col_izq_c, col_der_c = st.columns([7, 3])

                    with col_izq_c:
                        fechas_p_c = sorted(df_p_c['Fecha_dt'].unique())
                        fig_campo = go.Figure()

                        df_p_c['Val_Ant'] = df_p_c.groupby('Nombre')[col_metrica].shift(1)
                        df_p_c['Var_Pct'] = ((df_p_c[col_metrica] - df_p_c['Val_Ant']) / df_p_c['Val_Ant']) * 100

                        jugadores_p_c = df_p_c['Nombre'].unique()

                        for idx_f, f_dt in enumerate(fechas_p_c):
                            f_str = df_p_c[df_p_c['Fecha_dt'] == f_dt]['Fecha'].iloc[0]
                            df_f = df_p_c[df_p_c['Fecha_dt'] == f_dt].set_index('Nombre')

                            vals_y = [df_f.loc[j, col_metrica] if j in df_f.index else None for j in jugadores_p_c]
                            vars_pct = [df_f.loc[j, 'Var_Pct'] if j in df_f.index else None for j in jugadores_p_c]

                            etiquetas = []
                            for v, vp in zip(vals_y, vars_pct):
                                if pd.isna(v): etiquetas.append("")
                                elif pd.isna(vp): etiquetas.append(f"<b>{v:.1f}</b>")
                                else:
                                    signo = "+" if vp > 0 else ""
                                    etiquetas.append(f"<b>{v:.1f}</b><br><i>{signo}{vp:.1f}%</i>")

                            fig_campo.add_trace(go.Bar(
                                x=jugadores_p_c, y=vals_y,
                                name=f"Fecha {f_str}",
                                marker_color=colores_fechas[idx_f % len(colores_fechas)],
                                text=etiquetas,
                                textposition='outside'
                            ))

                        # --- LÍNEA DE REFERENCIA POR POSICIÓN ---
                        ref_val_c = None
                        if df_ref_campo is not None and not df_ref_campo.empty:
                            row_rc = df_ref_campo[df_ref_campo['Posicion'] == pos_curr]
                            if not row_rc.empty and col_ref in row_rc.columns:
                                ref_val_c = row_rc.iloc[0][col_ref]

                        if ref_val_c and pd.notna(ref_val_c):
                            fig_campo.add_shape(
                                type="line", 
                                x0=-0.5, 
                                x1=len(jugadores_p_c)-0.5, 
                                y0=ref_val_c, 
                                y1=ref_val_c, 
                                line=dict(color="#2ECC71", width=3, dash="dash")
                            )
                            fig_campo.add_annotation(
                                x=len(jugadores_p_c)-1, 
                                y=ref_val_c, 
                                text=f"Ref. {pos_curr} ({ref_val_c:.1f} {unidad_m})", 
                                showarrow=False, 
                                font=dict(color="#2ECC71", size=11), 
                                align="right", 
                                yshift=12
                            )

                        val_min = min(df_p_c[col_metrica].min(), (ref_val_c or 0))
                        val_max = max(df_p_c[col_metrica].max(), (ref_val_c or 0))

                        fig_campo.update_layout(
                            title=f"⚽ Demarcación: {pos_curr} - {titulo_m}",
                            barmode='group', template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(tickangle=-45), 
                            yaxis=dict(title=f"Valor ({unidad_m})", range=[min(0, val_min - 2), val_max + 4]),
                            height=440, margin=dict(l=10, r=10, t=50, b=90),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_campo, use_container_width=True)

                    with col_der_c:
                        st.markdown(f"#### 🔍 Biomecánica ({ult_f_campo_str})")
                        df_p_c_ult = df_p_c[df_p_c['Fecha_dt'] == ult_f_campo_dt].copy()

                        def format_cualitativo(val):
                            if pd.isna(val): return "Sin Datos"
                            elif val == 1: return "<span style='color: #E74C3C; font-weight: bold;'>🔴 Malo</span>"
                            elif val == 2: return "<span style='color: #F1C40F; font-weight: bold;'>🟡 Aceptable</span>"
                            elif val == 3: return "<span style='color: #2ECC71; font-weight: bold;'>🟢 Bueno</span>"
                            return str(val)

                        df_p_c_ult['Val_Cualitativa'] = df_p_c_ult[col_tec].apply(format_cualitativo)

                        html_tabla = "<table style='width: 100%; border-collapse: collapse; background-color: rgba(255,255,255,0.03); border-radius: 8px;'>"
                        html_tabla += "<thead><tr style='border-bottom: 2px solid #555; text-align: left;'><th style='padding: 8px;'>Jugador</th><th style='padding: 8px;'>Técnica</th></tr></thead><tbody>"

                        for _, r_t in df_p_c_ult.iterrows():
                            html_tabla += f"<tr style='border-bottom: 1px solid #333;'><td style='padding: 8px;'><b>{r_t['Nombre']}</b></td><td style='padding: 8px;'>{r_t['Val_Cualitativa']}</td></tr>"
                        html_tabla += "</tbody></table>"

                        st.markdown(html_tabla, unsafe_allow_html=True)

                st.markdown("<br><hr>", unsafe_allow_html=True)

# =============================================================================
# ÁREA 8: RANKING GLOBAL (LA LIGA DEL VESTUARIO)
# =============================================================================
elif pest_sel == "🏆 Ranking Global":
    
    if df_pos is None or df_pos.empty:
        st.warning("⚠️ No se encontró la lista de plantilla en 'Posiciones.xlsx'.")
    else:
        conjunto_fechas_dt = set()
        for df_t in [df_mov, df_vam, df_dina, df_saltos, df_dri_sheet, df_fts, df_campo]:
            if df_t is not None and 'Fecha_dt' in df_t.columns:
                conjunto_fechas_dt.update(df_t['Fecha_dt'].dropna().unique())

        fechas_unicas_dt = sorted(list(conjunto_fechas_dt))

        if not fechas_unicas_dt:
            st.warning("⚠️ No hay fechas registradas en los archivos de evaluación.")
        else:
            dict_fechas_str = {f_dt: pd.to_datetime(f_dt).strftime('%d/%m/%Y') for f_dt in fechas_unicas_dt}
            
            col_filt_f, col_spacer = st.columns([2, 2])
            with col_filt_f:
                f_sel_dt = st.selectbox(
                    "📅 Selecciona Fecha de Evaluación para el Ranking:",
                    options=fechas_unicas_dt,
                    index=len(fechas_unicas_dt)-1,
                    format_func=lambda x: dict_fechas_str[x]
                )

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
                    df_m_u['Movilidad_Score'] = df_m_u[['DORSIFLEX_D', 'DORSIFLEX_I', 'ROT_INT_D', 'ROT_INT_I', 'FLEX_CAD_D', 'FLEX_CAD_I', 'LUMBAR']].mean(axis=1)
                    df_rank_base = pd.merge(df_rank_base, df_m_u[['Nombre', 'Movilidad_Score']], on='Nombre', how='left')

            df_v_met = get_metric_hasta_fecha(df_vam, 'VAM')
            if df_v_met is not None:
                df_rank_base = pd.merge(df_rank_base, df_v_met[['Nombre', 'VAM']], on='Nombre', how='left')

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
            if df_dri_met is not None:
                df_rank_base = pd.merge(df_rank_base, df_dri_met[['Nombre', 'DRI']], on='Nombre', how='left')

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
                with c_p1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="podium-1">🥇 1º PUESTO</div>
                        <h2 style='margin:5px 0;'>{j1['Nombre']}</h2>
                        <p style='color:#2ECC71; font-weight:bold; font-size:18px;'>{j1['PUNTOS_TOTALES']} Puntos Totales</p>
                        <small>{j1['Posicion']}</small>
                    </div>
                    """, unsafe_allow_html=True)

            if len(df_rank_base) >= 2:
                j2 = df_rank_base.iloc[1]
                with c_p2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="podium-2">🥈 2º PUESTO</div>
                        <h2 style='margin:5px 0;'>{j2['Nombre']}</h2>
                        <p style='color:#00A8E8; font-weight:bold; font-size:18px;'>{j2['PUNTOS_TOTALES']} Puntos Totales</p>
                        <small>{j2['Posicion']}</small>
                    </div>
                    """, unsafe_allow_html=True)

            if len(df_rank_base) >= 3:
                j3 = df_rank_base.iloc[2]
                with c_p3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="podium-3">🥉 3º PUESTO</div>
                        <h2 style='margin:5px 0;'>{j3['Nombre']}</h2>
                        <p style='color:#FF9F1C; font-weight:bold; font-size:18px;'>{j3['PUNTOS_TOTALES']} Puntos Totales</p>
                        <small>{j3['Posicion']}</small>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br><hr>", unsafe_allow_html=True)

            st.markdown(f"### Clasificación Completa ({f_sel_str})")
            st.caption("Nota: Menos Puntos Totales = Mejor Puesto Global. El número en cada columna representa el lugar obtenido en esa prueba específica (1º = Mejor de la plantilla).")

            df_tabla = df_rank_base.copy()
            def icon_pos(pos):
                if pos == 1: return "🥇 1º"
                elif pos == 2: return "🥈 2º"
                elif pos == 3: return "🥉 3º"
                return f"{pos}º"

            df_tabla['POSICION_GLOBAL'] = df_tabla['POSICION_GLOBAL'].apply(icon_pos)

            cols_mostrar = {
                'POSICION_GLOBAL': 'Posición',
                'Nombre': 'Jugador',
                'PUNTOS_TOTALES': '🏆 Puntos Totales',
                'P_Movilidad': '🩺 Movilidad',
                'P_VAM Aeróbico': '🫁 VAM',
                'P_Dinamometría': '⚙️ Dinamometría',
                'P_Salto CMJ': '🚀 CMJ',
                'P_DRI Drop Jump': '⚡ DRI',
                'P_Tren Superior': '🏋️ Tren Sup.',
                'P_Velocidad VMAX': '⚡ V_MAX',
                'P_Aceleración ACMAX': '⚡ AC_MAX'
            }

            cols_existentes = [c for c in cols_mostrar.keys() if c in df_tabla.columns]
            df_tabla_final = df_tabla[cols_existentes].rename(columns=cols_mostrar)

            st.dataframe(
                df_tabla_final,
                use_container_width=True,
                hide_index=True,
                height=(len(df_tabla_final) + 1) * 38 + 10
            )