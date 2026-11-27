"""
utils.py — Estilo común, helpers de gráficos y utilidades de la app.

Novedades respecto a la versión anterior:
- CSS móvil corregido: Streamlit renombró las columnas a data-testid="stColumn"
  (la regla antigua "column" ya no hacía nada).
- Paleta "resaltar / atenuar": lo que requiere atención va en color,
  lo normal en gris translúcido.
- Helpers de Plotly pensados para móvil (sin zoom con el dedo, leyendas abajo,
  barras horizontales por jugador con altura automática).
- Tarjetas KPI y "chips" de jugadores en HTML que se recolocan solas en el móvil.
- Formato de nombres (sin guiones bajos) y de fechas (dd/mm/aaaa).
- Botón para refrescar datos y preferencia "Vista móvil" compartida entre páginas.
"""
import os
import re
import base64
import html as _html
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import io
import time
import requests

# =============================================================================
# 1. PALETA ÚNICA DE LA APP
# =============================================================================
# Colores "de atención": solo se usan cuando un dato se sale de lo normal.
ROJO = "#EF4444"        # exceso / riesgo / alerta
NARANJA = "#F59E0B"     # aviso moderado
AZUL = "#38BDF8"        # por debajo de lo esperado (subcarga, déficit)
VERDE = "#22C55E"       # positivo (usar con moderación)
ACENTO = "#E11D48"      # color del club para destacar (jugador seleccionado, partido...)

# Colores "neutros": lo que está dentro de la normalidad.
NEUTRO = "rgba(148, 163, 184, 0.35)"        # barras / puntos normales
NEUTRO_FUERTE = "rgba(148, 163, 184, 0.65)"  # líneas normales
NEUTRO_TEXTO = "#94A3B8"
TEXTO = "#E6EDF3"
FONDO_TARJETA = "#161B22"
BORDE = "#26303B"

CFG_PLOTLY = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


def color_alfa(hex_color: str, alfa: float) -> str:
    """'#RRGGBB' -> 'rgba(r,g,b,alfa)'."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alfa})"


def colores_por_fecha(n: int, color_ultima: str = ACENTO):
    """Para gráficos con varias fechas: la última en color, las anteriores en gris
    cada vez más transparente (la más antigua, la más tenue)."""
    if n <= 0:
        return []
    if n == 1:
        return [color_ultima]
    alfas = np.linspace(0.18, 0.5, n - 1)
    return [f"rgba(148,163,184,{a:.2f})" for a in alfas] + [color_ultima]


# =============================================================================
# 2. FORMATO DE TEXTOS Y FECHAS
# =============================================================================
def nombre_bonito(nombre) -> str:
    """'Daniel_Diaz_Alvaro' -> 'Daniel Diaz Alvaro'."""
    if nombre is None or (isinstance(nombre, float) and np.isnan(nombre)):
        return ""
    return " ".join(str(nombre).replace("_", " ").split())


def nombre_corto(nombre) -> str:
    """'Francisco_Javier_Marian_Medina' -> 'Francisco J. Marian' (para ejes de gráficos)."""
    partes = nombre_bonito(nombre).split()
    if len(partes) <= 2:
        return " ".join(partes)
    if len(partes) == 3:
        return f"{partes[0]} {partes[1]}"
    return f"{partes[0]} {partes[1][0]}. {partes[2]}"


def fecha_es(valor, corta: bool = False) -> str:
    """Cualquier fecha -> '18/11/2026' (o '18/11' si corta=True)."""
    try:
        if isinstance(valor, str):
            v = valor.strip().split(" ")[0]
            if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", v):          # ya viene como dd/mm/aaaa
                return v[:-5] if corta else v
            d = pd.to_datetime(v, dayfirst=not re.match(r"^\d{4}-", v))
        else:
            d = pd.to_datetime(valor)
        if pd.isna(d):
            return "-"
        return d.strftime("%d/%m") if corta else d.strftime("%d/%m/%Y")
    except Exception:
        return str(valor)


def etiqueta_sesion(tipo) -> str:
    """'-4' -> 'MD-4', '+1 (compensatorio)' -> 'MD+1 (compensatorio)'."""
    t = str(tipo).strip()
    if t[:1] in "+-" and t[1:2].isdigit():
        return "MD" + t
    return t


# =============================================================================
# 3. INYECCIÓN DE HTML / CSS
# =============================================================================
def render_html(codigo_html: str, container=None):
    """Inserta HTML directamente en el DOM sin que Markdown lo escape como texto."""
    c = container if container is not None else st
    if hasattr(c, "html"):
        c.html(codigo_html)
    else:
        c.markdown(codigo_html, unsafe_allow_html=True)


def inyectar_css(css_codigo: str):
    """Inyecta bloques CSS limpios garantizando que el navegador los interprete."""
    render_html(f"<style>\n{css_codigo.strip()}\n</style>")


def aplicar_estilos_globales():
    """Tipografía del club + estilos comunes de tarjetas/chips."""
    inyectar_css(f"""
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], p, span:not([class*="material"]):not([data-testid="stIconMaterial"]), div, label, button, input, select {{
            font-family: 'Aptos', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}
        h1, h2, h3, h4, h5, h6, .stHeading, [data-testid="stHeadingWithActionElements"] {{
            font-family: 'Barlow Condensed', sans-serif !important;
            letter-spacing: 0.5px !important;
            font-weight: 700 !important;
        }}
        [data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"],
        [data-testid="collapsedControl"] span, [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebar"] button span {{
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
            letter-spacing: normal !important;
            text-transform: none !important;
        }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        [data-testid="stSidebarNav"] {{ padding-top: 10px; }}

        /* ---------- Tarjetas KPI (rejilla que se adapta sola) ---------- */
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 4px 0 12px 0; }}
        .kpi {{ background: {FONDO_TARJETA}; border: 1px solid {BORDE}; border-radius: 10px; padding: 10px 12px; min-width: 0; }}
        .kpi .k {{ color: {NEUTRO_TEXTO}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }}
        .kpi .v {{ color: {TEXTO}; font-size: 1.45rem; font-weight: 800; line-height: 1.15; margin-top: 2px; overflow-wrap: anywhere; }}
        .kpi .s {{ color: {NEUTRO_TEXTO}; font-size: 0.78rem; margin-top: 2px; }}

        /* ---------- Chips de jugadores ---------- */
        .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 8px 0; }}
        .chip {{ border-radius: 999px; padding: 3px 10px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; }}
        .bloque-alerta {{ border-left: 4px solid; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; background: rgba(255,255,255,0.03); }}
        .bloque-alerta .t {{ font-weight: 800; font-size: 0.9rem; margin-bottom: 6px; }}
        details.desplegable summary {{ cursor: pointer; color: {NEUTRO_TEXTO}; font-size: 0.85rem; }}
    """)


def aplicar_diseno_responsive():
    """Ajustes para pantallas estrechas (móvil / tablet)."""
    inyectar_css("""
        @media (max-width: 768px) {
            img { max-width: 100% !important; height: auto !important; object-fit: contain !important; }
            /* Nombre actual del contenedor de columna en Streamlit (antes era "column") */
            [data-testid="stColumn"], [data-testid="column"] {
                width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
            }
            .block-container { padding: 3.6rem 0.7rem 4rem 0.7rem !important; }   /* deja sitio a la barra superior */
            .solo-pc, [class*="st-key-solo_pc"] { display: none !important; }
            .js-plotly-plot, .plot-container { width: 100% !important; max-width: 100% !important; }
            h1, .stHeading h1 { font-size: 1.55rem !important; }
            h2, h3, .stHeading h2, .stHeading h3 { font-size: 1.2rem !important; }
            .stMarkdown p { font-size: 0.92rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
            .kpi .v { font-size: 1.2rem; }
            .footer-sello-unico { display: none !important; }
        }
        @media (min-width: 769px) { .solo-movil, [class*="st-key-solo_movil"] { display: none !important; } }
        @media (max-height: 720px) { .footer-sello-unico { display: none !important; } }
    """)


def mostrar_sello_sidebar():
    """Logo al pie del sidebar (se oculta en pantallas bajas para no tapar el menú)."""
    directorio_raiz = os.path.dirname(os.path.abspath(__file__))
    rutas_posibles = [
        os.path.join(directorio_raiz, "assets", "logo-guille_blanco.png"),
        os.path.join(directorio_raiz, "..", "assets", "logo-guille_blanco.png"),
    ]
    ruta_logo = next((r for r in rutas_posibles if os.path.exists(r)), None)
    if not ruta_logo:
        return
    with open(ruta_logo, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    render_html(f"""
        <style>
        .footer-sello-unico {{ position: fixed; bottom: 20px; left: 10px; width: 260px; text-align: center;
            z-index: 1; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.15); pointer-events: none; }}
        .footer-sello-unico img {{ width: 195px; height: auto; margin-bottom: 8px; display: inline-block; }}
        .footer-sello-unico p {{ font-size: 11px !important; color: #CCCCCC !important; margin: 2px 0 0 0 !important; }}
        </style>
        <div class="footer-sello-unico"><img src="data:image/png;base64,{b64}"><p>© 2026 All Rights Reserved</p></div>
    """, container=st.sidebar)


def configurar_pagina(titulo: str, icono: str = "⚡"):
    """set_page_config + estilos comunes. Llamar SIEMPRE lo primero en cada página."""
    st.set_page_config(page_title=titulo, page_icon=icono, layout="wide")
    _FALLOS_DESCARGA.clear()   # que no se arrastren avisos de otra página
    aplicar_estilos_globales()
    aplicar_diseno_responsive()
    mostrar_sello_sidebar()


def exigir_login_staff():
    if not st.session_state.get("logeado"):
        st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
        st.stop()


def controles_sidebar(mostrar_actualizar: bool = True) -> bool:
    """Botón de refrescar datos + interruptor 'Vista móvil'.
    Devuelve True si la vista móvil (compacta) está activada.
    En la app de jugadores se oculta el botón de actualizar (mostrar_actualizar=False)."""
    if "pref_movil" not in st.session_state:
        st.session_state["pref_movil"] = False
    with st.sidebar:
        movil = st.toggle("📱 Vista móvil (compacta)", value=st.session_state["pref_movil"],
                          help="Simplifica tablas y gráficos grandes para pantallas pequeñas.")
        st.session_state["pref_movil"] = movil
        if mostrar_actualizar and st.button("🔄 Actualizar datos", width="stretch",
                     help="Vuelve a descargar los Google Sheets y los Excel."):
            st.cache_data.clear()
            st.rerun()
    return movil


def vista_movil() -> bool:
    return bool(st.session_state.get("pref_movil", False))


# =============================================================================
# 4. COMPONENTES HTML: KPIs, CHIPS, BLOQUES DE ALERTA
# =============================================================================
def tarjetas_kpi(items, container=None):
    """items: lista de dicts {'titulo', 'valor', 'sub' (opcional), 'color' (opcional)}."""
    bloques = []
    for it in items:
        color = it.get("color") or TEXTO
        sub = f"<div class='s'>{it['sub']}</div>" if it.get("sub") else ""
        bloques.append(f"<div class='kpi'><div class='k'>{it['titulo']}</div>"
                       f"<div class='v' style='color:{color}'>{it['valor']}</div>{sub}</div>")
    render_html(f"<div class='kpi-grid'>{''.join(bloques)}</div>", container)


def chips_html(nombres, color=NEUTRO_TEXTO, sufijos=None) -> str:
    """Devuelve HTML con un 'chip' por jugador. sufijos: dict nombre -> texto extra."""
    sufijos = sufijos or {}
    partes = []
    for n in nombres:
        extra = f" · {sufijos[n]}" if n in sufijos and sufijos[n] != "" else ""
        partes.append(f"<span class='chip' style='background:{color_alfa(color, 0.15) if color.startswith('#') else 'rgba(148,163,184,0.15)'};"
                      f"color:{color}; border:1px solid {color_alfa(color, 0.35) if color.startswith('#') else BORDE}'>"
                      f"{_html.escape(nombre_bonito(n))}{_html.escape(extra)}</span>")
    return f"<div class='chips'>{''.join(partes)}</div>"


def bloque_alerta(titulo, nombres, color=ROJO, sufijos=None, vacio="✅ Sin avisos", container=None):
    """Bloque con borde de color, título y chips. Si no hay nombres, muestra 'vacio' atenuado."""
    if nombres:
        cuerpo = chips_html(nombres, color, sufijos)
        borde, col_t = color, color
    else:
        cuerpo = f"<div style='color:{NEUTRO_TEXTO}; font-size:0.85rem'>{vacio}</div>"
        borde, col_t = BORDE, NEUTRO_TEXTO
    render_html(f"<div class='bloque-alerta' style='border-left-color:{borde}'>"
                f"<div class='t' style='color:{col_t}'>{titulo}</div>{cuerpo}</div>", container)


# =============================================================================
# 5. PLOTLY: ESTILO COMÚN Y GRÁFICOS POR JUGADOR
# =============================================================================
def _limpiar_categorias(fig):
    """Quita los guiones bajos de los nombres usados como categorías en los ejes."""
    for tr in fig.data:
        for eje in ("x", "y"):
            vals = getattr(tr, eje, None)
            if vals is None:
                continue
            try:
                lista = list(vals)
            except TypeError:
                continue
            if lista and all(isinstance(v, str) for v in lista) and any("_" in v for v in lista):
                setattr(tr, eje, [nombre_bonito(v) for v in lista])
    return fig


def estilo_fig(fig, height=None, leyenda_abajo=True, titulo=None, margen_izq=10, limpiar_nombres=True):
    """Estilo oscuro común + configuración amigable con el móvil."""
    fig.update_layout(
        template="plotly_dark",
        font=dict(family="Inter, sans-serif", color=NEUTRO_TEXTO, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="#1e293b", font_size=13, font_color="#f8fafc"),
        margin=dict(l=margen_izq, r=10, t=(80 if leyenda_abajo else 45) if titulo else (40 if leyenda_abajo else 25), b=10),
        dragmode=False,
    )
    if titulo:
        fig.update_layout(title=dict(text=titulo, font=dict(size=14, color=TEXTO), x=0, xanchor="left"))
    if height:
        fig.update_layout(height=height)
    if leyenda_abajo:
        # Leyenda ARRIBA: abajo choca con las etiquetas del eje X en pantallas estrechas
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)))
    fig.update_xaxes(fixedrange=True, showgrid=False, zeroline=False, automargin=True)
    fig.update_yaxes(fixedrange=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, automargin=True)
    if limpiar_nombres:
        _limpiar_categorias(fig)
    return fig


def mostrar_fig(fig, key=None, **kwargs):
    """st.plotly_chart con la configuración móvil por defecto."""
    return st.plotly_chart(fig, width="stretch", config=CFG_PLOTLY, key=key, **kwargs)


def barras_jugadores(nombres, valores, colores, textos=None, titulo=None, eje_titulo=None,
                     lineas=None, hover=None, orden="asc", rango=None, alto_fila=19, acortar=True,
                     vertical=False, alto=430, ids=None):
    """Barras por jugador.
    - vertical=False: barras horizontales compactas (para el MÓVIL; toda la plantilla cabe en una pantalla).
    - vertical=True: jugadores a lo ancho, como antes (para el ORDENADOR; todo de un vistazo sin hacer scroll).
    - colores: lista de colores (usa NEUTRO para lo normal y un color fuerte para lo que destaca).
    - lineas: lista de dicts {'x': valor, 'color': ..., 'texto': ...} para umbrales verticales.
    - orden: 'asc' (el valor más bajo arriba), 'desc' o None (respetar el orden dado)."""
    df = pd.DataFrame({"n": [nombre_corto(n) if acortar else n for n in nombres], "v": list(valores), "c": list(colores),
                       "t": list(textos) if textos is not None else [None] * len(nombres),
                       "h": list(hover) if hover is not None else [None] * len(nombres),
                       "id": list(ids) if ids is not None else list(nombres)})
    if vertical:
        if orden == "asc":
            df = df.sort_values("v", ascending=True, na_position="last")     # el valor más bajo, a la izquierda
        elif orden == "desc":
            df = df.sort_values("v", ascending=False, na_position="last")
        fig = go.Figure(go.Bar(
            x=df["n"], y=df["v"], marker=dict(color=df["c"], line=dict(width=0)), customdata=df["id"],
            text=df["t"] if textos is not None else None, textposition="outside", cliponaxis=False,
            textfont=dict(size=11, color=TEXTO),
            hovertext=df["h"] if hover is not None else None,
            hoverinfo="text" if hover is not None else "x+y",
        ))
        for ln in (lineas or []):
            extra = dict(annotation_text=ln["texto"], annotation_position="top right",
                         annotation_font=dict(size=10, color=ln.get("color", NEUTRO_TEXTO))) if ln.get("texto") else {}
            fig.add_hline(y=ln["x"], line=dict(color=ln.get("color", NEUTRO_FUERTE), width=1.5, dash=ln.get("dash", "dash")), **extra)
        estilo_fig(fig, height=alto, leyenda_abajo=False, titulo=titulo)
        fig.update_layout(bargap=0.25, showlegend=False)
        fig.update_xaxes(tickangle=-45, tickfont=dict(size=11, color=TEXTO), type="category")
        fig.update_yaxes(title_text=eje_titulo, showgrid=True, gridcolor="rgba(255,255,255,0.06)")
        if rango is not None:
            fig.update_yaxes(range=rango)
        return fig

    if orden == "asc":
        df = df.sort_values("v", ascending=False, na_position="first")   # Plotly pinta de abajo arriba
    elif orden == "desc":
        df = df.sort_values("v", ascending=True, na_position="first")
    else:
        df = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df["v"], y=df["n"], orientation="h", marker=dict(color=df["c"], line=dict(width=0)), customdata=df["id"],
        text=df["t"] if textos is not None else None, textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=TEXTO),
        hovertext=df["h"] if hover is not None else None,
        hoverinfo="text" if hover is not None else "x+y",
    ))
    for ln in (lineas or []):
        extra = dict(annotation_text=ln["texto"], annotation_position=ln.get("pos", "top"),
                     annotation_font=dict(size=10, color=ln.get("color", NEUTRO_TEXTO))) if ln.get("texto") else {}
        fig.add_vline(x=ln["x"], line=dict(color=ln.get("color", NEUTRO_FUERTE), width=1.5, dash=ln.get("dash", "dash")), **extra)
    alto_h = max(260, alto_fila * len(df) + 90)
    estilo_fig(fig, height=alto_h, leyenda_abajo=False, titulo=titulo)
    fig.update_layout(bargap=0.2, showlegend=False)
    fig.update_yaxes(tickfont=dict(size=10, color=TEXTO), gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title_text=eje_titulo, showgrid=True, gridcolor="rgba(255,255,255,0.06)")
    if rango is not None:
        fig.update_xaxes(range=rango)
    return fig


def mostrar_segun_pantalla(fig_pc, fig_movil, key, movil=None, **kwargs):
    """Dibuja la versión de ordenador en pantallas anchas y la de móvil en pantallas estrechas
    (lo decide el navegador con CSS). Con 'Vista móvil' activada se muestra solo la de móvil."""
    if movil is None:
        movil = vista_movil()
    if movil:
        return [mostrar_fig(fig_movil, key=f"{key}_m", **kwargs)]
    with st.container(key=f"solo_pc_{key}"):
        e1 = mostrar_fig(fig_pc, key=f"{key}_pc", **kwargs)
    with st.container(key=f"solo_movil_{key}"):
        e2 = mostrar_fig(fig_movil, key=f"{key}_m", **kwargs)
    return [e1, e2]


def nombre_pulsado(eventos):
    """Devuelve el 'customdata' del primer punto/barra pulsado en una lista de eventos de st.plotly_chart."""
    for ev in eventos or []:
        try:
            puntos = ev["selection"]["points"]
        except Exception:
            continue
        for p in puntos:
            cd = p.get("customdata")
            if cd is not None:
                return cd[0] if isinstance(cd, (list, tuple)) else cd
    return None


# =============================================================================
# 6. DESCARGA DE GOOGLE SHEETS (con tiempo límite, reintento y sin guardar fallos)
# =============================================================================
_FALLOS_DESCARGA = []


@st.cache_data(ttl=600, show_spinner=False)
def leer_sheet_csv(url: str) -> pd.DataFrame:
    """Descarga un Google Sheet como CSV. Espera como máximo 12 s y reintenta una vez.
    Si falla, LANZA un error: los errores no se guardan en caché, así que en la siguiente
    recarga se vuelve a intentar (antes un fallo puntual podía quedarse guardado)."""
    ultimo = None
    for intento in range(2):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
            if r.status_code == 200 and r.text.strip():
                return pd.read_csv(io.StringIO(r.text))
            ultimo = f"respuesta {r.status_code}"
        except requests.exceptions.RequestException as e:
            ultimo = type(e).__name__
        time.sleep(1.5)
    raise RuntimeError("Google Sheets no ha respondido a tiempo (conexión lenta o caída). "
                       "Pulsa 🔄 Actualizar datos en la barra lateral o recarga la página en un momento. "
                       f"[{ultimo}]")


NOMBRES_SHEETS = {
    "1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s": "RPE",
    "12q2mpHSAq-HGAQv3qr5EU9Gm5yttbls_UtXhoiAOO9o": "Wellness",
    "1JyR7HA1zCU06-QPqHSCPaYac3hLHuSz5": "Calendario de partidos",
    "1cOh6eOiCTySipJhZUlYwTrYTpBr6NVn4D-KCoWXlxeI": "Cuestionario de jugadores (cumpleaños)",
    "1r7nUPbRWDjKpZW-Jwex1HFNpDcHiCTKTwLPF7YfHL2Y": "Drop Jump (Chronojump)",
}


def descargar_sheet(sheet_id: str, gid=None) -> pd.DataFrame:
    """Versión 'tolerante': si la descarga falla devuelve una tabla vacía y anota QUÉ Sheet ha fallado."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv" + (f"&gid={gid}" if gid is not None else "")
    try:
        return leer_sheet_csv(url)
    except Exception as e:
        motivo = str(e).split("[")[-1].rstrip("]") if "[" in str(e) else str(e)
        _FALLOS_DESCARGA.append(f"{NOMBRES_SHEETS.get(sheet_id, sheet_id[:10])} ({motivo})")
        return pd.DataFrame()


def comprobar_descargas(*funciones_cacheadas):
    """Llamar justo después de cargar los datos. Si algún Sheet falló, se borra la caché de esas
    funciones (para no quedarse 10 min con datos incompletos) y se avisa de cuál ha sido."""
    if _FALLOS_DESCARGA:
        for f in funciones_cacheadas:
            try: f.clear()
            except Exception: pass
        fallidos = ", ".join(sorted(set(_FALLOS_DESCARGA)))
        st.warning(f"⚠️ No se ha podido leer: **{fallidos}**. Faltan esos datos en esta página. "
                   "Pulsa 🔄 Actualizar datos en la barra lateral o recarga en un momento.")
        _FALLOS_DESCARGA.clear()


# =============================================================================
# 7. JUGADORES QUE HAN DEJADO EL EQUIPO (columna "Estado" = Baja en data/Posiciones.xlsx)
# =============================================================================
# No se borra nada de los Excel ni de los Sheets: la app solo los OCULTA como jugador
# (selectores, tablas, alertas, gráficos por jugador, rankings, portal de jugadores).
# Sus sesiones antiguas SIGUEN contando en las medias y totales del equipo.
import unicodedata as _ud

_RUTA_POSICIONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Posiciones.xlsx")


def clave_nombre(nombre) -> str:
    """Normaliza un nombre para cruzar fuentes: sin tildes, minúsculas, sin guiones bajos."""
    if nombre is None or (isinstance(nombre, float) and np.isnan(nombre)):
        return ""
    t = _ud.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    return " ".join(t.replace("_", " ").replace(".", " ").lower().split())


@st.cache_data(ttl=600, show_spinner=False)
def _claves_exjugadores(_mtime) -> tuple:
    try:
        df = pd.read_excel(_RUTA_POSICIONES)
    except Exception:
        return tuple()
    df.columns = df.columns.astype(str).str.strip()
    col_e = next((c for c in df.columns if clave_nombre(c) in ("estado", "baja", "situacion")), None)
    if col_e is None:
        return tuple()
    col_j = "Jugador" if "Jugador" in df.columns else df.columns[0]
    marcados = df[df[col_e].astype(str).map(clave_nombre).str.startswith("baja")]
    return tuple(sorted({clave_nombre(n) for n in marcados[col_j].dropna() if clave_nombre(n)}))


def claves_exjugadores() -> tuple:
    try:
        mtime = os.path.getmtime(_RUTA_POSICIONES)
    except OSError:
        mtime = 0
    return _claves_exjugadores(mtime)


def es_exjugador(nombre) -> bool:
    """True si el jugador está marcado como Baja. Tolera formatos distintos del nombre
    ('Ikki_Muller_Salak', 'Ikki Müller Salak', 'ikki muller'...)."""
    bajas = claves_exjugadores()
    if not bajas:
        return False
    k = clave_nombre(nombre)
    if not k:
        return False
    if k in bajas:
        return True
    t = k.split()
    for b in bajas:
        tb = b.split()
        corto, largo = (t, tb) if len(t) <= len(tb) else (tb, t)
        # p. ej. 'ikki muller' dentro de 'ikki muller salak' (mínimo nombre + un apellido, en orden)
        if len(corto) >= 2 and largo[:len(corto)] == corto:
            return True
    return False


def quitar_exjugadores(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Devuelve el DataFrame sin las filas de jugadores de baja (si la columna existe)."""
    if df is None or df.empty or col not in df.columns or not claves_exjugadores():
        return df
    marcas = {v: es_exjugador(v) for v in df[col].dropna().unique()}
    return df[~df[col].map(marcas).fillna(False).astype(bool)]


def sin_exjugadores(nombres):
    """Filtra una lista de nombres."""
    if not claves_exjugadores():
        return list(nombres)
    return [n for n in nombres if not es_exjugador(n)]
