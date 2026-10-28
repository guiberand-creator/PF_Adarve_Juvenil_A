import os
import streamlit as st

def render_html(codigo_html: str, container=None):
    """Inserta HTML directamente en el DOM sin pasar por el compilador de Markdown."""
    c = container if container is not None else st
    if hasattr(c, "html"):
        c.html(codigo_html)
    else:
        c.markdown(codigo_html, unsafe_allow_html=True)

def inyectar_css(css_codigo: str):
    """Inyecta bloques <style> limpios sin sangría que el navegador pueda interpretar."""
    css_limpio = f"<style>\n{css_codigo.strip()}\n</style>"
    render_html(css_limpio)

def aplicar_estilos_globales():
    """Aplica fuentes oficiales del club, limpia el menú y ajusta el sidebar."""
    inyectar_css("""
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');

        /* Fuentes generales */
        html, body, [class*="css"], p, span, div, label {
            font-family: 'Aptos', sans-serif !important;
        }

        /* Títulos */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Barlow Condensed', sans-serif !important;
        }
        
        /* Ocultar elementos nativos de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Ajustes de interfaz limpia para el menú */
        [data-testid="stSidebarNav"] {
            padding-top: 10px;
        }
    """)

def mostrar_sello_autor():
    """Renderiza el sello/logo del autor en la barra lateral."""
    directorio_raiz = os.path.dirname(os.path.abspath(__file__))
    ruta_logo_png = os.path.join(directorio_raiz, "assets", "logo-guille_blanco.png")

    st.sidebar.markdown("---")
    if os.path.exists(ruta_logo_png):
        st.sidebar.image(ruta_logo_png, use_container_width=True)
        st.sidebar.caption("⚡ **Performance & Data Analytics**")
        st.sidebar.caption("© 2026 All Rights Reserved")
    else:
        st.sidebar.caption("⚡ **GUILLE PERFORMANCE**")
        st.sidebar.caption("Performance & Data Analytics")
        st.sidebar.caption("© 2026 All Rights Reserved")

def aplicar_diseno_responsive():
    """Fuerza a que imágenes, columnas y gráficos se adapten al 100% de la pantalla móvil."""
    inyectar_css("""
        /* Ajustes específicos para móviles (< 768px) */
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

            .stHeading h1 { font-size: 1.4rem !important; }
            .stHeading h2, .stHeading h3 { font-size: 1.1rem !important; }
            .stMarkdown p { font-size: 0.85rem !important; }
        }
    """)