import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from utils import aplicar_diseno_responsive

# Al principio de la página
aplicar_diseno_responsive()

# PROTEGER SUBPÁGINA: Si no viene logueado desde la portada, lo bloqueamos
if 'logeado' not in st.session_state or not st.session_state['logeado']:
    st.warning("⚠️ Por favor, inicia sesión en la página principal para acceder.")
    st.stop()


# -----------------------------------------------------------------------------
# SELLO FIJO AL PIE DEL SIDEBAR (+30% TAMAÑO)
# -----------------------------------------------------------------------------
_carpeta_pages = os.path.dirname(os.path.abspath(__file__))
_ruta_logo = os.path.abspath(os.path.join(_carpeta_pages, "..", "assets", "logo-guille_blanco.png"))

if os.path.exists(_ruta_logo):
    with open(_ruta_logo, "rb") as _f:
        import base64
        _b64 = base64.b64encode(_f.read()).decode()
        
    st.sidebar.markdown(f"""
        <style>
        .footer-sello-unico {{
            position: fixed;
            bottom: 20px;
            left: 10px;
            width: 260px;
            text-align: center;
            z-index: 999;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
        }}
        .footer-sello-unico img {{
            width: 195px; /* Aumentado un 30% */
            height: auto;
            margin-bottom: 8px;
        }}
        .footer-sello-unico p {{
            font-size: 11px !important;
            color: #CCCCCC !important;
            margin: 2px 0 0 0 !important;
            letter-spacing: 0.5px;
        }}
        </style>

        <div class="footer-sello-unico">
            <img src="data:image/png;base64,{_b64}">
            <p>© 2026 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CONEXIÓN Y MAPEO BLINDADO CON TU GOOGLE SHEETS (RESPUESTAS DEL FORMULARIO RPE)
# ==============================================================================
@st.cache_data(ttl=10)
def obtener_datos_carga_real():
    sheet_id = "1Q8z8qhMJPt4p110OjpvutzklzYhO_jjdZysDbCER45s"
    gid = "1785642271"
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip()
        
        # FIX CRÍTICO: Forzamos de forma estricta el formato de fecha Día-Mes-Año (dayfirst=True)
        df['Fecha'] = pd.to_datetime(df['Marca temporal'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Fecha'])
        
        # Mapeo de identidad y variables de volumen
        df['Nombre'] = df['Nombre y apellidos'].fillna('Anónimo')
        df['Tipo de Sesión'] = df['Tipo de sesión'].fillna('Entreno').astype(str).str.strip()
        df['Duracion'] = pd.to_numeric(df['Minutos entreno/partido'], errors='coerce').fillna(0)
        
        # BUSCADOR DINÁMICO DE COLUMNAS (Evita roturas por cambios de texto en el Form)
        col_cardio = [c for c in df.columns if 'CARDIO' in c.upper()]
        col_muscular = [c for c in df.columns if 'MUSCULAR' in c.upper()]
        col_emocional = [c for c in df.columns if 'EMOCIONAL' in c.upper() or 'ÁNIMO' in c.upper() or 'ANIMO' in c.upper()]
        
        # Asignación numérica indexada
        df['RPE_Cardio'] = pd.to_numeric(df[col_cardio[0]], errors='coerce').fillna(0) if col_cardio else 0
        df['RPE_Muscular'] = pd.to_numeric(df[col_muscular[0]], errors='coerce').fillna(0) if col_muscular else 0
        df['Estado_Animo'] = pd.to_numeric(df[col_emocional[0]], errors='coerce').fillna(5) if col_emocional else 5
        
        # sRPE Módulo General (Promedio ponderado de la sesión)
        df['RPE_General'] = (df['RPE_Cardio'] + df['RPE_Muscular']) / 2
        
        # Regla de cómputo para minutos reales en competición
        df['Minutos Jugados'] = df.apply(lambda r: r['Duracion'] if 'partido' in str(r['Tipo de Sesión']).lower() else 0, axis=1)
                
        return df, None
    except Exception as e:
        return None, str(e)

# Ejecución de la extracción limpia
df_raw, error_hoja = obtener_datos_carga_real()

# ==============================================================================
# 2. INTERFAZ GENERAL DE CARGA INTERNA
# ==============================================================================
st.title("CARGA INTERNA (RPE)")
st.caption("Control de métricas de carga interna y percepción de esfuerzo del equipo ADARVE JUVENIL DH.")

if error_hoja:
    st.error(f"Error de mapeo o conexión con Google Sheets: {error_hoja}")
elif df_raw is None or df_raw.empty:
    st.warning("Base de datos vacía o no estructurada. Revisa las respuestas del formulario.")
else:
    # --------------------------------------------------------------------------
    # FILTRADO TÁCTICO DE EXCLUSIONES (Wellness y Minutos)
    # --------------------------------------------------------------------------
    df_filtrado = df_raw[df_raw['Tipo de Sesión'].astype(str).str.lower().str.strip() != 'entreno a parte/lesión'].copy()
    df_filtrado['Carga_Individual'] = df_filtrado['RPE_General'] * df_filtrado['Duracion']
    df_filtrado['Semana'] = df_filtrado['Fecha'].dt.isocalendar().week
    
    df_colectivo = df_filtrado[~((df_filtrado['Tipo de Sesión'].astype(str).str.lower().str.strip() == 'partido') & (df_filtrado['Minutos Jugados'] < 70))].copy()

    # ==============================================================================
    # BLOCK 1 (LO PRIMERO): SISTEMA DE ALERTAS AUTOMÁTICAS (TODA LA PLANTILLA)
    # ==============================================================================
    st.markdown("---")
    st.markdown("## 🔍 SISTEMA DE ALERTAS AUTOMÁTICAS (TODA LA PLANTILLA)")
    
    alertas_sobrecarga = []
    alertas_subentreno = []
    alertas_desmotivacion = []
    
    for j in df_filtrado['Nombre'].unique():
        df_j = df_filtrado[df_filtrado['Nombre'] == j].sort_values('Fecha').copy()
        if len(df_j) >= 1:
            df_j['Aguda'] = df_j['Carga_Individual'].rolling(window=7, min_periods=1).mean()
            df_j['Cronica'] = df_j['Carga_Individual'].rolling(window=28, min_periods=1).mean()
            df_j['ACWR'] = df_j['Aguda'] / df_j['Cronica']
            
            df_a_temp = df_j.set_index('Fecha').resample('D')['Estado_Animo'].mean().ffill()
            media_a_15d = float(df_a_temp.rolling(window=15, min_periods=1).mean().iloc[-1]) if not df_a_temp.empty else 5.0
            
            ultimo_acwr = df_j['ACWR'].iloc[-1]
            ultimo_animo = df_j['Estado_Animo'].iloc[-1]
            
            if ultimo_acwr > 1.5: 
                alertas_sobrecarga.append(f"**{j}** (ACWR: {ultimo_acwr:.2f})")
            elif ultimo_acwr < 0.8: 
                alertas_subentreno.append(f"**{j}** (ACWR: {ultimo_acwr:.2f})")
                
            if ultimo_animo < 4.0 or ultimo_animo < (media_a_15d - 1.5):
                alertas_desmotivacion.append(f"**{j}** (Ánimo: {ultimo_animo} | MM15d: {media_a_15d:.1f})")
    
    col_al1, col_al2, col_al3 = st.columns(3)
    with col_al1:
        if alertas_sobrecarga: 
            st.error("❌ **SOBRECARGA / RIESGO LESIÓN**\n\n" + "\n\n".join(alertas_sobrecarga))
        else: 
            st.success("✅ Cargas agudas bajo control en toda la plantilla.")
    with col_al2:
        if alertas_subentreno: 
            st.warning("⚠️ **SUB-ENTRENAMIENTO**\n\n" + "\n\n".join(alertas_subentreno))
        else: 
            st.info("👍 Ningún jugador en niveles críticos de infra-carga.")
    with col_al3:
        if alertas_desmotivacion: 
            st.error("🧠 **BAJOS DE MOTIVACIÓN / ALERTA WELLNESS**\n\n" + "\n\n".join(alertas_desmotivacion))
        else: 
            st.success("😊 Índices de bienestar estables en el grupo.")

    # ==============================================================================
    # BLOCK 2: PANEL DE CONTROL GRUPAL (EQUIPO)
    # ==============================================================================
    st.markdown("---")
    st.markdown("## 📊 PANEL DE CONTROL GRUPAL")
    
    # 1. Agrupación diaria
    df_diario_equipo = df_colectivo.groupby(df_colectivo['Fecha'].dt.date).agg({
        'Carga_Individual': 'mean', 
        'RPE_Muscular': 'mean', 
        'RPE_Cardio': 'mean', 
        'Tipo de Sesión': 'first'
    }).sort_index().reset_index()
    
    df_diario_equipo['Fecha_dt'] = pd.to_datetime(df_diario_equipo['Fecha'])
    df_diario_equipo['Semana'] = df_diario_equipo['Fecha_dt'].dt.isocalendar().week
    df_diario_equipo['Tipo_Txt'] = df_diario_equipo['Tipo de Sesión']
    
    # 2. Mapeo de Semanas de Temporada (2026/2027)
    semana_inicio_temporada = 32 
    
    def calcular_semana_futbolistica_diario(row):
        sem_ano = row['Semana']
        ano = row['Fecha_dt'].year
        if ano == 2026:
            if sem_ano >= semana_inicio_temporada: 
                return f"Sem {int(sem_ano - semana_inicio_temporada + 1)}"
            else: 
                return f"Sem {int(sem_ano - semana_inicio_temporada)}"
        else:
            semanas_restantes_2026 = 52 - semana_inicio_temporada + 1
            return f"Sem {int(semanas_restantes_2026 + sem_ano)}"

    df_diario_equipo['Sem_Txt'] = df_diario_equipo.apply(calcular_semana_futbolistica_diario, axis=1)
    df_diario_equipo['Eje_X_Diario'] = (
        df_diario_equipo['Sem_Txt'] + " - " + 
        df_diario_equipo['Fecha_dt'].dt.strftime('%d %b')
    )
    
    # 3. Macro métricas semanales
    df_semanal = df_colectivo.groupby(['Semana', df_colectivo['Fecha'].dt.date]).agg({'Carga_Individual': 'mean'}).reset_index()
    df_macro = df_semanal.groupby('Semana').agg(
        Carga_Semanal=('Carga_Individual', 'sum'), Media_Carga=('Carga_Individual', 'mean'), Desv_Carga=('Carga_Individual', 'std')
    ).reset_index()
    df_macro['Desv_Carga'] = df_macro['Desv_Carga'].fillna(0)
    df_macro['Monotonia'] = df_macro.apply(lambda r: r['Media_Carga'] / r['Desv_Carga'] if r['Desv_Carga'] > 0 else 1.0, axis=1)
    df_macro['Training_Strain'] = df_macro['Carga_Semanal'] * df_macro['Monotonia']

    df_mes_semana = df_colectivo.groupby('Semana')['Fecha'].min().reset_index()
    
    def calcular_semana_futbolistica(fila):
        sem_ano = fila['Semana']
        ano = fila['Fecha'].year
        if ano == 2026:
            if sem_ano >= semana_inicio_temporada: return int(sem_ano - semana_inicio_temporada + 1)
            else: return int(sem_ano - semana_inicio_temporada)
        else:
            semanas_restantes_2026 = 52 - semana_inicio_temporada + 1
            return int(semanas_restantes_2026 + sem_ano)

    df_mes_semana['Semana_Temporada'] = df_mes_semana.apply(calcular_semana_futbolistica, axis=1)
    meses_es = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
    df_mes_semana['Mes_Txt'] = df_mes_semana['Fecha'].dt.month.map(meses_es)
    
    df_macro = df_macro.merge(df_mes_semana[['Semana', 'Semana_Temporada', 'Mes_Txt']], on='Semana', how='left')
    df_macro = df_macro.sort_values('Semana_Temporada')
    df_macro['Eje_X_Labels'] = "Sem " + df_macro['Semana_Temporada'].astype(str) + " (" + df_macro['Mes_Txt'].fillna('') + ")"

    # Diseño a 2 Columnas
    col_graf1, col_graf2 = st.columns([1.1, 1])
    
    # COLUMNA 1: Gestión de Sesión (Día a Día)
    with col_graf1:
        st.markdown("#### Gestión de Sesión (Día a Día)")
        fig_diario = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_diario.add_trace(
            go.Bar(
                x=df_diario_equipo['Eje_X_Diario'], y=df_diario_equipo['Carga_Individual'], 
                name="Volumen Carga", marker_color='#B31F24',
                text=df_diario_equipo['Tipo_Txt'], textposition='outside', cliponaxis=False
            ), secondary_y=False
        )
        fig_diario.add_trace(
            go.Scatter(x=df_diario_equipo['Eje_X_Diario'], y=df_diario_equipo['RPE_Muscular'], name="RPE Muscular (Fuerza)", line=dict(color='#FFC107', width=2.5), mode='lines+markers'),
            secondary_y=True
        )
        fig_diario.add_trace(
            go.Scatter(x=df_diario_equipo['Eje_X_Diario'], y=df_diario_equipo['RPE_Cardio'], name="RPE Cardio (Aeróbico)", line=dict(color='#00A8E8', width=2.5), mode='lines+markers'),
            secondary_y=True
        )
        
        # Separadores entre semanas (Lunes)
        for idx, row in df_diario_equipo.iterrows():
            if row['Fecha_dt'].weekday() == 0:
                fig_diario.add_vline(x=row['Eje_X_Diario'], line_width=1, line_dash="dash", line_color="#888888")

        fig_diario.update_layout(
            template="plotly_dark", margin=dict(t=50, b=20, l=10, r=10), 
            hovermode="x unified", height=380, 
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
            xaxis=dict(type='category')
        )
        fig_diario.update_yaxes(title_text="Volumen (RPE*Min)", secondary_y=False)
        fig_diario.update_yaxes(range=[0, 10.5], secondary_y=True)
        st.plotly_chart(fig_diario, use_container_width=True)
        
    # COLUMNA 2: Bloque Acumulado Semanal
    with col_graf2:
        st.markdown("#### Bloque Acumulado Semanal")
        fig_sem = make_subplots(specs=[[{"secondary_y": True}]])
        fig_sem.add_trace(go.Bar(x=df_macro['Eje_X_Labels'], y=df_macro['Carga_Semanal'], name="Carga Semanal", marker_color='#7A1215'), secondary_y=False)
        fig_sem.add_trace(go.Scatter(x=df_macro['Eje_X_Labels'], y=df_macro['Monotonia'], name="Monotonía", line=dict(color='#FFC107', width=2.5), mode='lines+markers'), secondary_y=True)
        fig_sem.add_hline(y=2.0, line_dash="dash", line_color="#B31F24", secondary_y=True)
        fig_sem.update_layout(template="plotly_dark", margin=dict(t=50, b=20, l=10, r=10), hovermode="x unified", height=380, legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0), xaxis=dict(type='category'))
        fig_sem.update_yaxes(title_text="Carga Semanal (UA)", secondary_y=False)
        st.plotly_chart(fig_sem, use_container_width=True)
        
    st.markdown("#### Historial de Estrés Orgánico (Training Strain Colectivo)")
    fig_strain = go.Figure()
    fig_strain.add_trace(go.Scatter(x=df_macro['Eje_X_Labels'], y=df_macro['Training_Strain'], name="Strain", fill='tozeroy', line=dict(color='#B31F24', width=2)))
    fig_strain.update_layout(template="plotly_dark", height=180, margin=dict(t=10, b=10), xaxis=dict(type='category'))
    st.plotly_chart(fig_strain, use_container_width=True)

    # ==============================================================================
    # BLOCK 3: CONTROL Y FICHA INDIVIDUAL
    # ==============================================================================
    st.markdown("---")
    st.markdown("## 👤 FICHA DE ANÁLISIS DETALLADO INDIVIDUAL")
    
    jugador_sel = st.selectbox("Selecciona un jugador para inspeccionar su histórico:", df_raw['Nombre'].unique())
    df_jugador = df_filtrado[df_filtrado['Nombre'] == jugador_sel].sort_values('Fecha').copy()
    
    if not df_jugador.empty:
        df_jugador['Aguda'] = df_jugador['Carga_Individual'].rolling(window=7, min_periods=1).mean()
        df_jugador['Cronica'] = df_jugador['Carga_Individual'].rolling(window=28, min_periods=1).mean()
        df_jugador['ACWR'] = df_jugador['Aguda'] / df_jugador['Cronica']
        
        ultimo_acwr = df_jugador['ACWR'].iloc[-1]
        df_animo_temp = df_jugador.set_index('Fecha').resample('D')['Estado_Animo'].mean().ffill()
        media_animo_15d = float(df_animo_temp.rolling(window=15, min_periods=1).mean().iloc[-1])
        ultimo_animo = float(df_jugador['Estado_Animo'].iloc[-1])
        
        df_jugador['Tipo_Txt'] = df_jugador['Tipo de Sesión']
        
        c_ind1, c_ind2, c_ind3 = st.columns([1, 1, 1])
        
        with c_ind1:
            fig_acwr = go.Figure()
            fig_acwr.add_trace(go.Scatter(x=df_jugador['Fecha'], y=df_jugador['ACWR'], name="ACWR", line=dict(color='#FFFFFF', width=2.5), mode='lines+markers'))
            fig_acwr.add_hline(y=1.5, line_color="#B31F24", line_width=1.5)
            fig_acwr.add_hline(y=1.3, line_dash="dash", line_color="#FFC107")
            fig_acwr.add_hline(y=0.8, line_dash="dash", line_color="#FFC107")
            fig_acwr.update_layout(title="<b>Evolución del ACWR</b>", template="plotly_dark", yaxis_range=[0, 2.2], height=340, margin=dict(t=60, b=30, l=15, r=15))
            st.plotly_chart(fig_acwr, use_container_width=True)
            
        with c_ind2:
            fig_animo = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = ultimo_animo,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"<b>Estado Anímico</b><br><span style='font-size:0.85em;color:gray;'>MM15d: {media_animo_15d:.1f}</span>", 'font': {'size': 15}},
                delta = {'reference': media_animo_15d, 'increasing': {'color': "#2ECC71"}, 'decreasing': {'color': "#B31F24"}},
                gauge = {
                    'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#FFFFFF"}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 2, 'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 4], 'color': 'rgba(179, 31, 36, 0.25)'},
                        {'range': [4, 7], 'color': 'rgba(255, 193, 7, 0.15)'},
                        {'range': [7, 10], 'color': 'rgba(46, 204, 113, 0.15)'}
                    ],
                }
            ))
            fig_animo.update_layout(template="plotly_dark", height=340, margin=dict(t=70, b=10, l=10, r=10))
            st.plotly_chart(fig_animo, use_container_width=True)
            
        with c_ind3:
            fig_perfil = go.Figure()
            fig_perfil.add_trace(go.Bar(x=df_jugador['Fecha'], y=df_jugador['RPE_Muscular'], name="Muscular (Fuerza)", marker_color='#FFC107'))
            fig_perfil.add_trace(go.Bar(x=df_jugador['Fecha'], y=df_jugador['RPE_Cardio'], name="Cardio (Aeróbico)", marker_color='#00A8E8', text=df_jugador['Tipo_Txt'], textposition='outside', cliponaxis=False))
            fig_perfil.update_layout(
                title="<b>Tipología de la Fatiga</b>", template="plotly_dark", barmode='stack', yaxis_range=[0, 22], height=340, 
                margin=dict(t=60, b=70, l=15, r=15), hovermode="x unified", 
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
            )
            fig_perfil.update_yaxes(title_text="RPE Total")
            st.plotly_chart(fig_perfil, use_container_width=True)
    else:
        st.info("No se registran suficientes entrenamientos válidos para este jugador.")