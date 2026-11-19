import streamlit as st
import pandas as pd
import numpy as np
import glob
import requests
import io
import plotly.express as px
from datetime import datetime, timedelta
import os
import re
import plotly.graph_objects as go
from utils import (descargar_sheet, comprobar_descargas, configurar_pagina, exigir_login_staff, controles_sidebar, render_html, tarjetas_kpi, bloque_alerta,
                   nombre_bonito, estilo_fig, mostrar_fig, ROJO, NARANJA, AZUL, ACENTO, NEUTRO, NEUTRO_TEXTO, TEXTO)

# =============================================================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# =============================================================================
configurar_pagina("Dosis - Respuesta | Adarve DH")
exigir_login_staff()
movil = controles_sidebar()
Z_RESIDUO = 2.0   # sesiones con respuesta (sRPE) muy por encima de lo esperado para su carga externa

if 'jugadores_seleccionados_dosis' not in st.session_state:
    st.session_state.jugadores_seleccionados_dosis = []
if 'dosis_key' not in st.session_state:
    st.session_state.dosis_key = 0

def norm_cruce(texto):
    if pd.isna(texto): return ""
    return " ".join(str(texto).replace('_', ' ').strip().lower().split())

# =============================================================================
# 2. MOTOR DE EXTRACCIÓN Y FUSIÓN DE DATOS
# =============================================================================
def descargar_csv_drive(sheet_id, gid=None):
    return descargar_sheet(sheet_id, gid)   # utils.py: tiempo límite + reintento

@st.cache_data(ttl=600)
def cargar_matriz_completa():
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
        col_animo = next((c for c in cols if any(k in str(c).lower() for k in ['animo', 'ánimo', 'estado'])), None)

        df_rpe['Fecha_dt'] = pd.to_datetime(df_rpe_raw[col_f], dayfirst=True, errors='coerce')
        df_rpe['Fecha'] = df_rpe['Fecha_dt'].dt.strftime('%Y-%m-%d')
        df_rpe['Fecha_Date'] = df_rpe['Fecha_dt'].dt.date
        df_rpe['Nombre_Cruce'] = df_rpe_raw[col_n].fillna('Anónimo').apply(norm_cruce)
        df_rpe['Nombre_Oficial'] = df_rpe_raw[col_n].fillna('Anónimo').astype(str).str.strip()
        df_rpe['Tipo_Sesion'] = df_rpe_raw[col_t].fillna('Entreno').astype(str).str.strip().str.title()
        
        df_rpe['Minutos'] = pd.to_numeric(df_rpe_raw[col_min], errors='coerce').fillna(0) if col_min else 0
        df_rpe['RPE_G'] = pd.concat([pd.to_numeric(df_rpe_raw[col_c], errors='coerce'),
                                     pd.to_numeric(df_rpe_raw[col_m], errors='coerce')], axis=1).mean(axis=1, skipna=True)
        df_rpe['sRPE'] = df_rpe['RPE_G'] * df_rpe['Minutos']
        df_rpe['Estado_Animo'] = pd.to_numeric(df_rpe_raw[col_animo], errors='coerce') if col_animo else np.nan
        
        df_rpe = df_rpe.dropna(subset=['Fecha_dt'])

    if not df_rpe.empty:
        df_rpe_daily = df_rpe.groupby(['Fecha_Date', 'Nombre_Cruce'], as_index=False)['sRPE'].sum()
        df_rpe_daily['Fecha_Date'] = df_rpe_daily['Fecha_Date'].apply(lambda d: d + timedelta(days=1) if pd.notna(d) else d)
        df_rpe_daily.rename(columns={'sRPE': 'sRPE_prev'}, inplace=True)
        df_rpe = pd.merge(df_rpe, df_rpe_daily[['Fecha_Date', 'Nombre_Cruce', 'sRPE_prev']], on=['Fecha_Date', 'Nombre_Cruce'], how='left')

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
                df_l['Nombre_Cruce'] = df_t[cn].apply(norm_cruce)
                df_l['Dist_Total'] = df_t[b_col(['distancia total', 'distance'])].apply(fn) if b_col(['distancia total', 'distance']) else 0.0
                df_l['Dist_18'] = df_t[b_col(['> 18', '>18'])].apply(fn) if b_col(['> 18', '>18']) else 0.0
                df_l['Dist_25'] = df_t[b_col(['> 25', '>25'])].apply(fn) if b_col(['> 25', '>25']) else 0.0
                accels = df_t[b_col(['aceleraciones', 'accel'])].apply(fn) if b_col(['aceleraciones', 'accel']) else 0.0
                decels = df_t[b_col(['desaceleraciones', 'decel'])].apply(fn) if b_col(['desaceleraciones', 'decel']) else 0.0
                df_l['Acc_Dec'] = accels + decels  
                df_l['V_MAX'] = df_t[b_col(['v. max', 'v.max', 'top speed'])].apply(fn) if b_col(['v. max', 'v.max', 'top speed']) else 0.0
                df_l['AC_MAX'] = df_t[b_col(['ac. max', 'acc. max'])].apply(fn) if b_col(['ac. max', 'acc. max']) else 0.0
                df_l['DEC_MAX'] = df_t[b_col(['dec. max', 'desac. max'])].apply(fn) if b_col(['dec. max', 'desac. max']) else 0.0

                lista_dfs.append(df_l.dropna(subset=['Fecha']))
            except: continue
                
        if lista_dfs:
            df_gps = pd.concat(lista_dfs, ignore_index=True)
            if not df_gps.empty and df_gps['Dist_Total'].max() < 25: 
                df_gps['Dist_Total'] *= 1000
                df_gps['Dist_18'] *= 1000
                df_gps['Dist_25'] *= 1000

    if df_gps.empty or df_rpe.empty: return pd.DataFrame()
    df_base = pd.merge(df_gps, df_rpe, on=['Fecha', 'Nombre_Cruce'], how='inner')
    # CORRECCIÓN: la carga EXTERNA ya no se multiplica por el RPE (si no, se correlaciona consigo misma)
    df_base['Carga_UA'] = df_base['Dist_Total'] + (df_base['Dist_18'] * 2) + (df_base['Dist_25'] * 4) + (df_base['Acc_Dec'] * 1.5)
    df_base['Fecha_dt'] = pd.to_datetime(df_base['Fecha'])
    df_base = df_base.sort_values('Fecha_dt').reset_index(drop=True)

    # CORRECCIÓN: el wellness se lee de SU hoja (antes se leía la hoja del RPE y la columna salía vacía)
    df_w_raw = descargar_csv_drive("12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o", "1891505901")
    if not df_w_raw.empty:
        cw = [str(c).strip() for c in df_w_raw.columns]
        df_w_raw.columns = cw
        up = {c: c.upper().replace('É', 'E').replace('Ú', 'U') for c in cw}
        c_f = next((c for c in cw if 'marca' in c.lower()), cw[0])
        c_n = next((c for c in cw if 'nombre' in c.lower()), cw[1])
        c_items = [c for c in cw if up[c].startswith(('SUE', 'DOLOR', 'ESTRES', 'CARGA'))]
        if c_items:
            df_w_raw['Wellness'] = df_w_raw[c_items].apply(pd.to_numeric, errors='coerce').mean(axis=1, skipna=True)
            df_w_raw['Fecha'] = pd.to_datetime(df_w_raw[c_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            df_w_raw['Nombre_Cruce'] = df_w_raw[c_n].apply(norm_cruce)
            df_w_clean = df_w_raw.groupby(['Fecha', 'Nombre_Cruce'])['Wellness'].mean().reset_index()
            df_base = pd.merge(df_base, df_w_clean, on=['Fecha', 'Nombre_Cruce'], how='left')

    # CORRECCIÓN: el resultado del partido sale del CALENDARIO (antes se tomaba la columna de minutos)
    df_cal = descargar_csv_drive("1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5", "1771990969")
    df_base['Resultado_Partido'] = np.nan
    if not df_cal.empty:
        cc = df_cal.columns
        c_f = next((c for c in cc if 'fecha' in str(c).lower()), None)
        c_cf = next((c for c in cc if 'casa' in str(c).lower() or 'fuera' in str(c).lower()), None)
        c_r = next((c for c in cc if 'resultado' in str(c).lower()), None)
        if c_f and c_cf and c_r:
            def puntos(row):
                m = re.search(r'(\d+)\s*[-:\s_xX]\s*(\d+)', str(row[c_r]))
                if not m: return np.nan
                gl, gv = int(m.group(1)), int(m.group(2))
                casa = 'casa' in str(row[c_cf]).lower() or 'local' in str(row[c_cf]).lower()
                a, b = (gl, gv) if casa else (gv, gl)
                return 3.0 if a > b else (1.0 if a == b else 0.0)
            df_cal['Fecha'] = pd.to_datetime(df_cal[c_f], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            df_cal['Puntos'] = df_cal.apply(puntos, axis=1)
            mapa = df_cal.dropna(subset=['Fecha']).set_index('Fecha')['Puntos'].to_dict()
            df_base['Resultado_Partido'] = df_base['Fecha'].map(mapa)

    def cruzar_evaluacion(df_eval, col_valor, nuevo_nombre):
        if not df_eval.empty and col_valor in df_eval.columns:
            df_ev = df_eval.dropna(subset=['Fecha_dt']).copy()
            c_nom = next((c for c in df_ev.columns if 'nombre' in str(c).lower() or 'jugador' in str(c).lower()), 'Nombre')
            df_ev['Nombre_Cruce'] = df_ev[c_nom].apply(norm_cruce)
            df_ev[col_valor] = pd.to_numeric(df_ev[col_valor], errors='coerce')
            df_ev = df_ev.dropna(subset=[col_valor]).sort_values('Fecha_dt')
            if not df_ev.empty:
                df_res = pd.merge_asof(
                    df_base[['Fecha_dt', 'Nombre_Cruce']].sort_values('Fecha_dt'), 
                    df_ev[['Fecha_dt', 'Nombre_Cruce', col_valor]], 
                    on='Fecha_dt', by='Nombre_Cruce', direction='backward'
                )
                return df_res[col_valor].rename(nuevo_nombre)
        return pd.Series(np.nan, index=df_base.index)

    r_peso = os.path.join("data", "EVALUACIONES", "PESO", "PESO.xlsx")
    if os.path.exists(r_peso):
        try:
            d_p = pd.read_excel(r_peso)
            c_fecha = next((c for c in d_p.columns if 'fecha' in str(c).lower()), 'Fecha')
            c_peso = next((c for c in d_p.columns if any(k in str(c).lower() for k in ['peso', 'kg'])), d_p.columns[2])
            d_p['Fecha_dt'] = pd.to_datetime(d_p[c_fecha], dayfirst=True, errors='coerce')
            d_p['Peso'] = pd.to_numeric(d_p[c_peso], errors='coerce')
            df_base['Peso_Eval'] = cruzar_evaluacion(d_p, 'Peso', 'Peso_Eval')
        except: pass
    
    r_saltos = os.path.join("data", "EVALUACIONES", "SALTOS", "SALTOS.xlsx")
    if os.path.exists(r_saltos):
        try:
            d_s = pd.read_excel(r_saltos)
            c_fecha = next((c for c in d_s.columns if 'fecha' in str(c).lower()), 'Fecha')
            c_nombre = next((c for c in d_s.columns if 'nombre' in str(c).lower() or 'jugador' in str(c).lower()), 'Nombre')
            c_altura = next((c for c in d_s.columns if 'altura' in str(c).lower()), 'Altura')
            c_tipo = next((c for c in d_s.columns if 'tipo' in str(c).lower()), 'Tipo')
            d_s = d_s.rename(columns={c_nombre: 'Nombre', c_altura: 'Altura', c_tipo: 'Tipo'})
            d_s['Fecha_dt'] = pd.to_datetime(d_s[c_fecha].astype(str).str.split('_').str[0], errors='coerce')
            d_cmj = d_s[d_s['Tipo'].astype(str).str.upper() == 'CMJ']
            d_sl = d_s[d_s['Tipo'].astype(str).str.lower().str.contains('slcmj', na=False)].groupby(['Fecha_dt', 'Nombre'])['Altura'].mean().reset_index()
            df_base['CMJ_Eval'] = cruzar_evaluacion(d_cmj, 'Altura', 'CMJ_Eval')
            df_base['slCMJ_Eval'] = cruzar_evaluacion(d_sl, 'Altura', 'slCMJ_Eval')
        except: pass

    r_fuerza = os.path.join("data", "EVALUACIONES", "FUERZA", "ISOMETRICA.xlsx")
    if os.path.exists(r_fuerza):
        try:
            d_f = pd.read_excel(r_fuerza)
            c_fecha = next((c for c in d_f.columns if 'fecha' in str(c).lower()), 'Fecha')
            c_nombre = next((c for c in d_f.columns if 'nombre' in str(c).lower() or 'jugador' in str(c).lower()), 'Nombre')
            cols_rel = [c for c in d_f.columns if 'relativa' in str(c).lower() or 'fuerza' in str(c).lower()]
            if cols_rel:
                d_f['Fuerza_Iso_Gen'] = d_f[cols_rel].apply(pd.to_numeric, errors='coerce').mean(axis=1)
                d_f['Fecha_dt'] = pd.to_datetime(d_f[c_fecha].astype(str).str.split('_').str[0], errors='coerce')
                d_f = d_f.rename(columns={c_nombre: 'Nombre'})
                df_base['Fuerza_Iso_Gen'] = cruzar_evaluacion(d_f, 'Fuerza_Iso_Gen', 'Fuerza_Iso_Gen')
        except: pass

    return df_base

df_dosis = cargar_matriz_completa()
comprobar_descargas(cargar_matriz_completa)

# =============================================================================
# 3. INTERFAZ Y FILTROS
# =============================================================================
st.title("DOSIS - RESPUESTA")
st.caption("¿Responde cada jugador a la carga externa como se espera? Cada punto es una sesión: "
           "carga externa (GPS) frente a carga interna (sRPE). Se resaltan las sesiones con una respuesta "
           "anormalmente alta para la carga recibida, posible señal de fatiga.")

if df_dosis.empty:
    st.info("🚧 No hay suficientes datos coincidentes para construir la relación Dosis-Respuesta.")
    st.stop()

c_f1, c_f2 = st.columns([1, 2.5])
with c_f1:
    tipo_sel = st.selectbox("⚽ Tipo de sesión:", ["Todos"] + sorted(list(df_dosis['Tipo_Sesion'].unique())))
with c_f2:
    f_uni = sorted(df_dosis['Fecha_dt'].dropna().dt.date.unique())
    rango_s = st.slider("📅 Rango de Fechas:", min_value=f_uni[0], max_value=f_uni[-1], value=(f_uni[0], f_uni[-1]), format="DD/MM/YYYY")

df_f = df_dosis.copy()
if tipo_sel != "Todos": df_f = df_f[df_f['Tipo_Sesion'] == tipo_sel]
df_f = df_f[(df_f['Fecha_dt'].dt.date >= rango_s[0]) & (df_f['Fecha_dt'].dt.date <= rango_s[1])]

jugadores_opts = sorted(df_dosis['Nombre_Oficial'].dropna().unique(), key=nombre_bonito)
st.session_state.jugadores_seleccionados_dosis = [j for j in st.session_state.jugadores_seleccionados_dosis if j in jugadores_opts]
sel_jug = st.multiselect("🏃 Destacar jugadores:", jugadores_opts, default=st.session_state.jugadores_seleccionados_dosis,
                         format_func=nombre_bonito, key=f"ms_dosis_{st.session_state.dosis_key}")
st.session_state.jugadores_seleccionados_dosis = sel_jug

if df_f.empty:
    st.warning("No hay registros en el rango seleccionado.")
    st.stop()

# =============================================================================
# 4. GRÁFICO 1: DISPERSIÓN DOSIS-RESPUESTA
# =============================================================================
df_sc = df_f.dropna(subset=['Carga_UA', 'sRPE']).copy()
df_sc = df_sc[(df_sc['Carga_UA'] > 0) & (df_sc['sRPE'] > 0)]
if len(df_sc) >= 10:
    # Respuesta esperada = recta de regresión del equipo. Residuo estandarizado = cuánto se aleja cada sesión.
    pend, orig = np.polyfit(df_sc['Carga_UA'], df_sc['sRPE'], 1)
    df_sc['Esperado'] = pend * df_sc['Carga_UA'] + orig
    res = df_sc['sRPE'] - df_sc['Esperado']
    df_sc['Z_Res'] = (res - res.mean()) / (res.std() if res.std() > 0 else 1)
    r_val = df_sc[['Carga_UA', 'sRPE']].corr().iloc[0, 1]

    sel = set(st.session_state.jugadores_seleccionados_dosis)
    alta = df_sc['Z_Res'] > Z_RESIDUO
    def color_punto(row):
        if sel:
            return ACENTO if row['Nombre_Oficial'] in sel else "rgba(148,163,184,0.18)"
        return ROJO if row['Z_Res'] > Z_RESIDUO else "rgba(148,163,184,0.35)"
    colores = df_sc.apply(color_punto, axis=1)
    tam = [13 if (c not in ("rgba(148,163,184,0.18)", "rgba(148,163,184,0.35)")) else 9 for c in colores]

    fig = go.Figure()
    xs = np.linspace(df_sc['Carga_UA'].min(), df_sc['Carga_UA'].max(), 50)
    fig.add_trace(go.Scatter(x=xs, y=pend * xs + orig, mode="lines", line=dict(color=NEUTRO_TEXTO, dash="dash", width=1.5),
                             hoverinfo="skip", name="Respuesta esperada"))
    fig.add_trace(go.Scatter(
        x=df_sc['Carga_UA'], y=df_sc['sRPE'], mode="markers", name="Sesiones",
        marker=dict(color=colores, size=tam, line=dict(width=0.5, color="rgba(255,255,255,0.4)")),
        customdata=np.stack([df_sc['Nombre_Oficial'], df_sc['Fecha'], df_sc['Tipo_Sesion'], df_sc['Z_Res']], axis=-1),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>Carga externa: %{x:.0f} UA"
                      "<br>sRPE: %{y:.0f}<br>Desviación: %{customdata[3]:.2f}<extra></extra>"))
    estilo_fig(fig, height=420 if movil else 500, leyenda_abajo=False)
    fig.update_layout(showlegend=False,
                      xaxis_title="DOSIS · Carga externa (UA = dist + 2·>18 + 4·>25 + 1,5·acc/dec)",
                      yaxis_title="RESPUESTA · Carga interna (sRPE)")

    tarjetas_kpi([
        {"titulo": "Sesiones analizadas", "valor": str(len(df_sc))},
        {"titulo": "Relación dosis-respuesta (r)", "valor": f"{r_val:.2f}"},
        {"titulo": "Respuesta anormalmente alta", "valor": str(int(alta.sum())), "color": ROJO if alta.any() else TEXTO,
         "sub": f"desviación > {Z_RESIDUO} DE"},
    ])
    chart_key = f"dosis_scatter_{st.session_state.dosis_key}"
    event = mostrar_fig(fig, key=chart_key, on_select="rerun", selection_mode="points")
    if event and "selection" in event:
        pts = event["selection"].get("points", [])
        cambio = False
        for p in pts:
            cd = p.get("customdata")
            if cd:
                j = cd[0]
                if j in st.session_state.jugadores_seleccionados_dosis:
                    st.session_state.jugadores_seleccionados_dosis.remove(j)
                else:
                    st.session_state.jugadores_seleccionados_dosis.append(j)
                cambio = True
        if cambio:
            st.session_state.dosis_key += 1
            st.rerun()
    st.caption("Pulsa un punto (o usa el selector) para destacar a ese jugador. Sin selección se resaltan en rojo las sesiones con respuesta anormalmente alta.")

    ult = df_sc[alta].sort_values('Fecha_dt', ascending=False)
    if not ult.empty:
        recientes = ult[ult['Fecha_dt'] >= df_sc['Fecha_dt'].max() - pd.Timedelta(days=7)]
        bloque_alerta("🔺 Respuesta alta en los últimos 7 días",
                      recientes['Nombre_Oficial'].unique().tolist(), ROJO,
                      sufijos={n: pd.to_datetime(f).strftime('%d/%m') for n, f in zip(recientes['Nombre_Oficial'], recientes['Fecha'])})
else:
    st.info("Hacen falta al menos 10 sesiones con GPS y RPE para dibujar la relación.")

# =============================================================================
# 5. MATRICES DE CORRELACIÓN SEPARADAS
# =============================================================================
st.markdown("---")
st.markdown("### 📊 Matriz 1: variables diarias (control y carga)")
st.caption("Correlaciones entre -1 y 1. Rojo = suben juntas, azul = una sube cuando la otra baja. Cerca de 0 = sin relación. "
           "El resultado (3/1/0 puntos) solo existe los días de partido.")
dic_m1 = {
    'sRPE_prev': 'sRPE (D-1)', 'Wellness': 'Wellness (Día)', 'Dist_Total': 'Dist Total (m)',
    'Dist_18': 'Dist >18 km/h', 'Acc_Dec': 'Num. Acc+Dec', 'Estado_Animo': 'Estado ánimo', 'Resultado_Partido': 'Puntos partido'
}

cols_1 = [c for c in dic_m1.keys() if c in df_f.columns]
if len(cols_1) > 1:
    m_corr1 = df_f[cols_1].rename(columns=dic_m1).corr(numeric_only=True).dropna(how='all', axis=0).dropna(how='all', axis=1)
    if not m_corr1.empty:
        m_corr1 = m_corr1.where(np.tril(np.ones(m_corr1.shape, dtype=bool)))
        f_c1 = px.imshow(m_corr1, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", range_color=[-1, 1])
        f_c1.update_traces(opacity=0.85)
        f_c1.update_xaxes(showgrid=False)
        f_c1.update_yaxes(showgrid=False)
        f_c1.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=50))
        mostrar_fig(f_c1)
    else: st.info("Datos insuficientes para la Matriz 1.")
else: st.info("Datos insuficientes para la Matriz 1.")

st.markdown("---")
st.markdown("### 🏋️‍♂️ Matriz 2: Variables de Rendimiento Físico y Evaluaciones")
dic_m2 = {
    'V_MAX': 'Velocidad Máx', 'AC_MAX': 'Aceleración Máx', 'DEC_MAX': 'Desacel. Máx',
    'Peso_Eval': 'Peso (kg)', 'CMJ_Eval': 'CMJ Bilateral', 'slCMJ_Eval': 'slCMJ Unilateral', 'Fuerza_Iso_Gen': 'F. Isométrica Media'
}

cols_2 = [c for c in dic_m2.keys() if c in df_f.columns]
if len(cols_2) > 1:
    m_corr2 = df_f[cols_2].rename(columns=dic_m2).corr(numeric_only=True).dropna(how='all', axis=0).dropna(how='all', axis=1)
    if not m_corr2.empty:
        m_corr2 = m_corr2.where(np.tril(np.ones(m_corr2.shape, dtype=bool)))
        f_c2 = px.imshow(m_corr2, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", range_color=[-1, 1])
        f_c2.update_traces(opacity=0.85)
        f_c2.update_xaxes(showgrid=False)
        f_c2.update_yaxes(showgrid=False)
        f_c2.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=50))
        mostrar_fig(f_c2)
    else: st.info("Datos insuficientes para la Matriz 2.")
else: st.info("Datos insuficientes para la Matriz 2.")