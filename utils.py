import streamlit as st
import os
import base64

def aplicar_estilos_globales():
    """Aplica las fuentes del club (Barlow Condensed y Aptos) a toda la página."""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');

            /* Fuentes generales */
            html, body, [class*="css"], p, span, div, label {
                font-family: 'Aptos', sans-serif !important;
            }

            /* Títulos */
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Barlow Condensed', sans-serif !important;
            }
            
            /* Ocultar elementos de Streamlit */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)


def aplicar_estilos_globales():
    """
    Aplica los estilos CSS globales de la aplicación.
    """
    st.markdown("""
        <style>
        /* Ajustes de interfaz limpia para el menú */
        [data-testid="stSidebarNav"] {
            padding-top: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

def mostrar_sello_autor():
    """
    Renderiza el sello/logo del autor en la barra lateral usando
    la función oficial nativa de Streamlit para garantizar compatibilidad total.
    """
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
    st.markdown("""
    <style>
    /* Ajustes específicos para móviles (< 768px) */
    @media (max-width: 768px) {
        /* Evita que las imágenes se sobredimensionen */
        img {
            max-width: 100% !important;
            height: auto !important;
            object-fit: contain !important;
        }

        /* Fuerza a que las columnas de Streamlit se apilen limpiamente */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Fuerza a los gráficos a no desbordar el ancho de pantalla */
        .js-plotly-plot, .plot-container {
            width: 100% !important;
            max-width: 100% !important;
        }

        /* Tipografía más contenida */
        .stHeading h1 { font-size: 1.4rem !important; }
        .stHeading h2, .stHeading h3 { font-size: 1.1rem !important; }
        .stMarkdown p { font-size: 0.85rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)