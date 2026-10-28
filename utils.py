import os
import base64
import streamlit as st

def render_html(codigo_html: str, container=None):
    """Inserta HTML directamente en el DOM sin que Markdown lo escape como texto."""
    c = container if container is not None else st
    if hasattr(c, "html"):
        c.html(codigo_html)
    else:
        c.markdown(codigo_html, unsafe_allow_html=True)

def inyectar_css(css_codigo: str):
    """Inyecta bloques CSS limpios garantizando que el navegador los interprete."""
    css_limpio = f"<style>\n{css_codigo.strip()}\n</style>"
    render_html(css_limpio)

def aplicar_estilos_globales():
    """Aplica tipografía homogénea oficial del club a toda la aplicación
    y protege de forma blindada los iconos nativos de Streamlit."""
    inyectar_css("""
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        /* 1. Tipografía Base y Contenido General en toda la App */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], p, span:not([class*="material"]):not([data-testid="stIconMaterial"]), div, label, button, input, select {
            font-family: 'Aptos', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* 2. Títulos homogéneos en todas las páginas */
        h1, h2, h3, h4, h5, h6, .stHeading, [data-testid="stHeadingWithActionElements"] {
            font-family: 'Barlow Condensed', sans-serif !important;
            letter-spacing: 0.5px !important;
            font-weight: 700 !important;
        }

        /* 3. REGLA BLINDADA: Proteger iconos nativos de Streamlit para evitar que aparezca 'keyboard_double_arrow_right' */
        [data-testid="stIconMaterial"], 
        .material-symbols-rounded, 
        [class*="material-symbols"], 
        [data-testid="collapsedControl"] span,
        [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebar"] button span {
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
            font-size: 24px !important;
            letter-spacing: normal !important;
            text-transform: none !important;
        }
        
        /* 4. Ocultar elementos nativos no deseados */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* 5. Ajustes de interfaz limpia para el menú */
        [data-testid="stSidebarNav"] {
            padding-top: 10px;
        }
    """)

def mostrar_sello_sidebar():
    """Inserta el pie de página con el logo en el sidebar de forma limpia y universal,
    sin que aparezca código CSS en pantalla."""
    directorio_raiz = os.path.dirname(os.path.abspath(__file__))
    # Busca el logo tanto si se llama desde la raíz (Inicio) como desde pages/
    rutas_posibles = [
        os.path.join(directorio_raiz, "assets", "logo-guille_blanco.png"),
        os.path.join(directorio_raiz, "..", "assets", "logo-guille_blanco.png")
    ]
    ruta_logo = next((r for r in rutas_posibles if os.path.exists(r)), None)

    if ruta_logo:
        with open(ruta_logo, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            
        render_html(f"""
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
                font-family: 'Aptos', 'Inter', sans-serif !important;
            }}
            </style>
            <div class="footer-sello-unico">
                <img src="data:image/png;base64,{b64}">
                <p>© 2026 All Rights Reserved</p>
            </div>
        """, container=st.sidebar)

def aplicar_diseno_responsive():
    """Fuerza a que imágenes, columnas y gráficos se adapten al 100% de la pantalla móvil
    sin reducir el tamaño de títulos o tipografías en ordenadores de sobremesa."""
    inyectar_css("""
        @media (max-width: 768px) {
            img {
                max-width: 100% !important;
                height: auto !important;
                object-fit: contain !important;
            }

            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }

            .js-plotly-plot, .plot-container {
                width: 100% !important;
                max-width: 100% !important;
            }

            .stHeading h1 { font-size: 1.6rem !important; }
            .stHeading h2, .stHeading h3 { font-size: 1.25rem !important; }
            .stMarkdown p { font-size: 0.9rem !important; }
        }
    """)