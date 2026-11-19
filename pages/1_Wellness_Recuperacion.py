import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import (leer_sheet_csv, configurar_pagina, exigir_login_staff, controles_sidebar, render_html, tarjetas_kpi,
                   bloque_alerta, chips_html, nombre_bonito, nombre_corto, fecha_es, estilo_fig, mostrar_fig,
                   barras_jugadores, mostrar_segun_pantalla, ROJO, NARANJA, AZUL, VERDE, NEUTRO, NEUTRO_TEXTO, TEXTO)

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
configurar_pagina("Wellness y Recuperación - Adarve DH")
exigir_login_staff()
movil = controles_sidebar()

# Umbrales (escala wellness 1-5, 5 = mejor)
WELL_ALERTA = 3.0        # media del día < 3.0
ITEM_CRITICO = 1         # algún ítem en el valor mínimo (1) -> aviso aunque la media sea buena
Z_ALERTA = -1.5          # caída respecto a su propia línea base
VENTANA_WELL = 15        # nº de registros previos que forman la línea base de wellness
VENTANA_DRI = 4          # nº de tests previos que forman la línea base del DRI
ALTURA_CAJON_M = 0.50

def normalizar_texto(text):
    if pd.isna(text): return ""
    return (str(text).replace('_', ' ').strip().lower()
            .replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            .replace('ü', 'u').replace('ñ', 'n'))

# ==========================================
# 2. DATOS WELLNESS
# ==========================================
def cargar_datos_wellness():
    url_csv = "https://docs.google.com/spreadsheets/d/12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o/export?format=csv&gid=1891505901"
    try:
        df = leer_sheet_csv(url_csv)
        df.columns = (df.columns.str.strip().str.upper()
                      .str.replace('É', 'E').str.replace('Ú', 'U').str.replace('Á', 'A')
                      .str.replace('Í', 'I').str.replace('Ó', 'O'))
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
        col_zona = next((c for c in df.columns if 'MUSCULATURA' in c or 'CARGADA' in c), None)
        col_det = next((c for c in df.columns if 'ESPECIFICA' in c or 'SIENTES' in c or 'DIFERENTE' in c), None)

        # CORRECCIÓN: sin fillna(0). Un ítem vacío queda vacío y no hunde la media.
        df['SUEÑO'] = pd.to_numeric(df[col_sueno], errors='coerce')
        df['DOLOR'] = pd.to_numeric(df[col_dolor], errors='coerce')
        df['ESTRÉS'] = pd.to_numeric(df[col_estres], errors='coerce')
        df['CARGA'] = pd.to_numeric(df[col_carga], errors='coerce')
        df['DISPONIBLE'] = df[col_entrenar].astype(str).str.strip().str.lower()
        df['ZONA_DOLOR'] = df[col_zona].fillna('Ninguna').astype(str).str.strip() if col_zona else 'Ninguna'
        df['DETALLE_DOLOR'] = df[col_det].fillna('-').astype(str).str.strip() if col_det else '-'
        df['ZONA_DOLOR'] = df['ZONA_DOLOR'].apply(lambda x: 'Ninguna' if x.lower() in ['', 'nan', 'none', '-'] else x)
        df['DETALLE_DOLOR'] = df['DETALLE_DOLOR'].apply(lambda x: '-' if x.lower() in ['', 'nan', 'none', '-'] else x)
        items = df[['SUEÑO', 'DOLOR', 'ESTRÉS', 'CARGA']]
        df['WELLNESS_TOTAL'] = items.mean(axis=1, skipna=True)
        df['ITEM_MIN'] = items.min(axis=1, skipna=True)
        return df, None
    except Exception as e:
        return None, str(e)

# ==========================================
# 3. DATOS DROP JUMP (DRI)
# ==========================================
def cargar_datos_saltos():
    url_csv = "https://docs.google.com/spreadsheets/d/1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y/export?format=csv&gid=0"
    try:
        d = leer_sheet_csv(url_csv)
        d.columns = d.columns.str.strip()
        d['JUGADOR_NORM'] = d['Nombre de atleta'].fillna('Anónimo').astype(str).str.strip().apply(normalizar_texto)
        d['FECHA_REAL'] = pd.to_datetime(d['Fecha y hora'].astype(str).str.split('_').str[0], format='%Y-%m-%d', errors='coerce')
        d = d.dropna(subset=['FECHA_REAL'])
        d['FECHA_DIA'] = d['FECHA_REAL'].dt.date
        d['TC_SEG'] = pd.to_numeric(d['TC'].astype(str).str.replace(',', '.'), errors='coerce')
        d['ALTURA_CM'] = pd.to_numeric(d['Altura'].astype(str).str.replace(',', '.'), errors='coerce')
        # CORRECCIÓN: los intentos sin tiempo de contacto válido se descartan (antes contaban como DRI = 0)
        d = d[(d['TC_SEG'] > 0) & d['ALTURA_CM'].notna()].copy()
        d['DRI_INTENTO'] = (ALTURA_CAJON_M + d['ALTURA_CM'] / 100.0) / (9.81 * d['TC_SEG'] ** 2)
        g = d.groupby(['JUGADOR_NORM', 'FECHA_DIA']).agg(
            DRI_MEDIO=('DRI_INTENTO', 'mean'), ALTURA_MEDIA_CM=('ALTURA_CM', 'mean'),
            TC_MEDIO_S=('TC_SEG', 'mean'), INTENTOS=('DRI_INTENTO', 'count')).reset_index()
        return g, None
    except Exception as e:
        return None, str(e)


def zscore_vs_linea_base(serie_grupo, ventana, min_previos):
    """z = (hoy - media de los N registros ANTERIORES) / desviación de esos registros.
    CORRECCIÓN: antes la línea base incluía el propio día, lo que amortiguaba las caídas."""
    base = serie_grupo.shift(1)
    media = base.rolling(ventana, min_periods=min_previos).mean()
    sd = base.rolling(ventana, min_periods=min_previos).std()
    z = (serie_grupo - media) / sd.replace(0, np.nan)
    return z, media

# ==========================================
# 4. CABECERA
# ==========================================
st.title("WELLNESS Y RECUPERACIÓN")
st.caption(f"Ítems de 1 a 5 (5 = mejor). Cada jugador se compara con su propia línea base: últimos {VENTANA_WELL} cuestionarios (wellness) "
           f"y últimos {VENTANA_DRI} tests de Drop Jump (DRI).")

df_well, error_w = cargar_datos_wellness()
df_saltos, error_s = cargar_datos_saltos()
if error_w:
    st.error(f"Error al conectar con la base de datos de Wellness: {error_w}")
    st.stop()
if error_s:
    st.warning(f"No se pudieron leer los saltos (Chronojump): {error_s}. Se muestra solo el wellness.")
    df_saltos = pd.DataFrame(columns=['JUGADOR_NORM', 'FECHA_DIA', 'DRI_MEDIO', 'ALTURA_MEDIA_CM', 'TC_MEDIO_S', 'INTENTOS'])

fechas_disponibles = sorted(df_well['FECHA_DIA'].unique(), reverse=True)
c_top, _ = st.columns([1, 2])
with c_top:
    fecha_sel = st.selectbox("📅 Fecha de análisis", fechas_disponibles, format_func=fecha_es)

# ==========================================
# 5. Z-SCORES INDIVIDUALES
# ==========================================
dw = df_well.sort_values(['JUGADOR_NORM', 'FECHA_REAL']).copy()
z_list, m_list = [], []
for _, g in dw.groupby('JUGADOR_NORM', sort=False):
    z, m = zscore_vs_linea_base(g['WELLNESS_TOTAL'], VENTANA_WELL, 3)
    z_list.append(z); m_list.append(m)
dw['Z_WELL'] = pd.concat(z_list) if z_list else np.nan
dw['WELL_BASE'] = pd.concat(m_list) if m_list else np.nan

ds = df_saltos.sort_values(['JUGADOR_NORM', 'FECHA_DIA']).copy()
if not ds.empty:
    zs = [zscore_vs_linea_base(g['DRI_MEDIO'], VENTANA_DRI, 2)[0] for _, g in ds.groupby('JUGADOR_NORM', sort=False)]
    ds['Z_SALTO'] = pd.concat(zs)
else:
    ds['Z_SALTO'] = np.nan

hoy_w = dw[dw['FECHA_DIA'] == fecha_sel].drop_duplicates('JUGADOR_NORM', keep='last')
hoy_s = ds[ds['FECHA_DIA'] == fecha_sel]
df = pd.merge(hoy_w, hoy_s[['JUGADOR_NORM', 'DRI_MEDIO', 'ALTURA_MEDIA_CM', 'TC_MEDIO_S', 'INTENTOS', 'Z_SALTO']],
              on='JUGADOR_NORM', how='left')
tiene_saltos = df['Z_SALTO'].notna().any()

if df.empty:
    st.info("No hay registros de Wellness para este día.")
    st.stop()

def tiene_molestia(z):
    z = str(z).lower()
    return not ('nada' in z or z in ['ninguna', '', 'nan', 'none', '-'])

def estado(row):
    """Lógica ÚNICA de estado (antes el gráfico y la tabla usaban criterios distintos)."""
    if str(row['DISPONIBLE']).startswith('no'):
        return "🚑 Enfermería"
    fatiga_subj = (row['WELLNESS_TOTAL'] < WELL_ALERTA) or (pd.notna(row['Z_WELL']) and row['Z_WELL'] < Z_ALERTA) \
        or (pd.notna(row['ITEM_MIN']) and row['ITEM_MIN'] <= ITEM_CRITICO)
    fatiga_snc = pd.notna(row.get('Z_SALTO')) and row['Z_SALTO'] < Z_ALERTA
    if fatiga_subj and fatiga_snc: return "❌ Alerta integral"
    if fatiga_snc: return "⚡ Alerta neuromuscular"
    if fatiga_subj: return "⚠️ Fatiga subjetiva"
    if tiene_molestia(row['ZONA_DOLOR']): return "🩹 Molestia"
    return "🟢 Sin problemas"

df['ESTADO'] = df.apply(estado, axis=1)
COLOR_ESTADO = {"❌ Alerta integral": ROJO, "⚡ Alerta neuromuscular": ROJO, "⚠️ Fatiga subjetiva": NARANJA,
                "🩹 Molestia": AZUL, "🟢 Sin problemas": NEUTRO, "🚑 Enfermería": NEUTRO}
df['COLOR'] = df['ESTADO'].map(COLOR_ESTADO)

# ==========================================
# 6. RESUMEN DE ALERTAS
# ==========================================
disp = df[~df['DISPONIBLE'].str.startswith('no', na=False)]
tarjetas_kpi([
    {"titulo": "Respuestas", "valor": str(len(df)), "sub": f"{len(disp)} disponibles"},
    {"titulo": "Wellness medio", "valor": f"{disp['WELLNESS_TOTAL'].mean():.1f}" if not disp.empty else "-"},
    {"titulo": "Alertas", "valor": str(int(df['ESTADO'].isin(["❌ Alerta integral", "⚡ Alerta neuromuscular"]).sum())),
     "color": ROJO if df['ESTADO'].isin(["❌ Alerta integral", "⚡ Alerta neuromuscular"]).any() else TEXTO},
    {"titulo": "Fatiga subjetiva", "valor": str(int((df['ESTADO'] == "⚠️ Fatiga subjetiva").sum())),
     "color": NARANJA if (df['ESTADO'] == "⚠️ Fatiga subjetiva").any() else TEXTO},
])
ca, cb = st.columns(2)
with ca:
    bloque_alerta("❌ Alertas (integral / neuromuscular)",
                  df[df['ESTADO'].isin(["❌ Alerta integral", "⚡ Alerta neuromuscular"])]['JUGADOR'].tolist(), ROJO)
with cb:
    sub = df[df['ESTADO'] == "⚠️ Fatiga subjetiva"]
    bloque_alerta("⚠️ Fatiga subjetiva", sub['JUGADOR'].tolist(), NARANJA,
                  sufijos={r['JUGADOR']: f"W {r['WELLNESS_TOTAL']:.1f}" for _, r in sub.iterrows()})

# ==========================================
# 7. GRÁFICOS (solo se colorea lo que requiere atención)
# ==========================================
st.markdown("---")
st.markdown("#### Desviación respecto a su línea base")
graf = df[~df['DISPONIBLE'].str.startswith('no', na=False)].copy()
graf['Z_PLOT'] = graf['Z_WELL'].fillna(0)
# La media del día va junto al nombre (así no se pisa con las barras en el móvil)
graf['ETIQ'] = [f"{nombre_corto(j)} · {w:.1f}" for j, w in zip(graf['JUGADOR'], graf['WELLNESS_TOTAL'])]
hover = [f"<b>{nombre_bonito(j)}</b><br>Wellness: {w:.1f}<br>Z wellness: {z if pd.isna(z) else round(z, 2)}<br>"
         f"Sueño {s} · Dolor {d} · Estrés {e} · Carga {c}<br>Molestia: {zn}<br>{est}"
         for j, w, z, s, d, e, c, zn, est in zip(graf['JUGADOR'], graf['WELLNESS_TOTAL'], graf['Z_WELL'], graf['SUEÑO'],
                                                 graf['DOLOR'], graf['ESTRÉS'], graf['CARGA'], graf['ZONA_DOLOR'], graf['ESTADO'])]
args_w = dict(hover=hover, acortar=False, eje_titulo="Z-score wellness (0 = su normalidad)",
              lineas=[{"x": Z_ALERTA, "color": ROJO, "texto": f"{Z_ALERTA}"}, {"x": 0, "color": NEUTRO_TEXTO, "dash": "dot"}],
              rango=[min(-3.2, graf['Z_PLOT'].min() - 0.5), max(2.5, graf['Z_PLOT'].max() + 1.2)])
fig_w = barras_jugadores(graf['ETIQ'], graf['Z_PLOT'], graf['COLOR'], **args_w)                    # móvil
fig_w_pc = barras_jugadores(graf['ETIQ'], graf['Z_PLOT'], graf['COLOR'], vertical=True, **args_w)  # ordenador
if tiene_saltos:
    # Rombos del salto (DRI) sobre el mismo eje: en color solo si caen por debajo del umbral
    m = graf[graf['Z_SALTO'].notna()]
    fig_w.add_trace(go.Scatter(
        x=m['Z_SALTO'], y=m['ETIQ'], mode="markers", name="Z DRI (salto)",
        marker=dict(symbol="diamond", size=11, color=[ROJO if z < Z_ALERTA else "rgba(148,163,184,0.8)" for z in m['Z_SALTO']],
                    line=dict(width=1, color="white")),
        hovertemplate="%{y}<br>Z DRI: %{x:.2f}<extra></extra>"))
    fig_w_pc.add_trace(go.Scatter(
        x=m['ETIQ'], y=m['Z_SALTO'], mode="markers", name="Z DRI (salto)",
        marker=dict(symbol="diamond", size=11, color=[ROJO if z < Z_ALERTA else "rgba(148,163,184,0.8)" for z in m['Z_SALTO']],
                    line=dict(width=1, color="white")),
        hovertemplate="%{x}<br>Z DRI: %{y:.2f}<extra></extra>"))
    for f_ in (fig_w, fig_w_pc):
        f_.update_layout(showlegend=True, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    st.caption("Barras = z-score del wellness · ◆ = z-score del salto (DRI). Junto al nombre, la media de wellness del día. "
               "En color solo los jugadores con aviso o alerta.")
mostrar_segun_pantalla(fig_w_pc, fig_w, key="wellness_z", movil=movil)

if tiene_saltos:
    st.markdown("#### Matriz de readiness")
    m = graf[graf['Z_SALTO'].notna()]
    destacado = m['COLOR'] != NEUTRO
    fig_sc = go.Figure()
    fig_sc.add_trace(go.Scatter(
        x=m['Z_WELL'].fillna(0), y=m['Z_SALTO'], mode='markers+text',
        text=[nombre_corto(j) if dst else "" for j, dst in zip(m['JUGADOR'], destacado)], textposition='top center',
        textfont=dict(color=TEXTO, size=11),
        hovertext=[f"<b>{nombre_bonito(j)}</b><br>Z wellness: {zw:.2f}<br>Z DRI: {zs:.2f}<br>Molestia: {zn}"
                   for j, zw, zs, zn in zip(m['JUGADOR'], m['Z_WELL'].fillna(0), m['Z_SALTO'], m['ZONA_DOLOR'])],
        hoverinfo='text',
        marker=dict(size=13, color=m['COLOR'].replace({NEUTRO: "rgba(148,163,184,0.45)"}), line=dict(width=1, color='white'))))
    fig_sc.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig_sc.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    for x, y, t, c in [(1.9, 2.6, "RECUPERADO", NEUTRO_TEXTO), (-1.9, 2.6, "FATIGA PERCIBIDA", NARANJA),
                       (1.9, -2.6, "FATIGA OCULTA (SNC)", ROJO), (-1.9, -2.6, "FATIGA INTEGRAL", ROJO)]:
        fig_sc.add_annotation(x=x, y=y, text=t, showarrow=False, font=dict(color=c, size=10))
    estilo_fig(fig_sc, height=420 if movil else 480, leyenda_abajo=False)
    fig_sc.update_layout(showlegend=False, xaxis=dict(range=[-3.2, 3.2], title="Z wellness →  más fresco"),
                         yaxis=dict(range=[-3.2, 3.2], title="Z DRI →  mejor salto"))
    mostrar_fig(fig_sc)

# ==========================================
# 8. MOLESTIAS PRE-SESIÓN (solo zonas con casos)
# ==========================================
st.markdown("---")
st.markdown(f"#### Molestias pre-sesión ({fecha_es(fecha_sel)})")
total_disp = len(disp)
if total_disp == 0:
    st.warning("⚠️ No hay jugadores disponibles en la fecha seleccionada.")
else:
    zonas = ['Cuadriceps', 'Pubis', 'Adductores', 'Isquios', 'Gemelos']
    conteo = {z: [] for z in zonas}
    sin_molestia, duele_todo, con_molestia = [], [], []
    for _, r in disp.iterrows():
        zr = str(r['ZONA_DOLOR']).lower()
        if not tiene_molestia(zr):
            sin_molestia.append(r['JUGADOR']); continue
        con_molestia.append(r['JUGADOR'])
        if 'todo' in zr:
            duele_todo.append(r['JUGADOR'])
            for z in zonas: conteo[z].append(r['JUGADOR'])
        else:
            for z in zonas:
                if z.lower() in zr: conteo[z].append(r['JUGADOR'])

    tarjetas_kpi([
        {"titulo": "Disponibles", "valor": str(total_disp)},
        {"titulo": "Sin molestias", "valor": f"{len(sin_molestia) / total_disp * 100:.0f}%", "sub": f"{len(sin_molestia)} jugadores"},
        {"titulo": "Con alguna molestia", "valor": f"{len(con_molestia) / total_disp * 100:.0f}%", "sub": f"{len(con_molestia)} jugadores",
         "color": NARANJA if con_molestia else TEXTO},
        {"titulo": "“Me duele todo”", "valor": str(len(duele_todo)), "color": ROJO if duele_todo else TEXTO},
    ])
    zonas_con = [z for z in zonas if conteo[z]]
    for z in zonas_con:
        pct = len(conteo[z]) / total_disp * 100
        color = ROJO if pct >= 20 else NARANJA
        bloque_alerta(f"{z}: {len(conteo[z])} jugador(es) · {pct:.0f}%", conteo[z], color)
    if duele_todo:
        bloque_alerta("💥 Fatiga generalizada (me duele todo)", duele_todo, ROJO)
    sin_casos = [z for z in zonas if not conteo[z]]
    if sin_casos:
        st.caption("Sin casos hoy: " + ", ".join(sin_casos))

# ==========================================
# 9. TABLA DE DETALLE
# ==========================================
st.markdown("---")
st.markdown("#### 📋 Detalle por jugador")
t = df.copy()
t['Jugador'] = t['JUGADOR'].apply(nombre_bonito)

def flecha(z, invertir=False):
    if pd.isna(z): return ""
    if invertir: z = -z
    return " 🔺" if z > 0.1 else (" 🔻" if z < -0.1 else " =")

cols = {'Jugador': 'Jugador', 'ESTADO': 'Estado', 'WELLNESS_TOTAL': 'Media', 'SUEÑO': 'Sueño', 'DOLOR': 'Dolor',
        'ESTRÉS': 'Estrés', 'CARGA': 'Carga'}
if tiene_saltos:
    t['DRI'] = [f"{v:.2f}{flecha(z)}" if pd.notna(v) else "-" for v, z in zip(t['DRI_MEDIO'], t['Z_SALTO'])]
    t['Altura DJ'] = [f"{v:.1f}" if pd.notna(v) else "-" for v in t['ALTURA_MEDIA_CM']]
    t['TC (s)'] = [f"{v:.3f}" if pd.notna(v) else "-" for v in t['TC_MEDIO_S']]
    cols.update({'DRI': 'DRI', 'Altura DJ': 'Altura DJ (cm)', 'TC (s)': 'TC (s)'})
cols.update({'ZONA_DOLOR': 'Molestia', 'DETALLE_DOLOR': 'Detalle'})
if movil:
    cols = {k: v for k, v in cols.items() if k in ['Jugador', 'ESTADO', 'WELLNESS_TOTAL', 'ZONA_DOLOR']}

orden_estado = {"❌ Alerta integral": 0, "⚡ Alerta neuromuscular": 1, "⚠️ Fatiga subjetiva": 2, "🩹 Molestia": 3,
                "🟢 Sin problemas": 4, "🚑 Enfermería": 5}
t['_o'] = t['ESTADO'].map(orden_estado)
tf = t.sort_values(['_o', 'WELLNESS_TOTAL'])[list(cols.keys())].rename(columns=cols)

def resaltar_bajo(v):
    try:
        if float(v) < WELL_ALERTA: return f'background-color: {ROJO}33; color: #FF9B9B; font-weight: bold;'
    except (ValueError, TypeError): pass
    return 'color: #94A3B8;'

num_cols = [c for c in ['Media', 'Sueño', 'Dolor', 'Estrés', 'Carga'] if c in tf.columns]
sty = tf.style.map(resaltar_bajo, subset=num_cols).format({c: "{:.1f}" for c in num_cols}, na_rep="-")
if 'DRI' in tf.columns:
    sty = sty.map(lambda v: f'background-color: {ROJO}33; color: #FF9B9B; font-weight: bold;' if '🔻' in str(v) else '', subset=['DRI'])
st.dataframe(sty, width="stretch", hide_index=True, height=min(38 * (len(tf) + 1) + 4, 700))
