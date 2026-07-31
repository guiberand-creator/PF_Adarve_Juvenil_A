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