import streamlit as st
import pandas as pd
import altair as alt 
from datetime import datetime, timedelta
import conector

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Gestión Rugby", layout="centered", page_icon="🏉")
URL_FORMULARIO_ASISTENCIA = "https://docs.google.com/forms/d/e/1FAIpQLSfZF8sRpapNBPzpGxh07vr_W2sv6mPv2yfsmyM5EyG7MKCoJA/viewform"

# --- FUNCIÓN NUEVA: TARJETAS HTML FLEXIBLES (LA SOLUCIÓN) ---
def renderizar_tarjetas_flex(total, fwds, backs, sin_id):
    """
    Genera tarjetas HTML que realmente se ajustan al contenido y bajan de línea.
    """
    
    # Color para "Sin Identificar" (Rojo si hay errores, Gris si no)
    color_sin_id = "#ff4b4b" if sin_id > 0 else "#262730"
    borde_sin_id = "#ff4b4b" if sin_id > 0 else "#464b59"

    # HTML y CSS inyectado directamente
    html = f"""
    <style>
        .flex-container {{
            display: flex;
            flex-wrap: wrap;       /* ESTO HACE LA MAGIA: Baja de línea si no cabe */
            gap: 8px;              /* Espacio entre tarjetas */
            justify-content: center; /* Centrar tarjetas */
            margin-bottom: 20px;
        }}
        .flex-card {{
            background-color: #262730;
            border: 1px solid #464b59;
            border-radius: 8px;
            padding: 8px 12px;     /* Relleno ajustado */
            text-align: center;
            flex: 0 1 auto;        /* Ancho automático según contenido */
            min-width: 60px;       /* Ancho mínimo para no romperse */
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .flex-card h3 {{
            margin: 0;
            font-size: 12px;
            color: #fafafa;
            font-weight: normal;
            white-space: nowrap;   /* Título en una sola línea */
        }}
        .flex-card p {{
            margin: 0;
            font-size: 20px;
            font-weight: bold;
            color: white;
        }}
        /* Estilo especial para alertas */
        .card-alert {{
            background-color: {color_sin_id}; 
            border: 1px solid {borde_sin_id};
        }}
    </style>

    <div class="flex-container">
        <div class="flex-card">
            <h3>Total</h3>
            <p>{total}</p>
        </div>
        
        <div class="flex-card">
            <h3>Fwds 🐗</h3>
            <p>{fwds}</p>
        </div>

        <div class="flex-card">
            <h3>Backs 🏃</h3>
            <p>{backs}</p>
        </div>

        <div class="flex-card {'card-alert' if sin_id > 0 else ''}">
            <h3>S/Identif.</h3>
            <p>{sin_id}</p>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_datos_asistencia(df):
    if df.empty: return df
    col_fecha = df.columns[0]
    col_nombre = df.columns[1]
    df[col_nombre] = df[col_nombre].astype(str).str.strip() 
    df['fecha_dt'] = pd.to_datetime(df[col_fecha], dayfirst=True, format='mixed', errors='coerce').dt.date
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
    
    df_asistencia = conector.cargar_datos("DB_Asistencia")
    
    mapa_tipos = {}
    if not df_jugadores.empty and 'Nombre' in df_jugadores.columns and 'Tipo' in df_jugadores.columns:
        for index, row in df_jugadores.iterrows():
            nombre_norm = str(row['Nombre']).strip().lower()
            if 'Apellido' in df_jugadores.columns:
                nombre_norm = (str(row['Nombre']).strip() + " " + str(row['Apellido']).strip()).lower()
            mapa_tipos[nombre_norm] = str(row['Tipo']).lower()

    # --- MÉTRICAS GLOBALES (Arriba) ---
    # Estas las dejamos con st.metric normal porque se ven bien en 3 columnas
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
    c1.metric("Plantel", total_plantel)
    c2.metric("Disponibles", disponibles, delta=f"{porcentaje_disp:.0%}")
    c3.metric("Bajas", lesionados_activos, delta=-lesionados_activos, delta_color="inverse")
    
    st.divider()

    # --- ASISTENCIA POR DÍA (AQUÍ USAMOS LA NUEVA FUNCIÓN) ---
    st.subheader("📅 Asistencia por Día")
    
    if not df_asistencia.empty:
        df_asistencia = limpiar_datos_asistencia(df_asistencia)
        fechas_unicas = sorted(df_asistencia['fecha_dt'].unique(), reverse=True)
        fecha_selecc = st.selectbox("Selecciona Fecha:", fechas_unicas)
        
        if fecha_selecc:
            asistentes_hoy = df_asistencia[df_asistencia['fecha_dt'] == fecha_selecc]
            lista_nombres_hoy = sorted(asistentes_hoy.iloc[:, 1].unique())
            
            total_hoy = len(lista_nombres_hoy)
            fwds = 0
            backs = 0
            sin_id = 0
            for jugador in lista_nombres_hoy:
                nombre_limpio = str(jugador).strip().lower()
                tipo = mapa_tipos.get(nombre_limpio, "desconocido")
                if "forward" in tipo or "foward" in tipo or "fwd" in tipo or "pilar" in tipo or "segunda" in tipo or "ala" in tipo or "octavo" in tipo or "hooker" in tipo:
                    fwds += 1
                elif "back" in tipo or "3/4" in tipo or "medio" in tipo or "apertura" in tipo or "centro" in tipo or "wing" in tipo or "fullback" in tipo:
                    backs += 1
                else:
                    sin_id += 1
            
            # --- REEMPLAZO DE ST.COLUMNS POR NUESTRO HTML FLEXIBLE ---
            renderizar_tarjetas_flex(total_hoy, fwds, backs, sin_id)
            # ---------------------------------------------------------
            
            st.write("---")
            with st.expander(f"📜 Ver lista ({total_hoy})", expanded=False):
                df_lista = pd.DataFrame(lista_nombres_hoy, columns=["Nombre del Jugador"])
                st.dataframe(df_lista, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros.")

    st.divider()

    # --- GRÁFICOS ---
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("⚖️ Roles")
        if 'Tipo' in df_jugadores.columns:
            source = df_jugadores['Tipo'].value_counts().reset_index()
            source.columns = ['Tipo', 'Cantidad']
            base = alt.Chart(source).encode(theta=alt.Theta("Cantidad", stack=True), color="Tipo")
            pie = base.mark_arc(outerRadius=80) + base.mark_text(radius=100).encode(text="Cantidad", color=alt.value("black"))
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

def main():
    menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "Plantel", "Asistencia", "Médico"])
    df = conector.cargar_datos("Jugadores")
    if df.empty:
        st.error("No se pudo cargar la lista de jugadores.")
        return
    df.columns = [c.strip().capitalize() for c in df.columns]
    if menu == "📊 Dashboard": mostrar_dashboard(df)
    elif menu == "Plantel": mostrar_plantel(df)
    elif menu == "Asistencia": modulo_asistencia(df)
    elif menu == "Médico": modulo_medico(df)

if __name__ == "__main__":
    main()