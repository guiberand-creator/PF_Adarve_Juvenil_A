import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import (leer_sheet_csv, configurar_pagina, exigir_login_staff, controles_sidebar, render_html, tarjetas_kpi,
                   bloque_alerta, nombre_bonito, nombre_corto, fecha_es, etiqueta_sesion, estilo_fig, mostrar_fig,
                   ROJO, NARANJA, AZUL, VERDE, ACENTO, NEUTRO, NEUTRO_FUERTE, NEUTRO_TEXTO, TEXTO)

configurar_pagina("Carga Interna - Adarve DH")
exigir_login_staff()
movil = controles_sidebar()

# =============================================================================
# PARÁMETROS
# =============================================================================
INICIO_TEMPORADA = pd.Timestamp("2026-08-03")   # lunes de la "Sem 1" (antes: semana ISO 32)
ACWR_ALTO, ACWR_BAJO = 1.5, 0.8
DIAS_MIN_HISTORICO = 21       # sin 3 semanas de datos el ACWR no es fiable -> no se alerta
MONOTONIA_ALTA = 2.0
SUBIDA_SEMANAL = 0.15         # +15% de carga semanal respecto a la anterior -> semana resaltada
ANIMO_MUY_BAJO, ANIMO_BAJO, CAIDA_ANIMO = 4, 6, 1.5

def semana_temporada(fecha):
    """CORRECCIÓN: semana contada desde el inicio de temporada (no depende del año ISO ni de la semana 53)."""
    d = (pd.Timestamp(fecha).normalize() - INICIO_TEMPORADA).days // 7
    return d + 1 if d >= 0 else d   # pretemporada: -1, -2, ... (no existe la semana 0)

# =============================================================================
# DATOS
# =============================================================================
def obtener_datos_carga_real():
    url_csv = "https://docs.google.com/spreadsheets/d/1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s/export?format=csv&gid=1785642271"
    try:
        df = leer_sheet_csv(url_csv)
        df.columns = df.columns.str.strip()
        df['Fecha'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Fecha'])
        df['Dia'] = df['Fecha'].dt.normalize()
        df['Nombre'] = df['Nombre y apellidos'].fillna('Anónimo').astype(str).str.strip()
        df['Tipo de Sesión'] = df['Tipo de sesión'].fillna('Entreno').astype(str).str.strip()
        df['Duracion'] = pd.to_numeric(df['Minutos entreno/partido'], errors='coerce').fillna(0)
        col_cardio = [c for c in df.columns if 'CARDIO' in c.upper()]
        col_musc = [c for c in df.columns if 'MUSCULAR' in c.upper()]
        col_emo = [c for c in df.columns if 'EMOCIONAL' in c.upper() or 'ÁNIMO' in c.upper() or 'ANIMO' in c.upper()]
        df['RPE_Cardio'] = pd.to_numeric(df[col_cardio[0]], errors='coerce') if col_cardio else np.nan
        df['RPE_Muscular'] = pd.to_numeric(df[col_musc[0]], errors='coerce') if col_musc else np.nan
        df['Estado_Animo'] = pd.to_numeric(df[col_emo[0]], errors='coerce') if col_emo else np.nan
        df['RPE_General'] = df[['RPE_Cardio', 'RPE_Muscular']].mean(axis=1, skipna=True)
        df['Es_Partido'] = df['Tipo de Sesión'].str.lower().str.contains('partido')
        df['Es_Lesion'] = df['Tipo de Sesión'].str.lower().str.strip() == 'entreno a parte/lesión'
        return df, None
    except Exception as e:
        return None, str(e)


def serie_diaria(df_j, fecha_fin):
    """Carga diaria de un jugador con los días SIN sesión a 0 (necesario para ACWR y monotonía)."""
    s = df_j.groupby('Dia')['Carga_Individual'].sum()
    if s.empty: return s
    idx = pd.date_range(s.index.min(), fecha_fin, freq='D')
    return s.reindex(idx, fill_value=0.0)


def acwr_diario(s):
    """CORRECCIÓN: ACWR por DÍAS (antes por sesiones). Agudo = 7 días; crónico = media semanal de 28 días."""
    aguda = s.rolling(7, min_periods=7).sum()
    cronica = s.rolling(28, min_periods=DIAS_MIN_HISTORICO).sum() / 4
    return aguda / cronica.replace(0, np.nan)


df_raw, error_hoja = obtener_datos_carga_real()

st.title("CARGA INTERNA (RPE)")
st.caption("sRPE = RPE (media cardio + muscular) × minutos. Los entrenos aparte/lesión no cuentan en la carga del grupo.")

if error_hoja:
    st.error(f"Error de mapeo o conexión con Google Sheets: {error_hoja}")
    st.stop()
if df_raw is None or df_raw.empty:
    st.warning("Base de datos vacía o no estructurada. Revisa las respuestas del formulario.")
    st.stop()

fecha_fin = df_raw['Dia'].max()
df_f = df_raw[~df_raw['Es_Lesion']].copy()
df_f['Carga_Individual'] = df_f['RPE_General'] * df_f['Duracion']
# Para medias del equipo: los partidos solo cuentan si el jugador jugó >= 60' (mismo criterio en toda la app)
df_col = df_f[~(df_f['Es_Partido'] & (df_f['Duracion'] < 60))].copy()

# Jugadores cuyo último registro es "entreno aparte/lesión": no se les alerta de subcarga
ultimo_registro = df_raw.sort_values('Fecha').groupby('Nombre').tail(1).set_index('Nombre')
lesionados = set(ultimo_registro[ultimo_registro['Es_Lesion']].index)

# =============================================================================
# ALERTAS
# =============================================================================
al_sobre, al_sub, al_animo, acwr_actual = [], [], [], {}
for j, df_j in df_f.groupby('Nombre'):
    s = serie_diaria(df_j, fecha_fin)
    if s.empty: continue
    a = acwr_diario(s)
    ult = a.iloc[-1]
    acwr_actual[j] = ult
    if pd.notna(ult):
        if ult > ACWR_ALTO: al_sobre.append((j, f"{ult:.2f}"))
        elif ult < ACWR_BAJO and j not in lesionados: al_sub.append((j, f"{ult:.2f}"))

for j, df_j in df_raw.sort_values('Fecha').groupby('Nombre'):
    an = df_j.dropna(subset=['Estado_Animo'])
    if an.empty: continue
    if (fecha_fin - an['Dia'].iloc[-1]).days > 3:   # solo respuestas recientes
        continue
    ult = an['Estado_Animo'].iloc[-1]
    previos = an.iloc[:-1]
    previos = previos[previos['Dia'] >= an['Dia'].iloc[-1] - pd.Timedelta(days=15)]
    media_prev = previos['Estado_Animo'].mean() if not previos.empty else np.nan
    # CORRECCIÓN: un 8/10 ya no es "baja motivación". Hace falta valor bajo (<=6) Y caída, o un valor muy bajo (<=4).
    if ult <= ANIMO_MUY_BAJO or (ult <= ANIMO_BAJO and pd.notna(media_prev) and ult < media_prev - CAIDA_ANIMO):
        al_animo.append((j, f"{ult:.0f}" + (f" (media {media_prev:.1f})" if pd.notna(media_prev) else "")))

c1, c2, c3 = st.columns(3)
with c1: bloque_alerta(f"❌ ACWR > {ACWR_ALTO} (pico de carga)", [x[0] for x in al_sobre], ROJO, dict(al_sobre),
                       vacio="✅ Sin picos de carga")
with c2: bloque_alerta(f"🔵 ACWR < {ACWR_BAJO} (subcarga)", [x[0] for x in al_sub], AZUL, dict(al_sub),
                       vacio="✅ Nadie en subcarga (se excluyen lesionados)")
with c3: bloque_alerta("🧠 Estado anímico bajo", [x[0] for x in al_animo], NARANJA, dict(al_animo),
                       vacio="✅ Estado anímico estable")
st.caption(f"ACWR = carga de los últimos 7 días / media semanal de los últimos 28 (días sin sesión = 0). "
           f"No se calcula hasta tener {DIAS_MIN_HISTORICO} días de histórico. Úsalo como guía de planificación, no como predictor de lesión.")

# =============================================================================
# PANEL GRUPAL
# =============================================================================
st.markdown("---")
st.markdown("## 📊 Panel grupal")

# Carga media del equipo por día (días sin sesión = 0, necesario para la monotonía de Foster)
diario = df_col.groupby('Dia').agg(Carga=('Carga_Individual', 'mean'), RPE_M=('RPE_Muscular', 'mean'),
                                   RPE_C=('RPE_Cardio', 'mean'),
                                   Tipo=('Tipo de Sesión', lambda x: x.mode().iloc[0] if not x.mode().empty else ''))
idx = pd.date_range(diario.index.min(), fecha_fin, freq='D')
diario_full = diario.reindex(idx)
diario_full['Carga0'] = diario_full['Carga'].fillna(0)
diario_full['Sem'] = [semana_temporada(d) for d in diario_full.index]

semanal = diario_full.groupby('Sem').agg(Carga=('Carga0', 'sum'), Media=('Carga0', 'mean'), SD=('Carga0', 'std'),
                                         Inicio=('Carga0', lambda x: x.index.min()), Dias=('Carga0', 'size')).reset_index()
# CORRECCIÓN monotonía (Foster): media / desviación de las cargas de los 7 días, incluyendo descansos (0)
semanal['Monotonia'] = semanal['Media'] / semanal['SD'].replace(0, np.nan)
semanal.loc[semanal['Dias'] < 7, 'Monotonia'] = np.nan   # semana en curso: la monotonía no es comparable
semanal['Strain'] = semanal['Carga'] * semanal['Monotonia']
semanal['Cambio'] = semanal['Carga'].pct_change()
semanal.loc[semanal['Dias'] < 7, 'Cambio'] = np.nan      # no comparar una semana a medias con una completa
meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
semanal['Etiqueta'] = [f"S{int(s)} ({meses[pd.Timestamp(i).month]})" for s, i in zip(semanal['Sem'], semanal['Inicio'])]
semanal['Incompleta'] = semanal['Dias'] < 7

periodos = {"Últimas 4 semanas": 28, "Últimas 8 semanas": 56, "Temporada completa": None}
c_p, _ = st.columns([1, 2])
with c_p:
    periodo = st.selectbox("Periodo", list(periodos.keys()), index=0 if movil else 1)
dias_p = periodos[periodo]
d_vis = diario.copy()
if dias_p:
    d_vis = d_vis[d_vis.index > fecha_fin - pd.Timedelta(days=dias_p)]
    s_vis = semanal[semanal['Inicio'] > fecha_fin - pd.Timedelta(days=dias_p + 6)]
else:
    s_vis = semanal

g1, g2 = st.columns([1.1, 1])
with g1:
    st.markdown("#### Carga diaria del equipo")
    es_partido = d_vis['Tipo'].str.lower().str.contains('partido')
    fig_d = make_subplots(specs=[[{"secondary_y": True}]])
    fig_d.add_trace(go.Bar(x=d_vis.index, y=d_vis['Carga'], name="sRPE medio",
                           marker_color=[ACENTO if p else NEUTRO for p in es_partido],
                           customdata=[etiqueta_sesion(t) for t in d_vis['Tipo']],
                           hovertemplate="%{x|%d/%m}<br>%{customdata}<br>sRPE: %{y:.0f}<extra></extra>"), secondary_y=False)
    fig_d.add_trace(go.Scatter(x=d_vis.index, y=d_vis['RPE_M'], name="RPE muscular", mode="lines",
                               line=dict(color=NARANJA, width=1.8)), secondary_y=True)
    fig_d.add_trace(go.Scatter(x=d_vis.index, y=d_vis['RPE_C'], name="RPE cardio", mode="lines",
                               line=dict(color=AZUL, width=1.8)), secondary_y=True)
    estilo_fig(fig_d, height=360)
    fig_d.update_yaxes(title_text="sRPE (UA)", secondary_y=False)
    fig_d.update_yaxes(range=[0, 10.5], title_text="RPE", secondary_y=True, showgrid=False)
    fig_d.update_xaxes(tickformat="%d/%m")
    st.caption("En rojo los partidos; en gris los entrenamientos.")
    mostrar_fig(fig_d)

with g2:
    st.markdown("#### Carga semanal y monotonía")
    def color_sem(r):
        if (pd.notna(r['Monotonia']) and r['Monotonia'] > MONOTONIA_ALTA) or (pd.notna(r['Cambio']) and r['Cambio'] > SUBIDA_SEMANAL):
            return ROJO
        return NEUTRO
    fig_s = make_subplots(specs=[[{"secondary_y": True}]])
    fig_s.add_trace(go.Bar(x=s_vis['Etiqueta'], y=s_vis['Carga'], name="Carga semanal",
                           marker_color=[color_sem(r) for _, r in s_vis.iterrows()],
                           customdata=np.stack([s_vis['Cambio'].fillna(0) * 100, s_vis['Monotonia'].fillna(0)], axis=-1),
                           hovertemplate="%{x}<br>Carga: %{y:.0f} UA<br>Cambio: %{customdata[0]:+.0f}%<br>Monotonía: %{customdata[1]:.2f}<extra></extra>"),
                    secondary_y=False)
    fig_s.add_trace(go.Scatter(x=s_vis['Etiqueta'], y=s_vis['Monotonia'], name="Monotonía", mode="lines+markers",
                               line=dict(color=NEUTRO_FUERTE, width=2),
                               marker=dict(color=[ROJO if (pd.notna(m) and m > MONOTONIA_ALTA) else NEUTRO_FUERTE for m in s_vis['Monotonia']], size=8)),
                    secondary_y=True)
    fig_s.add_hline(y=MONOTONIA_ALTA, line_dash="dash", line_color=ROJO, secondary_y=True,
                    annotation_text=f"Monotonía {MONOTONIA_ALTA}", annotation_font=dict(size=10, color=ROJO))
    estilo_fig(fig_s, height=360)
    max_mono = max(3.0, float(np.nanmax(s_vis['Monotonia'])) * 1.15) if s_vis['Monotonia'].notna().any() else 3.0
    fig_s.update_yaxes(title_text="Carga semanal (UA)", secondary_y=False)
    fig_s.update_yaxes(title_text="Monotonía", range=[0, max_mono], secondary_y=True, showgrid=False)
    fig_s.update_xaxes(type='category')
    st.caption(f"En rojo las semanas con monotonía > {MONOTONIA_ALTA} o con una subida > {SUBIDA_SEMANAL:.0%} respecto a la anterior. "
               "La semana en curso no tiene monotonía hasta que se complete.")
    mostrar_fig(fig_s)

st.markdown("#### Training strain (carga × monotonía)")
fig_st = go.Figure(go.Scatter(x=s_vis['Etiqueta'], y=s_vis['Strain'], fill='tozeroy', mode="lines+markers",
                              line=dict(color=NEUTRO_FUERTE, width=2), fillcolor="rgba(148,163,184,0.12)",
                              marker=dict(size=7, color=[ROJO if v >= np.nanpercentile(semanal['Strain'], 90) else NEUTRO_FUERTE
                                                         for v in s_vis['Strain'].fillna(0)])))
estilo_fig(fig_st, height=200)
fig_st.update_xaxes(type='category')
st.caption("Puntos rojos: semanas en el 10% más alto de la temporada.")
mostrar_fig(fig_st)

# =============================================================================
# PLANTILLA: todos los jugadores de un vistazo (pulsa uno para ver su detalle)
# =============================================================================
SUBIDA_JUGADOR = 0.30      # +30% de carga respecto a su semana anterior -> aviso
BAJADA_JUGADOR = -0.40     # -40% -> aviso de bajada brusca

st.markdown("---")
st.markdown("## 👥 Plantilla")
st.caption("Elige un jugador (o pulsa su línea en el gráfico) y todos los gráficos se filtran para él.")

filas = []
for j, d_j in df_f.groupby('Nombre'):
    s = serie_diaria(d_j, fecha_fin)
    if s.empty:
        continue
    a = acwr_diario(s)
    ac = a.iloc[-1]
    c7 = s.iloc[-7:].sum()
    c7p = s.iloc[-14:-7].sum() if len(s) >= 14 else np.nan
    cambio = (c7 / c7p - 1) if pd.notna(c7p) and c7p > 0 else np.nan
    ult7 = d_j[d_j['Dia'] > fecha_fin - pd.Timedelta(days=7)]
    s28 = s.reindex(pd.date_range(fecha_fin - pd.Timedelta(days=27), fecha_fin, freq='D'), fill_value=0.0)

    avisos, prioridad = [], 9
    if j in lesionados:
        avisos.append("🚑 Lesión/aparte"); prioridad = min(prioridad, 3)
    if pd.notna(ac) and ac > ACWR_ALTO:
        avisos.append("🔴 ACWR alto"); prioridad = min(prioridad, 0)
    elif pd.notna(ac) and ac > 1.3:
        avisos.append("🟠 ACWR 1.3-1.5"); prioridad = min(prioridad, 1)
    elif pd.notna(ac) and ac < ACWR_BAJO and j not in lesionados:
        avisos.append("🔵 ACWR bajo"); prioridad = min(prioridad, 2)
    if pd.notna(cambio) and cambio > SUBIDA_JUGADOR:
        avisos.append(f"🟠 +{cambio:.0%} semana"); prioridad = min(prioridad, 1)
    elif pd.notna(cambio) and cambio < BAJADA_JUGADOR and j not in lesionados:
        avisos.append(f"🔵 {cambio:.0%} semana"); prioridad = min(prioridad, 2)
    if len(ult7) == 0 and j not in lesionados:
        avisos.append("⚪ Sin sesiones 7 días"); prioridad = min(prioridad, 2)

    filas.append({"Nombre": j, "Jugador": nombre_bonito(j), "Avisos": " · ".join(avisos) if avisos else "—",
                  "ACWR": ac, "Carga 7 días": c7, "Cambio semanal": cambio * 100 if pd.notna(cambio) else np.nan,
                  "RPE medio 7 días": ult7['RPE_General'].mean() if not ult7.empty else np.nan,
                  "Sesiones 7 días": int(len(ult7)), "Carga 28 días": [float(v) for v in s28.values],
                  "_prio": prioridad, "_lesion": j in lesionados})
plantilla = pd.DataFrame(filas)
for _c in ['ACWR', 'Carga 7 días', 'Cambio semanal', 'RPE medio 7 días']:
    if _c in plantilla.columns: plantilla[_c] = pd.to_numeric(plantilla[_c], errors='coerce')

if "sel_ci_n" not in st.session_state:
    st.session_state["sel_ci_n"] = 0

def seleccionar_jugador(nombre):
    """Lleva al jugador pulsado al análisis individual y limpia la selección del gráfico/tabla."""
    st.session_state["jug_ci_pendiente"] = nombre    # se aplica al selector en la siguiente ejecución
    st.session_state["sel_ci_n"] += 1
    st.rerun()

# ---------- Fotos de los jugadores (columna de foto de data/Posiciones.xlsx) ----------
def cargar_fotos():
    ruta = os.path.join("data", "Posiciones.xlsx")
    if not os.path.exists(ruta): return {}
    try:
        dp = pd.read_excel(ruta)
        dp.columns = [str(c).strip() for c in dp.columns]
        c_n = next((c for c in dp.columns if 'jugador' in c.lower() or 'nombre' in c.lower()), dp.columns[0])
        c_f = next((c for c in dp.columns if any(k in c.lower() for k in ['foto', 'url'])), None)
        if not c_f: return {}
        return {nombre_bonito(n).lower(): str(u).strip() for n, u in zip(dp[c_n], dp[c_f])
                if pd.notna(u) and str(u).strip().lower().startswith("http")}
    except Exception:
        return {}
fotos = cargar_fotos()

if not plantilla.empty:
    plantilla = plantilla.sort_values(['_prio', 'ACWR'], ascending=[True, False]).reset_index(drop=True)
TODOS = "__todos__"
jugadores = sorted(df_raw['Nombre'].unique(), key=nombre_bonito)
opciones = [TODOS] + jugadores
if st.session_state.get("jug_ci_pendiente") in opciones:
    st.session_state["jug_ci"] = st.session_state.pop("jug_ci_pendiente")
if st.session_state.get("jug_ci") not in opciones:
    st.session_state["jug_ci"] = TODOS

dia_min, dia_max = df_f['Dia'].min().date(), fecha_fin.date()
c_sel, c_fec, c_bot = st.columns([2, 2, 1], vertical_alignment="bottom")
with c_sel:
    jug = st.selectbox("Jugador", opciones, key="jug_ci",
                       format_func=lambda x: "👥 Toda la plantilla" if x == TODOS else nombre_bonito(x))
with c_fec:
    rango = st.date_input("Rango de fechas", value=(max(dia_min, (fecha_fin - pd.Timedelta(days=56)).date()), dia_max),
                          min_value=dia_min, max_value=dia_max, format="DD/MM/YYYY", key="rango_ci")
with c_bot:
    if jug != TODOS and st.button("👥 Ver toda la plantilla", width="stretch"):
        seleccionar_jugador(TODOS)
# Mientras se elige el rango, el calendario devuelve solo la fecha de inicio
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    desde, hasta = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
else:
    desde = pd.Timestamp(rango[0] if isinstance(rango, (list, tuple)) else rango); hasta = fecha_fin

# ---------- ACWR: toda la plantilla o solo el jugador elegido ----------
def color_jugador(r):
    if r['_lesion'] or pd.isna(r['ACWR']): return None
    if r['ACWR'] > ACWR_ALTO: return ROJO
    if r['ACWR'] > 1.3: return NARANJA
    if r['ACWR'] < ACWR_BAJO: return AZUL
    return None

fig_all = go.Figure()
fig_all.add_hrect(y0=ACWR_BAJO, y1=1.3, fillcolor="rgba(148,163,184,0.07)", line_width=0)
fig_all.add_hline(y=ACWR_ALTO, line=dict(color=ROJO, dash="dash", width=1))
fig_all.add_hline(y=ACWR_BAJO, line=dict(color=AZUL, dash="dash", width=1))
y_max_all = 2.0
info = {r['Nombre']: r for _, r in plantilla.iterrows()} if not plantilla.empty else {}
if jug == TODOS:
    # primero los normales (gris, debajo) y encima los que se salen
    a_dibujar = sorted(info.keys(), key=lambda n: color_jugador(info[n]) is not None)
else:
    a_dibujar = [jug]
for n in a_dibujar:
    s_n = serie_diaria(df_f[df_f['Nombre'] == n], fecha_fin)
    a_n = acwr_diario(s_n)
    a_n = a_n[(a_n.index >= desde) & (a_n.index <= hasta)]
    if a_n.notna().sum() == 0:
        continue
    if jug != TODOS:
        color_l, ancho = ACENTO, 3
        marcas = [ROJO if v > ACWR_ALTO else NARANJA if v > 1.3 else AZUL if v < ACWR_BAJO else ACENTO for v in a_n.fillna(1).values]
        tam = 7
    else:
        col = color_jugador(info[n]) if n in info else None
        color_l, ancho = (col, 1.8) if col else ("rgba(148,163,184,0.30)", 1.1)
        marcas, tam = color_l, 4
    y_max_all = max(y_max_all, float(a_n.max()) + 0.15)
    fig_all.add_trace(go.Scatter(
        x=a_n.index, y=a_n.values, mode="lines+markers", connectgaps=False,
        line=dict(color=color_l, width=ancho), marker=dict(size=tam, color=marcas),
        customdata=[n] * len(a_n), name=nombre_bonito(n),
        hovertemplate=f"<b>{nombre_bonito(n)}</b><br>" + "%{x|%d/%m}: ACWR %{y:.2f}<extra></extra>"))
titulo_acwr = "ACWR (7:28 días) · toda la plantilla" if jug == TODOS else f"ACWR (7:28 días) · {nombre_bonito(jug)}"
estilo_fig(fig_all, height=420 if movil else 500, leyenda_abajo=False, titulo=titulo_acwr)
fig_all.update_layout(showlegend=False, hovermode="closest", margin=dict(l=10, r=10, t=45, b=10),
                      hoverlabel=dict(font_size=14))
fig_all.update_yaxes(range=[0, y_max_all])
fig_all.update_xaxes(tickformat="%d/%m", range=[desde - pd.Timedelta(days=1), hasta + pd.Timedelta(days=1)])
ev = mostrar_fig(fig_all, key=f"acwr_all_{st.session_state['sel_ci_n']}", on_select="rerun", selection_mode="points")
if ev and ev.get("selection", {}).get("points"):
    cd = ev["selection"]["points"][0].get("customdata")
    if cd:
        nombre_click = cd[0] if isinstance(cd, list) else cd
        if nombre_click != jug:
            seleccionar_jugador(nombre_click)
if jug == TODOS:
    st.caption("En gris, los jugadores en rango; en color, los que hoy se salen (rojo > 1.5 · naranja 1.3-1.5 · azul < 0.8). "
               "Pasa el cursor por una línea para ver de quién es y **púlsala para quedarte solo con ese jugador**.")

sin_datos = [r['Jugador'] for _, r in plantilla.iterrows() if r['_lesion'] or pd.isna(r['ACWR'])] if not plantilla.empty else []
if sin_datos and jug == TODOS:
    st.caption("Sin línea de color (lesión/aparte o sin histórico suficiente): " + ", ".join(sin_datos))

if not plantilla.empty:
    with st.expander("📋 Tabla de la plantilla (avisos y carga de los últimos 28 días)"):
        n_sel = st.session_state["sel_ci_n"]
        tabla = plantilla[['Jugador', 'Avisos', 'ACWR', 'Carga 7 días', 'Cambio semanal', 'RPE medio 7 días', 'Sesiones 7 días', 'Carga 28 días']]
        if movil:
            tabla = tabla[['Jugador', 'Avisos', 'ACWR', 'Carga 28 días']]
        ev_t = st.dataframe(
            tabla, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key=f"tabla_ci_{n_sel}",
            height=min(36 * (len(tabla) + 1) + 4, 720),
            column_config={
                "Jugador": st.column_config.TextColumn("Jugador", pinned=True),
                "Avisos": st.column_config.TextColumn("Avisos", width="medium"),
                "ACWR": st.column_config.NumberColumn("ACWR", format="%.2f"),
                "Carga 7 días": st.column_config.NumberColumn("Carga 7 d (UA)", format="%.0f"),
                "Cambio semanal": st.column_config.NumberColumn("vs semana ant.", format="%+.0f%%"),
                "RPE medio 7 días": st.column_config.NumberColumn("RPE 7 d", format="%.1f"),
                "Sesiones 7 días": st.column_config.NumberColumn("Sesiones 7 d", format="%d"),
                "Carga 28 días": st.column_config.LineChartColumn("Carga últimos 28 días", y_min=0, width="medium"),
            })
        filas_sel = ev_t.selection.rows if ev_t and hasattr(ev_t, "selection") else []
        if filas_sel:
            seleccionar_jugador(plantilla.iloc[filas_sel[0]]['Nombre'])
        st.caption("Ordenada por prioridad: primero los avisos rojos, luego naranjas y azules. "
                   f"Avisos: ACWR > {ACWR_ALTO} o entre 1.3 y {ACWR_ALTO}, ACWR < {ACWR_BAJO}, "
                   f"cambio semanal > +{SUBIDA_JUGADOR:.0%} o < {BAJADA_JUGADOR:.0%}, o ninguna sesión en 7 días.")


# =============================================================================
# DETALLE DEL JUGADOR SELECCIONADO
# =============================================================================
if jug == TODOS:
    st.info("👆 Elige un jugador en el desplegable o pulsa su línea en el gráfico para ver su detalle.")
    st.stop()
url_foto = fotos.get(nombre_bonito(jug).lower())
foto_html = f"<img src='{url_foto}' style='height:80px; width:auto; object-fit:contain'>" if url_foto else "<span style='font-size:2rem'>👤</span>"
render_html(f"<div style='display:flex; align-items:center; gap:14px; margin:14px 0 6px 0'>{foto_html}"
            f"<span style='font-size:1.6rem; font-weight:800; color:{TEXTO}; font-family:Barlow Condensed, sans-serif'>"
            f"{nombre_bonito(jug)}</span></div>")
df_j = df_f[df_f['Nombre'] == jug].sort_values('Fecha')
if df_j.empty:
    st.info("No se registran entrenamientos válidos para este jugador.")
    st.stop()

s_j = serie_diaria(df_j, fecha_fin)
a_j = acwr_diario(s_j)
carga_7 = s_j.iloc[-7:].sum()
carga_7_prev = s_j.iloc[-14:-7].sum() if len(s_j) >= 14 else np.nan
ult_acwr = a_j.iloc[-1]
rpe_7 = df_j[df_j['Dia'] > fecha_fin - pd.Timedelta(days=7)]['RPE_General'].mean()
color_acwr = ROJO if pd.notna(ult_acwr) and ult_acwr > ACWR_ALTO else (AZUL if pd.notna(ult_acwr) and ult_acwr < ACWR_BAJO else TEXTO)
tarjetas_kpi([
    {"titulo": "ACWR actual", "valor": f"{ult_acwr:.2f}" if pd.notna(ult_acwr) else "-", "color": color_acwr,
     "sub": "sin histórico suficiente" if pd.isna(ult_acwr) else ""},
    {"titulo": "Carga últimos 7 días", "valor": f"{carga_7:.0f} UA",
     "sub": f"{(carga_7 / carga_7_prev - 1) * 100:+.0f}% vs semana previa" if pd.notna(carga_7_prev) and carga_7_prev > 0 else ""},
    {"titulo": "RPE medio 7 días", "valor": f"{rpe_7:.1f}" if pd.notna(rpe_7) else "-"},
    {"titulo": "Estado", "valor": "Lesión / aparte" if jug in lesionados else "Disponible",
     "color": ROJO if jug in lesionados else TEXTO},
])

i1, i2 = st.columns(2)
with i1:
    s_vis = s_j[(s_j.index >= desde) & (s_j.index <= hasta)]
    tipos = df_j.groupby('Dia')['Tipo de Sesión'].first()
    es_p = [('partido' in str(tipos.get(d, '')).lower()) for d in s_vis.index]
    fig_c = go.Figure(go.Bar(x=s_vis.index, y=s_vis.values, marker_color=[ACENTO if p else NEUTRO for p in es_p],
                             customdata=[etiqueta_sesion(tipos.get(d, 'Descanso')) for d in s_vis.index],
                             hovertemplate="%{x|%d/%m} · %{customdata}<br>%{y:.0f} UA<extra></extra>"))
    estilo_fig(fig_c, height=320, titulo="Carga diaria (sRPE) · partidos en rojo")
    fig_c.update_layout(showlegend=False)
    fig_c.update_xaxes(tickformat="%d/%m")
    mostrar_fig(fig_c)
with i2:
    df_jv = df_j[(df_j['Dia'] >= desde) & (df_j['Dia'] <= hasta)]
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(x=df_jv['Fecha'], y=df_jv['RPE_Muscular'], name="Muscular", marker_color=NARANJA))
    fig_p.add_trace(go.Bar(x=df_jv['Fecha'], y=df_jv['RPE_Cardio'], name="Cardio", marker_color=AZUL,
                           customdata=[etiqueta_sesion(t) for t in df_jv['Tipo de Sesión']],
                           hovertemplate="%{x|%d/%m} · %{customdata}<br>Cardio: %{y}<extra></extra>"))
    estilo_fig(fig_p, height=320, titulo="Tipología de la fatiga (RPE muscular vs cardio)")
    fig_p.update_layout(barmode='stack', yaxis_range=[0, 20.5])
    fig_p.update_xaxes(tickformat="%d/%m")
    mostrar_fig(fig_p)
