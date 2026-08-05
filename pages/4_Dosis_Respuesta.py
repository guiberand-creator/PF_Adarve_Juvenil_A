import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import requests
import io
import plotly.express as px
import plotly.graph_objects as go
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
# 2. MOTOR DE EXTRACCIÓN Y UNIFICACIÓN MULTI-FUENTE
# =============================================================================
def descargar_csv_drive(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return pd.read_csv(io.StringIO(res.text))
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_datos_completos_dosis():
    # 1. RPE
    df_rpe_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "1785642271")
    df_rpe = pd.DataFrame()
    if not df_rpe_raw.empty:
        cols = df_rpe_raw.columns
        col_f = next((c for c in cols if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols[0])
        col_n = next((c for c in cols if 'nombre' in str(c).lower()), cols[1])
        col_t = next((c for c in cols if str(c).lower().strip() == 'tipo de sesión' or 'tipo de sesion' in str(c).lower()), cols[2])
        col_min = next((c for c in cols if 'minuto' in str(c).lower()), cols[3] if len(cols)>3 else None)
        col_c = next((c for c in cols if 'cardio' in str(c).lower()), cols[4] if len(cols)>4 else None)
        col_m = next((c for c in cols if 'muscular' in str(c).lower()), cols[5] if len(cols)>5 else None)

        df_rpe['Fecha'] = pd.to_datetime(df_rpe_raw[col_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_rpe['Nombre_Cruce'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip().str.lower()
        df_rpe['Nombre_Oficial'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip()
        df_rpe['Tipo_Sesion'] = df_rpe_raw[col_t].fillna('Entreno').astype(str).str.strip().str.title()
        
        mins = pd.to_numeric(df_rpe_raw[col_min], errors='coerce').fillna(0) if col_min else 0
        val_c = pd.to_numeric(df_rpe_raw[col_c], errors='coerce').fillna(0) if col_c else 0
        val_m = pd.to_numeric(df_rpe_raw[col_m], errors='coerce').fillna(0) if col_m else 0
        
        df_rpe['Minutos'] = mins
        df_rpe['RPE_G'] = (val_c + val_m) / 2
        df_rpe['sRPE'] = df_rpe['RPE_G'] * df_rpe['Minutos']
        df_rpe = df_rpe.dropna(subset=['Fecha'])

    # 2. GPS
    ruta_gps = os.path.join("data", "GPS")
    df_gps = pd.DataFrame()
    if os.path.exists(ruta_gps):
        archivos = glob.glob(os.path.join(ruta_gps, "*.xlsx"))
        lista_dfs = []
        for f in archivos:
            if "~$" in f: continue
            try:
                df_temp = pd.read_excel(f, sheet_name=1)
                cols_lower = [str(c).lower().strip() for c in df_temp.columns]
                df_temp.columns = cols_lower
                
                def buscar_col(keywords):
                    for c in df_temp.columns:
                        if any(k in c for k in keywords): return c
                    return None
                    
                col_fecha = buscar_col(['fecha', 'date'])
                col_nombre = buscar_col(['nombre', 'name', 'player'])
                col_dt = buscar_col(['distancia total', 'distance'])
                col_18 = buscar_col(['> 18', '>18'])
                col_25 = buscar_col(['> 25', '>25'])
                col_acc = buscar_col(['aceleraciones', 'accel', 'nº aceleraciones'])
                col_dec = buscar_col(['desaceleraciones', 'decel', 'nº desaceleraciones'])
                col_vmax = buscar_col(['v. max', 'v.max', 'top speed'])
                col_acmax = buscar_col(['ac. max', 'acc. max'])
                col_decmax = buscar_col(['dec. max', 'desac. max'])
                col_pload = buscar_col(['player load', 'carga'])
                
                if not col_fecha or not col_nombre: continue
                
                def fix_num(val):
                    try: return float(str(val).replace(',', '.'))
                    except: return 0.0

                df_l = pd.DataFrame()
                df_l['Fecha'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                df_l['Nombre_GPS'] = df_temp[col_nombre].astype(str).str.strip()
                df_l['Nombre_Cruce'] = df_l['Nombre_GPS'].str.lower()
                
                df_l['Dist_Total'] = df_temp[col_dt].apply(fix_num) if col_dt else 0.0
                df_l['Dist_18'] = df_temp[col_18].apply(fix_num) if col_18 else 0.0
                df_l['Dist_25'] = df_temp[col_25].apply(fix_num) if col_25 else 0.0
                df_l['Accels'] = df_temp[col_acc].apply(fix_num) if col_acc else 0.0
                df_l['Decels'] = df_temp[col_dec].apply(fix_num) if col_dec else 0.0
                df_l['V_MAX'] = df_temp[col_vmax].apply(fix_num) if col_vmax else 0.0
                df_l['AC_MAX'] = df_temp[col_acmax].apply(fix_num) if col_acmax else 0.0
                df_l['DEC_MAX'] = df_temp[col_decmax].apply(fix_num) if col_decmax else 0.0
                df_l['Player_Load'] = df_temp[col_pload].apply(fix_num) if col_pload else 0.0

                lista_dfs.append(df_l.dropna(subset=['Fecha']))
            except: continue
                
        if lista_dfs:
            df_gps = pd.concat(lista_dfs, ignore_index=True)
            if df_gps['Dist_Total'].max() < 25: 
                df_gps['Dist_Total'] = df_gps['Dist_Total'] * 1000
                df_gps['Dist_18'] = df_gps['Dist_18'] * 1000
                df_gps['Dist_25'] = df_gps['Dist_25'] * 1000

    if df_gps.empty or df_rpe.empty: return pd.DataFrame()

    # Fusionar GPS + RPE
    df_base = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='inner')
    df_base['Carga_UA'] = (
        df_base['Dist_Total'] + 
        (df_base['Dist_18'] * 2) + 
        (df_base['Dist_25'] * 4) + 
        ((df_base['Accels'] + df_base['Decels']) * 1.5)
    ) * df_base['RPE_G']

    # 3. WELLNESS AL DÍA SIGUIENTE (D+1)
    df_well_raw = descargar_csv_drive("1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s", "0")
    if not df_well_raw.empty:
        cols_w = df_well_raw.columns
        col_wf = next((c for c in cols_w if 'marca' in str(c).lower() or 'fecha' in str(c).lower()), cols_w[0])
        col_wn = next((c for c in cols_w if 'nombre' in str(c).lower()), cols_w[1])
        
        # Sumar ítems de Wellness
        cols_items = [c for c in cols_w if any(k in str(c).lower() for k in ['sueño', 'fatiga', 'estrés', 'agujetas', 'estado'])]
        df_well_raw['Wellness_Total'] = df_well_raw[cols_items].apply(pd.to_numeric, errors='coerce').sum(axis=1) if cols_items else 0
        df_well_raw['Fecha_Well'] = pd.to_datetime(df_well_raw[col_wf], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_well_raw['Nombre_Cruce'] = df_well_raw[col_wn].fillna('Anónimo').astype(str).str.strip().str.lower()
        
        # Calcular fecha del día anterior en el Wellness para emparejar con el día de la sesión
        df_well_raw['Fecha_Sesion_Ref'] = (pd.to_datetime(df_well_raw['Fecha_Well']) - timedelta(days=1)).dt.strftime('%Y-%m-%d')
        
        df_well_clean = df_well_raw.groupby(['Fecha_Sesion_Ref', 'Nombre_Cruce'])['Wellness_Total'].mean().reset_index()
        df_well_clean.rename(columns={'Fecha_Sesion_Ref': 'Fecha', 'Wellness_Total': 'Wellness_D1'}, inplace=True)
        
        df_base = pd.merge(df_base, df_well_clean, on=['Fecha', 'Nombre_Cruce'], how='left')

    # 4. EVALUACIONES CONDICIONALES (CÁLCULO DEL ÚLTIMO DATO REGISTRADO HASTA LA FECHA)
    # A) Peso
    ruta_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    df_peso_eval = pd.read_excel(ruta_peso) if os.path.exists(ruta_peso) else pd.DataFrame()
    if not df_peso_eval.empty:
        df_peso_eval['Fecha_dt'] = pd.to_datetime(df_peso_eval['Fecha'], dayfirst=True, errors='coerce')
        df_peso_eval['Nombre_Cruce'] = df_peso_eval['Nombre'].astype(str).str.strip().str.lower()

    # B) Saltos CMJ y slCMJ
    ruta_saltos = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
    df_saltos_eval = pd.read_excel(ruta_saltos) if os.path.exists(ruta_saltos) else pd.DataFrame()
    if not df_saltos_eval.empty:
        df_saltos_eval['Fecha_dt'] = pd.to_datetime(df_saltos_eval['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_saltos_eval['Nombre_Cruce'] = df_saltos_eval['Nombre'].astype(str).str.strip().str.lower()

    # C) DRI Drop Jump
    df_dri_sheet = descargar_csv_drive("1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y", "0")
    if not df_dri_sheet.empty and 'DRI' in df_dri_sheet.columns:
        df_dri_sheet['Fecha_dt'] = pd.to_datetime(df_dri_sheet['Fecha_Hora'].astype(str).str.split('_').str[0], errors='coerce')
        df_dri_sheet['Nombre_Cruce'] = df_dri_sheet['Nombre'].astype(str).str.strip().str.lower()

    # D) VAM Aeróbico
    ruta_vam = os.path.join("data", "EVALUACIONES", "AEROBICO", "AEROBICO_5MIN.xlsx")
    df_vam_eval = pd.read_excel(ruta_vam) if os.path.exists(ruta_vam) else pd.DataFrame()
    if not df_vam_eval.empty:
        df_vam_eval['Fecha_dt'] = pd.to_datetime(df_vam_eval['Fecha'], dayfirst=True, errors='coerce')
        df_vam_eval['Nombre_Cruce'] = df_vam_eval['Nombre'].astype(str).str.strip().str.lower()

    # Fusión inteligente del último test condicional a la fecha de la sesión
    lst_peso, lst_cmj, lst_slcmj, lst_dri, lst_vam = [], [], [], [], []

    for _, row in df_base.iterrows():
        f_dt = pd.to_datetime(row['Fecha'])
        nom = row['Nombre_Cruce']
        
        # Peso
        p_val = np.nan
        if not df_peso_eval.empty:
            sub = df_peso_eval[(df_peso_eval['Nombre_Cruce'] == nom) & (df_peso_eval['Fecha_dt'] <= f_dt)]
            if not sub.empty: p_val = sub.sort_values('Fecha_dt').iloc[-1]['Peso']
        lst_peso.append(p_val)
        
        # CMJ y slCMJ
        cmj_val, slcmj_val = np.nan, np.nan
        if not df_saltos_eval.empty:
            sub = df_saltos_eval[(df_saltos_eval['Nombre_Cruce'] == nom) & (df_saltos_eval['Fecha_dt'] <= f_dt)]
            if not sub.empty:
                ult_f = sub['Fecha_dt'].max()
                sub_u = sub[sub['Fecha_dt'] == ult_f]
                
                cmj_m = sub_u[sub_u['Tipo'].astype(str).str.upper() == 'CMJ']['Altura'].mean()
                if pd.notna(cmj_m): cmj_val = cmj_m
                
                sr = sub_u[sub_u['Tipo'].astype(str).str.lower() == 'slcmjright']['Altura'].mean()
                sl = sub_u[sub_u['Tipo'].astype(str).str.lower() == 'slcmjleft']['Altura'].mean()
                if pd.notna(sr) and pd.notna(sl): slcmj_val = (sr + sl) / 2
                elif pd.notna(sr): slcmj_val = sr
                elif pd.notna(sl): slcmj_val = sl
        lst_cmj.append(cmj_val)
        lst_slcmj.append(slcmj_val)
        
        # DRI
        dri_val = np.nan
        if not df_dri_sheet.empty and 'DRI' in df_dri_sheet.columns:
            sub = df_dri_sheet[(df_dri_sheet['Nombre_Cruce'] == nom) & (df_dri_sheet['Fecha_dt'] <= f_dt)]
            if not sub.empty: dri_val = sub.sort_values('Fecha_dt').iloc[-1]['DRI']
        lst_dri.append(dri_val)
        
        # VAM
        vam_val = np.nan
        if not df_vam_eval.empty:
            sub = df_vam_eval[(df_vam_eval['Nombre_Cruce'] == nom) & (df_vam_eval['Fecha_dt'] <= f_dt)]
            if not sub.empty: vam_val = sub.sort_values('Fecha_dt').iloc[-1]['VAM']
        lst_vam.append(vam_val)

    df_base['Peso_Eval'] = lst_peso
    df_base['CMJ_Eval'] = lst_cmj
    df_base['slCMJ_Eval'] = lst_slcmj
    df_base['DRI_Eval'] = lst_dri
    df_base['VAM_Eval'] = lst_vam

    return df_base

df_dosis = cargar_datos_completos_dosis()

# =============================================================================
# 3. INTERFAZ Y GRÁFICO 1: MATRIZ DOSIS - RESPUESTA (DISPERSIÓN)
# =============================================================================
st.markdown("""
    <div>
        <h1 style="margin-bottom: 0px;">DOSIS - RESPUESTA</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin-top: 5px;">Relación entre la Carga Externa Ponderada (UA) y la Carga Interna Percibida (sRPE).</p>
    </div>
""", unsafe_allow_html=True)

if df_dosis.empty:
    st.info("🚧 No hay suficientes datos coincidentes de GPS y RPE para construir la relación Dosis-Respuesta.")
    st.stop()

st.markdown("---")

c_f1, c_f2 = st.columns([1, 2.5])
with c_f1:
    tipos_sesion = ["Todos"] + sorted(list(df_dosis['Tipo_Sesion'].unique()))
    tipo_sel = st.selectbox("⚽ Tipo de Sesión:", tipos_sesion)

with c_f2:
    fechas_dt_unicas = sorted([datetime.strptime(f, '%Y-%m-%d').date() for f in df_dosis['Fecha'].unique()])
    min_date_val, max_date_val = fechas_dt_unicas[0], fechas_dt_unicas[-1]
    
    rango_slider = st.slider(
        "📅 Rango de Fechas:",
        min_value=min_date_val,
        max_value=max_date_val,
        value=(min_date_val, max_date_val),
        format="DD/MM/YYYY"
    )

df_filtrado = df_dosis.copy()

if tipo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Tipo_Sesion'] == tipo_sel]

if len(rango_slider) == 2:
    f_ini_str = rango_slider[0].strftime('%Y-%m-%d')
    f_fin_str = rango_slider[1].strftime('%Y-%m-%d')
    df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= f_ini_str) & (df_filtrado['Fecha'] <= f_fin_str)]

c_info_f, c_btn = st.columns([3, 1])
with c_info_f:
    if st.session_state.jugadores_seleccionados_dosis:
        st.markdown(f"🏃 **Filtrado por jugador(es):** `{', '.join(st.session_state.jugadores_seleccionados_dosis)}`")
    else:
        st.caption("💡 Haz clic sobre los círculos del gráfico para filtrar/aislar a esos jugadores.")

with c_btn:
    if st.session_state.jugadores_seleccionados_dosis:
        if st.button("🧹 Limpiar Selección", use_container_width=True):
            st.session_state.jugadores_seleccionados_dosis = []
            st.session_state.dosis_key += 1
            st.rerun()

if st.session_state.jugadores_seleccionados_dosis:
    df_grafico = df_filtrado[df_filtrado['Nombre_Oficial'].isin(st.session_state.jugadores_seleccionados_dosis)]
else:
    df_grafico = df_filtrado.copy()

if df_grafico.empty:
    st.warning("No hay registros para los filtros seleccionados.")
    st.stop()

# Scatter Plot
media_srpe = df_filtrado['sRPE'].mean()
media_ua = df_filtrado['Carga_UA'].mean()

fig = px.scatter(
    df_grafico,
    x="sRPE",
    y="Carga_UA",
    color="Nombre_Oficial",
    custom_data=["Nombre_Oficial", "Fecha", "Tipo_Sesion"],
    hover_data=["Fecha", "Tipo_Sesion", "Minutos", "RPE_G", "Dist_Total"],
    labels={
        "sRPE": "Carga Interna (sRPE) → [RPE * Duración]",
        "Carga_UA": "Carga Externa Ponderada (UA) ↑",
        "Nombre_Oficial": "Jugador"
    },
    template="plotly_dark"
)

fig.update_traces(marker=dict(size=14, line=dict(width=1, color='White')))
fig.add_vline(x=media_srpe, line=dict(color="#F1C40F", width=1.5, dash="dash"))
fig.add_hline(y=media_ua, line=dict(color="#F1C40F", width=1.5, dash="dash"))

fig.update_layout(
    height=550,
    plot_bgcolor='rgba(0,0,0,0.2)',
    paper_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(l=20, r=20, t=30, b=80)
)

dosis_chart_key = f"dosis_chart_{st.session_state.dosis_key}"
try:
    seleccion_dosis = st.plotly_chart(
        fig,
        use_container_width=True,
        config={'displayModeBar': False},
        on_select="rerun",
        selection_mode=["points", "box", "lasso"],
        key=dosis_chart_key
    )
    
    if seleccion_dosis and hasattr(seleccion_dosis, 'selection'):
        pts = getattr(seleccion_dosis.selection, 'points', [])
        cambio = False
        for p in pts:
            cd = p.get('customdata')
            if cd:
                nom_j = cd[0] if isinstance(cd, list) else cd
                if nom_j not in st.session_state.jugadores_seleccionados_dosis:
                    st.session_state.jugadores_seleccionados_dosis.append(nom_j)
                    cambio = True
        if cambio:
            st.session_state.dosis_key += 1
            st.rerun()
except Exception:
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# =============================================================================
# 4. GRÁFICO 2: MATRIZ DE CORRELACIONES DE PEARSON (HEATMAP)
# =============================================================================
st.markdown("---")
st.markdown("### 📊 Matriz de Correlaciones Integrada (Pearson)")
st.caption("Muestra la fuerza de relación (-1.0 a +1.0) entre la Carga Interna (sRPE), el Recuperación/Wellness (D+1), el GPS de la sesión y las Evaluaciones Físicas.")

# Mapeo de nombres limpios para el Heatmap
dict_cols_corr = {
    'sRPE': 'sRPE (Sesión)',
    'Wellness_D1': 'Wellness (D+1)',
    'Dist_18': 'Distancia >18 km/h',
    'V_MAX': 'Velocidad Máx (GPS)',
    'AC_MAX': 'Acel Máx (GPS)',
    'DEC_MAX': 'Desac Máx (GPS)',
    'Player_Load': 'Player Load',
    'Peso_Eval': 'Peso (kg)',
    'CMJ_Eval': 'CMJ Bilateral',
    'slCMJ_Eval': 'slCMJ Unilateral',
    'DRI_Eval': 'DRI (Drop Jump)',
    'VAM_Eval': 'VAM (km/h)'
}

cols_existentes = [c for c in dict_cols_corr.keys() if c in df_grafico.columns]
df_corr_sub = df_grafico[cols_existentes].rename(columns=dict_cols_corr)

# Calcular matriz de Pearson
matriz_corr = df_corr_sub.corr(method='pearson')

if not matriz_corr.empty:
    fig_corr = px.imshow(
        matriz_corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        range_color=[-1, 1],
        title="Matriz de Correlación de Pearson"
    )

    fig_corr.update_layout(
        height=550,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=50)
    )

    st.plotly_chart(fig_corr, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("No hay suficientes pares de datos para calcular la matriz de correlaciones.")