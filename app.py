import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import unicodedata
import matplotlib.colors as mcolors

# Configuración de la página
st.set_page_config(
    page_title="CRAI Analytics - USTA Villavicencio",
    page_icon="📚",
    layout="wide"
)

# Estilo de gráficos
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

# --- ESTILOS PERSONALIZADOS (CSS) ---
def apply_custom_styles():
    st.markdown("""
        <style>
        /* Fondo general */
        .stApp { background-color: #ffffff; }
        
        /* Estilo para el Sidebar */
        [data-testid="stSidebar"] {
            background-color: #003870 !important;
        }
        
        /* Estilo para el st.info en el Sidebar */
        [data-testid="stSidebar"] [data-testid="stNotification"] {
            background-color: #003870 !important; /* Usar el mismo azul del sidebar */
            border-left: 5px solid #FFD700 !important; /* Borde amarillo/oro para destacar */
            color: white !important; /* Asegurar que el texto del st.info sea blanco */
        }
        [data-testid="stSidebar"] [data-testid="stNotification"] p,
        [data-testid="stSidebar"] [data-testid="stNotification"] li {
            color: white !important;
        }

        /* Botón de Upload en negro */
        [data-testid="stFileUploader"] section button {
            background-color: #000000 !important;
            color: #ffffff !important;
            border: 1px solid #ffffff !important;
        }
        [data-testid="stFileUploader"] section button:hover {
            background-color: #333333 !important;
        }
        
        /* Fondo blanco exclusivo para el recuadro del logo */
        [data-testid="stSidebar"] [data-testid="stImage"] {
            background-color: white !important;
            padding: 15px !important;
            display: flex;
            justify-content: center;
        }
        
        /* Forzar texto blanco en Sidebar (títulos, etiquetas, párrafos) */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] [data-testid="stNotificationContent"] {
            color: white !important;
        }
        
        /* Títulos en el área principal - Azul USTA */
        h1, h2, h3 {
            color: #003870 !important;
        }

        /* Tarjetas de métricas con mejor contraste */
        .stMetric {
            background-color: #f1f3f5;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #003870;
        }
        [data-testid="stMetricLabel"] {
            color: #495057 !important; /* Gris oscuro para la etiqueta */
        }
        [data-testid="stMetricValue"] {
            color: #003870 !important; /* Azul para el valor */
        }
        
        /* Botones de descarga */
        .stDownloadButton button {
            width: 100%;
            border-radius: 5px;
            border: 2px solid #003870 !important;
            color: #003870 !important;
            font-weight: bold;
        }
        .stDownloadButton button:hover {
            background-color: #003870;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)

def fix_mojibake(text):
    """
    Repara errores de codificación donde caracteres UTF-8 se interpretan como Latin-1.
    Ejemplo: 'ConstituciÃ³n' -> 'Constitución'
    """
    if not isinstance(text, str):
        return text
    try:
        # Si el texto contiene patrones típicos de UTF-8 mal decodificado (como Ã seguido de algo)
        # Intentamos re-codificar a latin-1 para obtener los bytes originales y decodificar como utf-8
        if 'Ã' in text or 'Â' in text or '©' in text:
            # Intentamos la reparación
            return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si falla, devolvemos el texto original para no perder información
        return text
    return text

def load_data(uploaded_file):
    """
    Carga de archivos con lógica de detección de codificación robusta.
    """
    extension = uploaded_file.name.split('.')[-1]
    
    if extension == 'csv':
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                # Volver al inicio del archivo para cada intento
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=encoding, sep=None, engine='python')
                return df
            except Exception:
                continue
        st.error("No se pudo determinar la codificación del CSV. Intente guardarlo como Excel.")
        return None
    else:
        return pd.read_excel(uploaded_file)

def clean_data(df):
    """
    Pipeline de limpieza automatizada.
    """
    # 1. Reparar jeroglíficos (Mojibake) persistentes
    # 2. Eliminar espacios en blanco en todas las columnas de texto
    # 3. Normalizar caracteres (asegurar que tildes sean un solo caracter Unicode)
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(fix_mojibake)
        df[col] = df[col].apply(lambda x: unicodedata.normalize('NFC', str(x)) if pd.notnull(x) else x)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Identificar columnas por nombres probables (ajustar según el reporte real)
    # Mapeo de nombres comunes en sistemas de bibliotecas
    col_mapping = {
        'Nombre': ['nombre', 'usuario', 'estudiante', 'lector'],
        'Carrera': ['carrera', 'programa', 'facultad', 'programa académico'],
        'Tematica': ['temática', 'tema', 'área', 'título', 'materia'],
        'Fecha': ['fecha', 'fecha préstamo', 'fec_prestamo']
    }
    
    final_cols = {}
    for standard_name, aliases in col_mapping.items():
        for col in df.columns:
            if col.lower() in aliases:
                final_cols[standard_name] = col
                break

    # Aplicar transformaciones si las columnas existen
    if 'Nombre' in final_cols:
        df[final_cols['Nombre']] = df[final_cols['Nombre']].str.title()
    
    if 'Carrera' in final_cols:
        df[final_cols['Carrera']] = df[final_cols['Carrera']].str.upper()
        
    if 'Tematica' in final_cols:
        df[final_cols['Tematica']] = df[final_cols['Tematica']].str.capitalize()

    # Manejo de fechas
    if 'Fecha' in final_cols:
        df[final_cols['Fecha']] = pd.to_datetime(df[final_cols['Fecha']], errors='coerce')
    
    return df, final_cols

# --- INTERFAZ DE USUARIO ---

apply_custom_styles()

# Barra lateral (Sidebar) para configuración y carga
with st.sidebar:
    st.image("logo usta.png", width=180)
    st.title("Configuración")
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Cargar reporte del sistema", type=["csv", "xlsx"])
    st.markdown("---")
    st.info("""
        **Instrucciones:**
        1. Suba el archivo CSV/Excel.
        2. El sistema limpiará tildes y formatos.
        3. Revise los gráficos generados.
        4. Descargue el archivo corregido.
    """)

st.title("📚 Dashboard de Analítica - CRAI USTA Villavicencio")

if uploaded_file is not None:
    with st.spinner('Procesando y desinfectando datos...'):
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            df, cols = clean_data(df_raw.copy())
            st.success("✅ Datos procesados: Se han corregido codificaciones y formatos de texto.")

            # --- SECCIÓN DE KPIs ---
            kpi1, kpi2, kpi3 = st.columns(3)
            
            total_prestamos = len(df)
            # Intentar contar usuarios únicos si existe la columna
            usuarios_unid = df[cols['Nombre']].nunique() if 'Nombre' in cols else "N/A"
            libros_unid = df[cols['Tematica']].nunique() if 'Tematica' in cols else "N/A"
            
            kpi1.metric("Total Préstamos", total_prestamos)
            kpi2.metric("Usuarios Únicos", usuarios_unid)
            kpi3.metric("Títulos/Temas Distintos", libros_unid)

            # --- SECCIÓN DE GRÁFICOS ---
            st.markdown("---")
            tab1, tab2 = st.tabs(["📈 Análisis de Demanda", "📅 Tendencias Temporales"])

            with tab1:
                col_left, col_right = st.columns(2)
                with col_left:
                    if 'Tematica' in cols:
                        st.subheader("Top 10 Temáticas")
                        top_themes = df[cols['Tematica']].value_counts().head(10)
                        fig, ax = plt.subplots()
                        sns.barplot(x=top_themes.values, y=top_themes.index, palette='Blues_r', ax=ax)
                        st.pyplot(fig)

                with col_right:
                    if 'Carrera' in cols:
                        st.subheader("Demanda por Programa")
                        top_programs = df[cols['Carrera']].value_counts().head(5)
                        
                        if top_programs.empty:
                            st.warning("No hay datos de programas académicos para mostrar.")
                        else:
                            fig, ax = plt.subplots()
                            
                            # Colores pasteles, azules y grises (sin verdes ni fucsias)
                            colors = ['#2E5A88', '#4A7AB5', '#8DA9C4', '#A5B5C1', '#D1D9E0']

                            # Function to determine text color based on background color luminance
                            def get_text_color_for_slice(color_hex):
                                # Convertir hex a RGB (escala 0-1)
                                rgb_color = mcolors.to_rgb(color_hex)
                                # Calculate luminance (0-1 range)
                                luminance = (0.299 * rgb_color[0] + 0.587 * rgb_color[1] + 0.114 * rgb_color[2])
                                return 'white' if luminance < 0.5 else 'black' # Threshold 0.5 for dark/light

                            # Plot the pie chart
                            wedges, texts, autotexts = ax.pie(top_programs, 
                                                              labels=top_programs.index, 
                                                              autopct='%1.1f%%', 
                                                              colors=colors, 
                                                              startangle=140,
                                                              pctdistance=0.85) # Adjust distance of percentages from center

                            # Set the color of the percentage labels (autotexts)
                            for i, autotext in enumerate(autotexts):
                                autotext.set_color(get_text_color_for_slice(colors[i]))
                                autotext.set_fontsize(10)
                                autotext.set_fontweight('bold')
                            st.pyplot(fig)

            with tab2:
                if 'Fecha' in cols and not df[cols['Fecha']].isnull().all():
                    st.subheader("Densidad de Préstamos por Día")
                    df['Dia_Semana'] = df[cols['Fecha']].dt.day_name()
                    orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    densidad = df['Dia_Semana'].value_counts().reindex(orden_dias).fillna(0)
                    
                    fig, ax = plt.subplots(figsize=(12, 4))
                    sns.lineplot(x=densidad.index, y=densidad.values, marker='o', color='#003870', linewidth=2.5)
                    plt.fill_between(densidad.index, densidad.values, alpha=0.2, color='#003870')
                    st.pyplot(fig)

            # --- MÓDULO DE DESCARGA ---
            with st.expander("💾 Exportar y Previsualizar"):
                st.dataframe(df.head(10), use_container_width=True)
                
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Datos_CRAI_Limpios')
                
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')

                col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                st.download_button(
                    label="Descargar en Excel (.xlsx)",
                    data=output_excel.getvalue(),
                    file_name="CRAI_Reporte_Limpio.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col_dl2:
                st.download_button(
                    label="Descargar en CSV (Compatible con Excel)",
                    data=csv_data,
                    file_name="CRAI_Reporte_Limpio.csv",
                    mime="text/csv"
                )
        else:
            st.error("No se pudo procesar el archivo. Verifique el formato.")
else:
    st.info("👋 Bienvenido. Por favor, cargue el archivo desde el panel de la izquierda para comenzar.")
