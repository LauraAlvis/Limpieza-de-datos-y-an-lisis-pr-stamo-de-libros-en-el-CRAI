import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import unicodedata

# Configuración de la página
st.set_page_config(
    page_title="CRAI Analytics - USTA Villavicencio",
    page_icon="📚",
    layout="wide"
)

# Estilo de gráficos
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

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

st.title("📚 Sistema de Preparación y Analítica - CRAI USTA")
st.markdown("""
Esta herramienta automatiza la limpieza de reportes de préstamos y genera indicadores 
clave para la sede Villavicencio.
""")

uploaded_file = st.file_uploader("Cargue el reporte del sistema de préstamos (.csv o .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    with st.spinner('Procesando y desinfectando datos...'):
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
            df, cols = clean_data(df_raw.copy())
            st.success("✅ Datos procesados: Se han corregido codificaciones y formatos de texto.")

            # --- SECCIÓN DE KPIs ---
            st.subheader("📊 Indicadores Clave (KPIs)")
            kpi1, kpi2, kpi3 = st.columns(3)
            
            total_prestamos = len(df)
            # Intentar contar usuarios únicos si existe la columna
            usuarios_unid = df[cols['Nombre']].nunique() if 'Nombre' in cols else "N/A"
            libros_unid = df[cols['Tematica']].nunique() if 'Tematica' in cols else "N/A"
            
            kpi1.metric("Total Préstamos", total_prestamos)
            kpi2.metric("Usuarios Únicos", usuarios_unid)
            kpi3.metric("Títulos/Temas Distintos", libros_unid)

            # --- SECCIÓN DE GRÁFICOS ---
            col_left, col_right = st.columns(2)

            with col_left:
                if 'Tematica' in cols:
                    st.subheader("Top 10 Temáticas más Solicitadas")
                    top_themes = df[cols['Tematica']].value_counts().head(10)
                    fig, ax = plt.subplots()
                    sns.barplot(x=top_themes.values, y=top_themes.index, palette='Blues_r', ax=ax)
                    ax.set_xlabel("Cantidad de Préstamos")
                    st.pyplot(fig)

            with col_right:
                if 'Carrera' in cols:
                    st.subheader("Demanda por Programa Académico")
                    top_programs = df[cols['Carrera']].value_counts().head(5)
                    fig, ax = plt.subplots()
                    # Gráfico de dona para variar la visualización
                    plt.pie(top_programs, labels=top_programs.index, autopct='%1.1f%%', 
                            colors=sns.color_palette('viridis'), startangle=140)
                    st.pyplot(fig)

            # --- ANÁLISIS TEMPORAL ---
            if 'Fecha' in cols and not df[cols['Fecha']].isnull().all():
                st.subheader("📅 Análisis de Densidad Temporal (Préstamos por Día)")
                df['Dia_Semana'] = df[cols['Fecha']].dt.day_name()
                # Ordenar días correctamente
                orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                densidad = df['Dia_Semana'].value_counts().reindex(orden_dias).fillna(0)
                
                fig, ax = plt.subplots(figsize=(12, 4))
                sns.lineplot(x=densidad.index, y=densidad.values, marker='o', color='#1f77b4', linewidth=2.5)
                plt.fill_between(densidad.index, densidad.values, alpha=0.2)
                st.pyplot(fig)

            # --- MÓDULO DE DESCARGA ---
            st.divider()
            st.subheader("💾 Exportar Datos Limpios")
            
            # Preparar buffer para descarga
            # Opción 1: Excel
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Datos_CRAI_Limpios')
            
            # Opción 2: CSV con codificación específica para Excel en Windows (UTF-8-SIG)
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

            # Mostrar previsualización
            with st.expander("Ver previsualización de datos limpios"):
                st.dataframe(df.head(20))
        else:
            st.error("No se pudo procesar el archivo. Verifique el formato.")
else:
    st.info("👋 Por favor, cargue un archivo para comenzar el análisis.")
