import streamlit as st
import pandas as pd
import altair as alt # Librería gráfica nativa de Streamlit
from datetime import datetime, timedelta
import conector

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Gestión Rugby", layout="centered", page_icon="🏉")

# LINK DEL FORMULARIO
URL_FORMULARIO_ASISTENCIA = "https://docs.google.com/forms/d/e/1FAIpQLSfZF8sRpapNBPzpGxh07vr_W2sv6mPv2yfsmyM5EyG7MKCoJA/viewform"

# --- DICCIONARIOS ---
MAPA_PUESTOS = {
    1: "Pilar Izq", 2: "Hooker", 3: "Pilar Der",
    4: "2da Línea", 5: "2da Línea",
    6: "Ala", 7: "Ala", 8: "Octavo",
    9: "Medio Scrum", 10: "Apertura",
    11: "Wing", 12: "Centro", 13: "Centro", 14: "Wing",
    15: "Fullback"
}

# --- FUNCIONES DE AYUDA Y CÁLCULO ---
def limpiar_y_separar_numeros(valor_celda):
    if pd.isna(valor_celda) or valor_celda == "": return []
    texto = str(valor_celda).replace(".0", "").replace('.', ',')
    return [p.strip() for p in texto.split(',') if p.strip() != ""]

def traducir_puestos_visual(valor_celda):
    numeros = limpiar_y_separar_numeros(valor_celda)
    nombres = []
    for n in numeros:
        if n.isdigit(): nombres.append(MAPA_PUESTOS.get(int(n), n))
        else: nombres.append(n)
    return " | ".join(nombres)

def calcular_estado_asistencia(porcentaje):
    """Devuelve el emoji y color según el porcentaje."""
    if porcentaje > 85:
        return "🟢", "Excelente"
    elif porcentaje >= 65:
        return "🟡", "Regular"
    else:
        return "🔴", "Baja"

def obtener_metricas_jugador(df_asistencia, nombre_jugador):
    """Calcula % Año, % Mes y % Semana para un jugador específico."""
    if df_asistencia.empty:
        return 0, 0, 0

    # 1. Preparar fechas
    col_fecha = df_asistencia.columns[0]
    # Aseguramos formato fecha (date)
    df_asistencia['fecha_dt'] = pd.to_datetime(df_asistencia[col_fecha], dayfirst=True, errors='coerce').dt.date
    
    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    # Inicio de semana (Lunes)
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    # 2. Filtrar DataFrames por rangos de tiempo
    df_mes = df_asistencia[df_asistencia['fecha_dt'] >= inicio_mes]
    df_semana = df_asistencia[df_asistencia['fecha_dt'] >= inicio_semana]

    # 3. Calcular Totales (Denominadores: Días que hubo entrenamiento)
    total_entrenamientos_anio = df_asistencia['fecha_dt'].nunique()
    total_entrenamientos_mes = df_mes['fecha_dt'].nunique()
    total_entrenamientos_semana = df_semana['fecha_dt'].nunique()

    # 4. Calcular Asistencias del Jugador (Numeradores)
    # Filtramos por jugador y contamos fechas únicas
    asist_anio = df_asistencia[df_asistencia.iloc[:, 1] == nombre_jugador]['fecha_dt'].nunique()
    asist_mes = df_mes[df_mes.iloc[:, 1] == nombre_jugador]['fecha_dt'].nunique()
    asist_semana = df_semana[df_semana.iloc[:, 1] == nombre_jugador]['fecha_dt'].nunique()

    # 5. Calcular Porcentajes (Evitando división por cero)
    pct_anio = (asist_anio / total_entrenamientos_anio * 100) if total_entrenamientos_anio > 0 else 0
    pct_mes = (asist_mes / total_entrenamientos_mes * 100) if total_entrenamientos_mes > 0 else 0
    pct_semana = (asist_semana / total_entrenamientos_semana * 100) if total_entrenamientos_semana > 0 else 0

    return pct_anio, pct_mes, pct_semana

# --- DASHBOARD (TABLERO DE COMANDO) ---
def mostrar_dashboard(df_jugadores):
    st.title("📊 Tablero de Comando")
    
    total_plantel = len(df_jugadores)
    
    df_lesionados = conector.cargar_datos("Lesionados")
    lesionados_activos = 0
    
    if not df_lesionados.empty:
        df_lesionados.columns = [c.strip().lower() for c in df_lesionados.columns]
        col_gravedad = next((c for c in df_lesionados.columns if 'gravedad' in c or 'estado' in c), None)
        
        if col_gravedad:
            activos = df_lesionados[
                df_lesionados[col_gravedad].astype(str).str.lower().str.contains("rojo|amarillo", na=False)
            ]
            lesionados_activos = len(activos)
    
    disponibles = total_plantel - lesionados_activos
    porcentaje_disp = (disponibles / total_plantel) if total_plantel > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Plantel Total", total_plantel)
    col2.metric("Disponibles", disponibles, delta=f"{porcentaje_disp:.0%}")
    col3.metric("Bajas (Lesión)", lesionados_activos, delta=-lesionados_activos, delta_color="inverse")

    st.divider()

    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("⚖️ Balance")
        if 'Tipo' in df_jugadores.columns:
            source = df_jugadores['Tipo'].value_counts().reset_index()
            source.columns = ['Tipo', 'Cantidad']
            
            base = alt.Chart(source).encode(
                theta=alt.Theta("Cantidad", stack=True),
                color=alt.Color("Tipo", legend=alt.Legend(title="Rol")),
                tooltip=["Tipo", "Cantidad"]
            )
            pie = base.mark_arc(outerRadius=100, innerRadius=50)
            text = base.mark_text(radius=120).encode(
                text="Cantidad",
                order=alt.Order("Cantidad"),
                color=alt.value("black")  
            )
            st.altair_chart(pie + text, use_container_width=True)
        else:
            st.info("Falta columna 'Tipo'")

    with c2:
        st.subheader("📈 Asistencia")
        df_asistencia = conector.cargar_datos("DB_Asistencia")
        
        if not df_asistencia.empty:
            try:
                col_fecha = df_asistencia.columns[0]
                df_asistencia[col_fecha] = pd.to_datetime(df_asistencia[col_fecha], dayfirst=True, errors='coerce')
                asistencia_diaria = df_asistencia.groupby(df_asistencia[col_fecha].dt.date)[df_asistencia.columns[1]].nunique()
                
                source_asist = asistencia_diaria.reset_index()
                source_asist.columns = ['Fecha', 'Jugadores']
                
                chart_asist = alt.Chart(source_asist).mark_area(
                    color="#2ecc71",
                    opacity=0.8,
                    line=True
                ).encode(
                    x=alt.X('Fecha:T', axis=alt.Axis(format='%d/%m', title='Fecha')),
                    y=alt.Y('Jugadores:Q'),
                    tooltip=[alt.Tooltip('Fecha', format='%d/%m/%Y'), 'Jugadores']
                )
                
                st.altair_chart(chart_asist, use_container_width=True)
                
            except Exception as e:
                st.caption(f"Error procesando gráfico: {e}")
        else:
            st.info("Sin datos de asistencia.")

# --- MÓDULO PLANTEL (ACTUALIZADO CON SEMÁFOROS) ---
def mostrar_plantel(df):
    st.header("🏉 Plantel Superior")

    # 1. PREPARACIÓN DE DATOS
    if 'Nombre' in df.columns and 'Apellido' in df.columns:
        df['Nombre Completo'] = df['Nombre'] + " " + df['Apellido']
    elif 'Nombre' in df.columns:
        df['Nombre Completo'] = df['Nombre']
    else:
        st.error("Error: No se encuentran columnas de Nombre/Apellido.")
        return

    # --- CÁLCULO DE ASISTENCIA GLOBAL PARA LA LISTA ---
    df_asistencia = conector.cargar_datos("DB_Asistencia")
    mapa_asistencia = {}

    if not df_asistencia.empty:
        try:
            col_fecha = df_asistencia.columns[0]
            # Convertimos fechas
            df_asistencia['fecha_dt'] = pd.to_datetime(df_asistencia[col_fecha], dayfirst=True, errors='coerce').dt.date
            
            # Total de entrenamientos (Denominador)
            total_days = df_asistencia['fecha_dt'].nunique()
            
            if total_days > 0:
                # Contamos asistencias por jugador
                conteos = df_asistencia.groupby(df_asistencia.iloc[:, 1])['fecha_dt'].nunique()
                for jugador, count in conteos.items():
                    pct = (count / total_days) * 100
                    emoji, _ = calcular_estado_asistencia(pct)
                    # Creamos el string visual: "🟢 90%"
                    mapa_asistencia[jugador] = f"{emoji} {pct:.0f}%"
        except Exception as e:
            print(f"Error calculando asistencia lista: {e}")

    # Agregamos la columna visual al dataframe del plantel
    # Si no tiene asistencia, asumimos 0% -> Rojo
    df['Asistencia'] = df['Nombre Completo'].apply(lambda x: mapa_asistencia.get(x, "🔴 0%"))

    # Ordenamos lista de jugadores
    lista_jugadores = sorted(df['Nombre Completo'].unique().tolist())

    # --- 2. SELECTOR ---
    jugador_seleccionado = st.selectbox(
        "🔍 Buscar Jugador para ver Ficha:",
        lista_jugadores,
        index=None,
        placeholder="Escribe o selecciona un nombre..."
    )

    st.divider()

    # --- 3. LÓGICA DE VISTAS ---
    if jugador_seleccionado:
        # === VISTA DE FICHA (DETALLE) ===
        datos_jugador = df[df['Nombre Completo'] == jugador_seleccionado].iloc[0]
        
        st.subheader(f"👤 {jugador_seleccionado}")
        
        # --- NUEVA SECCIÓN: MÉTRICAS DE ASISTENCIA DETALLADA ---
        # Calculamos al momento
        pct_anio, pct_mes, pct_semana = obtener_metricas_jugador(df_asistencia, jugador_seleccionado)
        
        # Mostramos las 3 métricas en fila
        m1, m2, m3 = st.columns(3)
        
        # Helper para pintar el número del metric
        def color_metric(val):
            if val > 85: return "normal" # Streamlit usa verde por defecto en delta positivo, pero aquí usaremos texto
            if val < 65: return "off"
            return "normal"

        m1.metric("Año (Total)", f"{pct_anio:.0f}%", delta_color="normal") 
        m2.metric("Este Mes", f"{pct_mes:.0f}%")
        m3.metric("Esta Semana", f"{pct_semana:.0f}%")
        
        # Barra de progreso visual para el año
        st.progress(pct_anio / 100)
        # Leyenda pequeña
        if pct_anio > 85: st.caption("🟢 Asistencia Impecable")
        elif pct_anio >= 65: st.caption("🟡 Asistencia Regular")
        else: st.caption("🔴 Asistencia Crítica")

        st.divider()
        
        # --- DATOS TÉCNICOS ---
        st.subheader("Ficha Técnica")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Puesto:**")
            puesto_raw = datos_jugador.get('Puesto', '-')
            st.info(traducir_puestos_visual(puesto_raw))
        with c2:
            st.markdown("**Categoría:**")
            st.write(datos_jugador.get('Tipo', '-'))
        with c3:
            st.markdown("**📞 Celular:**")
            celu = datos_jugador.get('Celular personal', '-')
            st.write(str(celu))

        with st.expander("📋 Ver datos personales y contacto de emergencia", expanded=False):
            cols_a_excluir = ['Nombre', 'Apellido', 'Nombre Completo', 'Puesto', 'Tipo', 'Celular personal', 'Asistencia']
            
            for col in df.columns:
                if col not in cols_a_excluir:
                    valor = datos_jugador[col]
                    if pd.notna(valor) and str(valor).strip() != "":
                        titulo = col
                        if col == "Celular emergencia": titulo = "🚨 Celular Emergencia"
                        if col == "Nombre contacto": titulo = "👤 Contacto Emergencia"
                        st.markdown(f"**{titulo}:** {valor}")

        st.markdown("---")
        
        # --- HISTORIAL LESIONES ---
        st.subheader("🏥 Historial de Lesiones")
        df_lesiones = conector.cargar_datos("Lesionados")
        
        if not df_lesiones.empty:
            df_lesiones.columns = [c.strip() for c in df_lesiones.columns]
            col_jugador_lesion = next((c for c in df_lesiones.columns if 'jugador' in c.lower()), None)
            
            if col_jugador_lesion:
                historial = df_lesiones[df_lesiones[col_jugador_lesion].astype(str) == datos_jugador['Nombre']]
                if historial.empty and 'Nombre' in df.columns:
                     historial = df_lesiones[df_lesiones[col_jugador_lesion].astype(str).str.contains(datos_jugador['Nombre'], case=False, na=False)]

                if not historial.empty:
                    st.dataframe(historial, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Sin lesiones registradas.")
            else:
                st.warning("No se puede vincular historial (falta columna 'Jugador' en hoja Lesionados).")
        else:
            st.info("No hay base de lesiones cargada.")

    else:
        # === VISTA DE LISTA (CON SEMÁFOROS) ===
        st.info("👆 Selecciona un jugador arriba para ver su ficha completa.")
        
        # Mostramos Nombre y la nueva columna de Asistencia
        # Configuramos para que se vea bonito
        st.dataframe(
            df[['Nombre Completo', 'Asistencia']], 
            use_container_width=True, 
            hide_index=True,
            height=600
        )

# --- MÓDULO ASISTENCIA ---
def modulo_asistencia(df_jugadores):
    st.header("✅ Control de Asistencia")
    tab1, tab2 = st.tabs(["📲 QR Autogestión", "📝 Carga Manual"])
    
    with tab1:
        st.info("Escanear para dar presente")
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={URL_FORMULARIO_ASISTENCIA}")
        st.markdown(f"[Link directo]({URL_FORMULARIO_ASISTENCIA})")
        
    with tab2:
        lista_nombres = sorted(df_jugadores['Nombre'].unique().tolist()) if 'Nombre' in df_jugadores.columns else []
        
        with st.form("manual"):
            st.write("Selecciona los jugadores presentes (Múltiple):")
            
            jugadores_seleccionados = st.multiselect(
                "Jugadores", 
                lista_nombres, 
                placeholder="Escribe o selecciona múltiples jugadores..."
            )
            
            submit = st.form_submit_button("Marcar Presentes")
            
            if submit:
                if jugadores_seleccionados:
                    progreso = st.progress(0)
                    total = len(jugadores_seleccionados)
                    
                    guardados = 0
                    duplicados = 0
                    
                    for i, jugador in enumerate(jugadores_seleccionados):
                        resultado = conector.guardar_registro("DB_Asistencia", [jugador, "Manual-Coach"])
                        
                        if resultado == True:
                            guardados += 1
                        elif resultado == "DUPLICADO":
                            duplicados += 1
                        
                        progreso.progress((i + 1) / total)
                    
                    if guardados > 0:
                        st.success(f"✅ Se registraron {guardados} nuevos presentes.")
                    if duplicados > 0:
                        st.warning(f"⚠️ Se omitieron {duplicados} jugadores que YA tenían presente hoy.")
                else:
                    st.warning("⚠️ Debes seleccionar al menos un jugador.")

def modulo_medico(df_jugadores):
    st.header("🏥 Departamento Médico")
    tab1, tab2 = st.tabs(["Nueva Lesión", "Ver Lesionados"])
    with tab1:
        lista = sorted(df_jugadores['Nombre'].unique().tolist()) if 'Nombre' in df_jugadores.columns else []
        with st.form("lesion"):
            j = st.selectbox("Jugador", lista)
            d = st.text_input("Diagnóstico")
            g = st.select_slider("Gravedad", options=["Rojo (Out)", "Amarillo (Diferenciado)", "Verde (Alta)"])
            f = st.date_input("Fecha Alta Estimada")
            if st.form_submit_button("Guardar"):
                conector.guardar_registro("Lesionados", [j, d, g, str(f)])
                st.success("Guardado.")
    with tab2:
        df_l = conector.cargar_datos("Lesionados")
        if not df_l.empty: st.dataframe(df_l, use_container_width=True)
        else: st.info("Sin registros.")

# --- MAIN ---
def main():
    menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "Plantel", "Asistencia", "Médico"])
    try:
        df_jugadores = conector.cargar_datos("Jugadores")
        if not df_jugadores.empty:
            df_jugadores.columns = [c.strip().capitalize() for c in df_jugadores.columns]
    except:
        st.error("Error cargando Jugadores.")
        return

    if menu == "📊 Dashboard": mostrar_dashboard(df_jugadores)
    elif menu == "Plantel": mostrar_plantel(df_jugadores)
    elif menu == "Asistencia": modulo_asistencia(df_jugadores)
    elif menu == "Médico": modulo_medico(df_jugadores)

if __name__ == "__main__":
    main()