import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import requests
import io
import plotly.express as px
from datetime import datetime, timedelta
from utils import aplicar_diseno_responsive

# =============================================================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# =============================================================================
aplicar_diseno_responsive()

st.set_page_config(
    page_title="Dosis - Respuesta | Adarve DH",
    page_icon="⚡",
    layout="wide"
)

if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
    st.stop()

_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        import base64
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

if 'jugadores_seleccionados_dosis' not in st.session_state:
    st.session_state.jugadores_seleccionados_dosis = []
if 'dosis_key' not in st.session_state:
    st.session_state.dosis_key = 0

# =============================================================================
# 2. MOTOR DE EXTRACCIÓN Y FUSIÓN DE DATOS (VECTORIZADO)
# =============================================================================
def descargar_csv_drive(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200: return pd.read_csv(io.StringIO(res.text))
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_matriz_completa():
    # 1. CARGAR RPE
    df_rpe_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    df_rpe = pd.DataFrame()
    if not df_rpe_raw.empty:
        cols = df_rpe_raw.columns
        col_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        col_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        col_t = next((c for c in cols if 'tipo de sesi' in str(c).lower()), cols[2])
        col_min = next((c for c in cols if 'minuto' in str(c).lower()), cols[3] if len(cols)>3 else None)
        col_c = next((c for c in cols if 'cardio' in str(c).lower()), cols[4] if len(cols)>4 else None)
        col_m = next((c for c in cols if 'muscular' in str(c).lower()), cols[5] if len(cols)>5 else None)

        df_rpe['Fecha'] = pd.to_datetime(df_rpe_raw[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_rpe['Nombre_Cruce'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip().str.lower()
        df_rpe['Nombre_Oficial'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip()
        df_rpe['Tipo_Sesion'] = df_rpe_raw[col_t].fillna('Entreno').astype(str).str.strip().str.title()
        
        mins = pd.to_numeric(df_rpe_raw[col_min], errors='coerce').fillna(0) if col_min else 0
        df_rpe['Minutos'] = mins
        df_rpe['RPE_G'] = (pd.to_numeric(df_rpe_raw[col_c], errors='coerce').fillna(0) + pd.to_numeric(df_rpe_raw[col_m], errors='coerce').fillna(0)) / 2
        df_rpe['sRPE'] = df_rpe['RPE_G'] * df_rpe['Minutos']
        df_rpe = df_rpe.dropna(subset=['Fecha'])

    # 2. CARGAR GPS
    ruta_gps = os.path.join("data", "GPS")
    df_gps = pd.DataFrame()
    if os.path.exists(ruta_gps):
        archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
        lista_dfs = []
        for f in archivos:
            if "~$" in f: continue
            try:
                df_t = pd.read_excel(f, sheet_name=1)
                df_t.columns = [str(c).lower().strip() for c in df_t.columns]
                
                def b_col(keys): return next((c for c in df_t.columns if any(k in c for k in keys)), None)
                
                cf, cn = b_col(['fecha', 'date']), b_col(['nombre', 'player'])
                if not cf or not cn: continue
                
                def fn(v):
                    try: return float(str(v).replace(',', '.'))
                    except: return 0.0

                df_l = pd.DataFrame()
                df_l['Fecha'] = pd.to_datetime(df_t[cf], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                df_l['Nombre_Cruce'] = df_t[cn].astype(str).str.strip().str.lower()
                df_l['Dist_Total'] = df_t[b_col(['distancia total', 'distance'])].apply(fn) if b_col(['distancia total', 'distance']) else 0.0
                df_l['Dist_18'] = df_t[b_col(['> 18', '>18'])].apply(fn) if b_col(['> 18', '>18']) else 0.0
                df_l['Dist_25'] = df_t[b_col(['> 25', '>25'])].apply(fn) if b_col(['> 25', '>25']) else 0.0
                df_l['Accels'] = df_t[b_col(['aceleraciones', 'accel'])].apply(fn) if b_col(['aceleraciones', 'accel']) else 0.0
                df_l['Decels'] = df_t[b_col(['desaceleraciones', 'decel'])].apply(fn) if b_col(['desaceleraciones', 'decel']) else 0.0
                df_l['V_MAX'] = df_t[b_col(['v. max', 'v.max', 'top speed'])].apply(fn) if b_col(['v. max', 'v.max', 'top speed']) else 0.0
                df_l['AC_MAX'] = df_t[b_col(['ac. max', 'acc. max'])].apply(fn) if b_col(['ac. max', 'acc. max']) else 0.0
                df_l['DEC_MAX'] = df_t[b_col(['dec. max', 'desac. max'])].apply(fn) if b_col(['dec. max', 'desac. max']) else 0.0
                df_l['Player_Load'] = df_t[b_col(['player load', 'carga'])].apply(fn) if b_col(['player load', 'carga']) else 0.0

                lista_dfs.append(df_l.dropna(subset=['Fecha']))
            except: continue
                
        if lista_dfs:
            df_gps = pd.concat(lista_dfs, ignore_index=True)
            if df_gps['Dist_Total'].max() < 25: 
                df_gps['Dist_Total'] *= 1000
                df_gps['Dist_18'] *= 1000
                df_gps['Dist_25'] *= 1000

    if df_gps.empty or df_rpe.empty: return pd.DataFrame()

    # FUSIÓN BASE: GPS + RPE
    df_base = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='inner')
    df_base['Carga_UA'] = (df_base['Dist_Total'] + (df_base['Dist_18']*2) + (df_base['Dist_25']*4) + ((df_base['Accels']+df_base['Decels'])*1.5)) * df_base['RPE_G']
    df_base['Fecha_dt'] = pd.to_datetime(df_base['Fecha'])
    df_base = df_base.sort_values('Fecha_dt')

    # 3. AÑADIR WELLNESS D+1
    df_w_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "0")
    if not df_w_raw.empty:
        cw = df_w_raw.columns
        cw_f, cw_n = cw[0], cw[1]
        c_items = [c for c in cw if any(k in str(c).lower() for k in ['sueño', 'fatiga', 'estrés', 'agujetas', 'estado'])]
        df_w_raw['Wellness'] = df_w_raw[c_items].apply(pd.to_numeric, errors='coerce').sum(axis=1) if c_items else 0
        df_w_raw['Fecha_W'] = pd.to_datetime(df_w_raw[cw_f], dayfirst=True, errors='coerce')
        df_w_raw['Nombre_Cruce'] = df_w_raw[cw_n].fillna('').astype(str).str.strip().str.lower()
        # Restar 1 día para cruzar la nota de mañana con la sesión de hoy
        df_w_raw['Fecha'] = (df_w_raw['Fecha_W'] - timedelta(days=1)).dt.strftime('%Y-%m-%d')
        df_w_clean = df_w_raw.groupby(['Fecha', 'Nombre_Cruce'])['Wellness'].mean().reset_index()
        df_base = pd.merge(df_base, df_w_clean, on=['Fecha', 'Nombre_Cruce'], how='left')

    # 4. AÑADIR EVALUACIONES FÍSICAS (Último test previo a la sesión)
    def cruzar_evaluacion(df_eval, col_valor, nuevo_nombre):
        if not df_eval.empty and col_valor in df_eval.columns:
            df_eval = df_eval.dropna(subset=['Fecha_dt']).sort_values('Fecha_dt')
            df_eval['Nombre_Cruce'] = df_eval['Nombre'].astype(str).str.strip().str.lower()
            df_res = pd.merge_asof(df_base[['Fecha_dt', 'Nombre_Cruce']], df_eval[['Fecha_dt', 'Nombre_Cruce', col_valor]], on='Fecha_dt', by='Nombre_Cruce', direction='backward')
            return df_res[col_valor].rename(nuevo_nombre)
        return np.nan

    # A) Peso
    r_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    if os.path.exists(r_peso):
        d_p = pd.read_excel(r_peso)
        d_p['Fecha_dt'] = pd.to_datetime(d_p['Fecha'], dayfirst=True, errors='coerce')
        df_base['Peso_Eval'] = cruzar_evaluacion(d_p, 'Peso', 'Peso_Eval')
    
    # B) VAM
    r_vam = os.path.join("data", "EVALUACIONES", "AEROBICO", "AEROBICO_5MIN.xlsx")
    if os.path.exists(r_vam):
        d_v = pd.read_excel(r_vam)
        d_v['Fecha_dt'] = pd.to_datetime(d_v['Fecha'], dayfirst=True, errors='coerce')
        df_base['VAM_Eval'] = cruzar_evaluacion(d_v, 'VAM', 'VAM_Eval')

   # C) Saltos (CMJ y slCMJ)
    r_saltos = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
    if os.path.exists(r_saltos):
        try:
            d_s = pd.read_excel(r_saltos)
            
            # Buscamos los nombres reales de las columnas en tu Excel dinámicamente
            c_fecha = next((c for c in d_s.columns if 'fecha' in str(c).lower()), 'Fecha')
            c_nombre = next((c for c in d_s.columns if 'nombre' in str(c).lower() or 'jugador' in str(c).lower()), 'Nombre')
            c_altura = next((c for c in d_s.columns if 'altura' in str(c).lower()), 'Altura')
            c_tipo = next((c for c in d_s.columns if 'tipo' in str(c).lower()), 'Tipo')
            
            # Estandarizamos los nombres internamente para que el código no falle
            d_s = d_s.rename(columns={c_nombre: 'Nombre', c_altura: 'Altura', c_tipo: 'Tipo'})
            d_s['Fecha_dt'] = pd.to_datetime(d_s[c_fecha].astype(str).str.split('_').str[0], errors='coerce')
            
            d_cmj = d_s[d_s['Tipo'].astype(str).str.upper() == 'CMJ']
            d_sl = d_s[d_s['Tipo'].astype(str).str.lower().str.contains('slcmj', na=False)].groupby(['Fecha_dt', 'Nombre'])['Altura'].mean().reset_index()
            
            df_base['CMJ_Eval'] = cruzar_evaluacion(d_cmj, 'Altura', 'CMJ_Eval')
            df_base['slCMJ_Eval'] = cruzar_evaluacion(d_sl, 'Altura', 'slCMJ_Eval')
        except Exception:
            pass # Si el Excel tiene un formato inesperado, no romperá el resto de la app

    # D) DRI
    d_dri = descargar_csv_drive("1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y", "0")
    if not d_dri.empty and 'DRI' in d_dri.columns:
        d_dri['Fecha_dt'] = pd.to_datetime(d_dri['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_base['DRI_Eval'] = cruzar_evaluacion(d_dri, 'DRI', 'DRI_Eval')

    return df_base

df_dosis = cargar_matriz_completa()

# =============================================================================
# 3. INTERFAZ Y FILTROS
# =============================================================================
st.markdown("""
    <div>
        <h1 style="margin-bottom: 0px;">DOSIS - RESPUESTA</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Relación entre la Carga Externa Ponderada (UA) y la Carga Interna Percibida (sRPE).</p>
    </div>
""", unsafe_allow_html=True)

if df_dosis.empty:
    st.info("🚧 No hay suficientes datos coincidentes para construir la relación Dosis-Respuesta.")
    st.stop()

st.markdown("---")

c_f1, c_f2 = st.columns([1, 2.5])
with c_f1:
    tipo_sel = st.selectbox("⚽ Tipo de Sesión:", ["Todos"] + sorted(list(df_dosis['Tipo_Sesion'].unique())))
with c_f2:
    f_uni = sorted(df_dosis['Fecha_dt'].dropna().dt.date.unique())
    rango_s = st.slider("📅 Rango de Fechas:", min_value=f_uni[0], max_value=f_uni[-1], value=(f_uni[0], f_uni[-1]), format="DD/MM/YYYY")

df_f = df_dosis.copy()
if tipo_sel != "Todos": df_f = df_f[df_f['Tipo_Sesion'] == tipo_sel]
df_f = df_f[(df_f['Fecha_dt'].dt.date >= rango_s[0]) & (df_f['Fecha_dt'].dt.date <= rango_s[1])]

c_i, c_b = st.columns([3, 1])
with c_i:
    if st.session_state.jugadores_seleccionados_dosis: st.markdown(f"🏃 **Filtrado:** `{', '.join(st.session_state.jugadores_seleccionados_dosis)}`")
    else: st.caption("💡 Haz clic en los puntos del gráfico para filtrar jugadores.")
with c_b:
    if st.session_state.jugadores_seleccionados_dosis and st.button("🧹 Limpiar", use_container_width=True):
        st.session_state.jugadores_seleccionados_dosis = []
        st.session_state.dosis_key += 1
        st.rerun()

df_g = df_f[df_f['Nombre_Oficial'].isin(st.session_state.jugadores_seleccionados_dosis)] if st.session_state.jugadores_seleccionados_dosis else df_f.copy()

if df_g.empty:
    st.warning("No hay registros.")
    st.stop()

# =============================================================================
# 4. GRÁFICO 1: DISPERSIÓN DOSIS-RESPUESTA
# =============================================================================
fig = px.scatter(
    df_g, x="sRPE", y="Carga_UA", color="Nombre_Oficial", custom_data=["Nombre_Oficial"],
    hover_data=["Fecha", "Tipo_Sesion", "Minutos", "RPE_G", "Dist_Total"],
    labels={"sRPE": "Carga Interna (sRPE)", "Carga_UA": "Carga Externa (UA)", "Nombre_Oficial": "Jugador"}, template="plotly_dark"
)
fig.update_traces(marker=dict(size=14, line=dict(width=1, color='White')))
fig.add_vline(x=df_f['sRPE'].mean(), line=dict(color="#F1C40F", width=1.5, dash="dash"))
fig.add_hline(y=df_f['Carga_UA'].mean(), line=dict(color="#F1C40F", width=1.5, dash="dash"))
fig.update_layout(height=550, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.2)', margin=dict(l=20, r=20, t=30, b=80), legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5))

try:
    s_d = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode=["points"], key=f"d_k_{st.session_state.dosis_key}")
    if s_d and hasattr(s_d, 'selection'):
        cambio = False
        for p in getattr(s_d.selection, 'points', []):
            if p.get('customdata') and p['customdata'][0] not in st.session_state.jugadores_seleccionados_dosis:
                st.session_state.jugadores_seleccionados_dosis.append(p['customdata'][0])
                cambio = True
        if cambio:
            st.session_state.dosis_key += 1
            st.rerun()
except: st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# 5. GRÁFICO 2: MATRIZ DE CORRELACIONES INTEGRADA
# =============================================================================
st.markdown("---")
st.markdown("### 📊 Matriz de Correlaciones Integrada (Pearson)")

dic_c = {
    'sRPE': 'sRPE (Sesión)', 'Wellness': 'Wellness (D+1)', 'Dist_18': 'Dist >18 km/h',
    'V_MAX': 'Velocidad Máx', 'AC_MAX': 'Acel Máx', 'DEC_MAX': 'Desac Máx', 'Player_Load': 'Player Load',
    'Peso_Eval': 'Peso (kg)', 'CMJ_Eval': 'CMJ Bilateral', 'slCMJ_Eval': 'slCMJ Unilateral', 'DRI_Eval': 'DRI', 'VAM_Eval': 'VAM'
}

cols = [c for c in dic_c.keys() if c in df_g.columns]
if len(cols) > 1:
    m_corr = df_g[cols].rename(columns=dic_c).corr()
    f_c = px.imshow(m_corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", range_color=[-1, 1])
    f_c.update_layout(height=550, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=40, b=50))
    st.plotly_chart(f_c, use_container_width=True)
else: st.info("Datos insuficientes para la matriz.")