import streamlit as st
import pandas as pd
import altair as alt 
from datetime import datetime, timedelta
import conector

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Gestión Rugby", layout="centered", page_icon="🏉")
URL_FORMULARIO_ASISTENCIA = "https://docs.google.com/forms/d/e/1FAIpQLSfZF8sRpapNBPzpGxh07vr_W2sv6mPv2yfsmyM5EyG7MKCoJA/viewform"

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_datos_asistencia(df):
    """
    Función CLAVE: Limpia fechas y nombres para que los cálculos sean exactos.
    """
    if df.empty: return df

    # 1. Limpiar Nombres (Columna 1): Quita espacios y estandariza
    col_nombre = df.columns[1]
    df[col_nombre] = df[col_nombre].astype(str).str.strip() 

    # 2. Limpiar Fechas (Columna 0)
    col_fecha = df.columns[0]
    # Convertimos a fecha usando format='mixed' para soportar 5/2/2026 y 05/02/2026
    df['fecha_dt'] = pd.to_datetime(df[col_fecha], dayfirst=True, format='mixed', errors='coerce').dt.date
    
    # 3. BORRAR BASURA: Eliminamos filas donde la fecha no se entendió
    df = df.dropna(subset=['fecha_dt'])
    
    return df

# --- FUNCIONES DE CÁLCULO ---
def calcular_estado_asistencia(porcentaje):
    if porcentaje > 85: return "🟢", "Excelente"
    elif porcentaje >= 65: return "🟡", "Regular"
    else: return "🔴", "Baja"

def obtener_metricas_jugador(df_asistencia, nombre_jugador):
    if df_asistencia.empty: return 0, 0, 0

    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    df_mes = df_asistencia[df_asistencia['fecha_dt'] >= inicio_mes]
    df_semana = df_asistencia[df_asistencia['fecha_dt'] >= inicio_semana]

    total_anio = df_asistencia['fecha_dt'].nunique()
    total_mes = df_mes['fecha_dt'].nunique()
    total_semana = df_semana['fecha_dt'].nunique()

    col_nombre = df_asistencia.columns[1]
    # Filtramos asegurando que no haya espacios basura
    nombre_jugador = str(nombre_jugador).strip()
    
    asist_anio = df_asistencia[df_asistencia[col_nombre] == nombre_jugador]['fecha_dt'].nunique()
    asist_mes = df_mes[df_mes[col_nombre] == nombre_jugador]['fecha_dt'].nunique()
    asist_semana = df_semana[df_semana[col_nombre] == nombre_jugador]['fecha_dt'].nunique()

    pct_anio = (asist_anio / total_anio * 100) if total_anio > 0 else 0
    pct_mes = (asist_mes / total_mes * 100) if total_mes > 0 else 0
    pct_semana = (asist_semana / total_semana * 100) if total_semana > 0 else 0

    return pct_anio, pct_mes, pct_semana

# --- PANTALLAS ---
def mostrar_dashboard(df_jugadores):
    st.title("📊 Tablero de Comando")
    
    # 1. CARGA INICIAL DE DATOS (Vital para evitar errores)
    df_asistencia = conector.cargar_datos("DB_Asistencia")
    
    # Preparar mapa de tipos (Para saber si es Foward o Back)
    mapa_tipos = {}
    if not df_jugadores.empty and 'Nombre' in df_jugadores.columns and 'Tipo' in df_jugadores.columns:
        # Creamos un diccionario: {"juan perez": "Foward", "pedro": "Back"}
        # Usamos minúsculas para facilitar la búsqueda
        for index, row in df_jugadores.iterrows():
            nombre_norm = str(row['Nombre']).strip().lower()
            if 'Apellido' in df_jugadores.columns:
                nombre_norm = (str(row['Nombre']).strip() + " " + str(row['Apellido']).strip()).lower()
            
            mapa_tipos[nombre_norm] = str(row['Tipo']).lower()

    # --- MÉTRICAS GLOBALES ---
    total_plantel = len(df_jugadores)
    df_lesionados = conector.cargar_datos("Lesionados")
    lesionados_activos = 0
    if not df_lesionados.empty:
        df_lesionados.columns = [c.strip().lower() for c in df_lesionados.columns]
        col_gravedad = next((c for c in df_lesionados.columns if 'gravedad' in c or 'estado' in c), None)
        if col_gravedad:
            activos = df_lesionados[df_lesionados[col_gravedad].astype(str).str.lower().str.contains("rojo|amarillo", na=False)]
            lesionados_activos = len(activos)
            
    disponibles = total_plantel - lesionados_activos
    porcentaje_disp = (disponibles / total_plantel) if total_plantel > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Plantel Total", total_plantel)
    c2.metric("Disponibles", disponibles, delta=f"{porcentaje_disp:.0%}")
    c3.metric("Lesionados", lesionados_activos, delta=-lesionados_activos, delta_color="inverse")
    
    st.divider()

    # --- NUEVA SECCIÓN: CONTADOR DE ASISTENCIA DIARIA ---
    st.subheader("📅 Detalle de Asistencia por Día")
    
    if not df_asistencia.empty:
        df_asistencia = limpiar_datos_asistencia(df_asistencia)
        
        # Selector de fechas (de la más nueva a la más vieja)
        fechas_unicas = sorted(df_asistencia['fecha_dt'].unique(), reverse=True)
        fecha_selecc = st.selectbox("Selecciona Fecha:", fechas_unicas)
        
        if fecha_selecc:
            # Filtramos solo los presentes de ese día
            asistentes_hoy = df_asistencia[df_asistencia['fecha_dt'] == fecha_selecc]
            lista_nombres_hoy = asistentes_hoy.iloc[:, 1].unique()
            
            total_hoy = len(lista_nombres_hoy)
            fwds = 0
            backs = 0
            sin_id = 0
            
            # Clasificamos uno por uno
            for jugador in lista_nombres_hoy:
                nombre_limpio = str(jugador).strip().lower()
                tipo = mapa_tipos.get(nombre_limpio, "desconocido")
                
                # Lógica de detección (ajusta las palabras clave según tu Excel)
                if "foward" in tipo or "fwd" in tipo or "pilar" in tipo or "segunda" in tipo or "ala" in tipo or "octavo" in tipo or "hooker" in tipo:
                    fwds += 1
                elif "back" in tipo or "3/4" in tipo or "medio" in tipo or "apertura" in tipo or "centro" in tipo or "wing" in tipo or "fullback" in tipo:
                    backs += 1
                else:
                    sin_id += 1
            
            # Mostramos los contadores
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Presentes", total_hoy, border=True)
            k2.metric("Fowards 🐗", fwds, border=True)
            k3.metric("Backs 🏃", backs, border=True)
            if sin_id > 0:
                k4.metric("Sin Identificar ⚠️", sin_id, border=True, help="Nombres que no coinciden con la lista oficial")
            else:
                k4.metric("Identificados", "100%", border=True)

    else:
        st.info("No hay registros de asistencia para mostrar.")

    st.divider()

    # --- GRÁFICOS ---
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("⚖️ Roles (Plantel)")
        if 'Tipo' in df_jugadores.columns:
            source = df_jugadores['Tipo'].value_counts().reset_index()
            source.columns = ['Tipo', 'Cantidad']
            base = alt.Chart(source).encode(theta=alt.Theta("Cantidad", stack=True), color="Tipo")
            pie = base.mark_arc(outerRadius=100) + base.mark_text(radius=120).encode(text="Cantidad", color=alt.value("black"))
            st.altair_chart(pie, use_container_width=True)

    with col_der:
        st.subheader("📈 Evolución")
        if not df_asistencia.empty:
            diaria = df_asistencia.groupby('fecha_dt')[df_asistencia.columns[1]].nunique().reset_index()
            diaria.columns = ['Fecha', 'Jugadores']
            
            grafico = alt.Chart(diaria).mark_area(color="#2ecc71", opacity=0.8, line=True).encode(
                x=alt.X('Fecha:T', axis=alt.Axis(format='%d/%m')),
                y='Jugadores:Q',
                tooltip=['Fecha', 'Jugadores']
            )
            st.altair_chart(grafico, use_container_width=True)

def mostrar_plantel(df_jugadores):
    st.header("🏉 Plantel Superior")
    
    # Normalizamos nombres
    if 'Nombre' in df_jugadores.columns:
        df_jugadores['Nombre'] = df_jugadores['Nombre'].astype(str).str.strip()
    if 'Apellido' in df_jugadores.columns:
        df_jugadores['Apellido'] = df_jugadores['Apellido'].astype(str).str.strip()
        df_jugadores['Nombre Completo'] = df_jugadores['Nombre'] + " " + df_jugadores['Apellido']
    else:
        df_jugadores['Nombre Completo'] = df_jugadores['Nombre']

    df_asistencia = conector.cargar_datos("DB_Asistencia")
    mapa_asistencia = {}
    
    if not df_asistencia.empty:
        df_asistencia = limpiar_datos_asistencia(df_asistencia)
        total_days = df_asistencia['fecha_dt'].nunique()
        
        if total_days > 0:
            col_nombre_asist = df_asistencia.columns[1]
            conteos = df_asistencia.groupby(col_nombre_asist)['fecha_dt'].nunique()
            
            for jugador, count in conteos.items():
                pct = (count / total_days) * 100
                emoji, _ = calcular_estado_asistencia(pct)
                mapa_asistencia[jugador] = f"{emoji} {pct:.0f}%"

    df_jugadores['Asistencia'] = df_jugadores['Nombre Completo'].apply(lambda x: mapa_asistencia.get(x, "🔴 0%"))
    
    lista = sorted(df_jugadores['Nombre Completo'].unique().tolist())
    seleccion = st.selectbox("Buscar Jugador:", lista, index=None, placeholder="Escribe para buscar...")

    st.divider()

    if seleccion:
        datos = df_jugadores[df_jugadores['Nombre Completo'] == seleccion].iloc[0]
        st.subheader(f"👤 {seleccion}")
        
        p_anio, p_mes, p_sem = obtener_metricas_jugador(df_asistencia, seleccion)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Año", f"{p_anio:.0f}%")
        m2.metric("Mes", f"{p_mes:.0f}%")
        m3.metric("Semana", f"{p_sem:.0f}%")
        st.progress(p_anio/100)
        
        st.divider()
        st.write(f"**Puesto:** {datos.get('Puesto', '-')}")
        st.write(f"**Celular:** {datos.get('Celular personal', '-')}")
        
        with st.expander("Ver ficha completa"):
            st.write(datos.astype(str))
    else:
        st.dataframe(df_jugadores[['Nombre Completo', 'Asistencia', 'Puesto']], use_container_width=True, height=600)

def modulo_asistencia(df_jugadores):
    st.header("✅ Tomar Asistencia")
    tab1, tab2 = st.tabs(["QR", "Manual"])
    with tab1:
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={URL_FORMULARIO_ASISTENCIA}")
        st.write(f"[Link al Formulario]({URL_FORMULARIO_ASISTENCIA})")
    with tab2:
        names = sorted(df_jugadores['Nombre'].unique()) if 'Nombre' in df_jugadores.columns else []
        with st.form("asist_manual"):
            sel = st.multiselect("Presentes:", names)
            if st.form_submit_button("Guardar"):
                for p in sel:
                    conector.guardar_registro("DB_Asistencia", [datetime.now().strftime("%d/%m/%Y"), p, "Manual"])
                st.success("Guardado.")

def modulo_medico(df):
    st.header("🏥 Médico")
    df_l = conector.cargar_datos("Lesionados")
    st.dataframe(df_l, use_container_width=True)

# --- MAIN ---
def main():
    menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "Plantel", "Asistencia", "Médico"])
    df = conector.cargar_datos("Jugadores")
    if df.empty:
        st.error("No se pudo cargar la lista de jugadores. Revisa 'conector.py'")
        return
        
    df.columns = [c.strip().capitalize() for c in df.columns]

    if menu == "📊 Dashboard": mostrar_dashboard(df)
    elif menu == "Plantel": mostrar_plantel(df)
    elif menu == "Asistencia": modulo_asistencia(df)
    elif menu == "Médico": modulo_medico(df)

if __name__ == "__main__":
    main()