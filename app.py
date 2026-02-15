import streamlit as st
import pandas as pd
import altair as alt 
from datetime import datetime, timedelta
import conector

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Gestión Rugby", layout="centered", page_icon="🏉")
URL_FORMULARIO_ASISTENCIA = "https://docs.google.com/forms/d/e/1FAIpQLSfZF8sRpapNBPzpGxh07vr_W2sv6mPv2yfsmyM5EyG7MKCoJA/viewform"

# --- ESTILOS CSS PERSONALIZADOS (SOLUCIÓN VISUAL) ---
def inyectar_css():
    st.markdown("""
        <style>
        /* --- AJUSTES PARA MÓVILES --- */
        @media (max-width: 768px) {
            /* Forzar que las columnas se mantengan en fila (horizontal) y no se apilen */
            div[data-testid="column"] {
                width: auto !important;
                flex: 1 1 auto !important;
                min-width: 50px !important; /* Mínimo para que no desaparezcan */
                padding: 0 2px !important; /* Reducir espacio entre columnas */
            }
            
            /* Ajustar textos para que quepan en pantalla pequeña */
            div[data-testid="stMetricLabel"] p {
                font-size: 10px !important; /* Título más pequeño (ej: Fowards) */
                white-space: nowrap !important; /* Evitar que se rompa en dos líneas */
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            div[data-testid="stMetricValue"] div {
                font-size: 20px !important; /* Número más compacto */
            }
            div[data-testid="stMetricDelta"] div {
                font-size: 10px !important; /* Delta (flechita) pequeña */
            }
        }

        /* --- ESTILO TIPO TARJETA PARA LAS MÉTRICAS --- */
        div[data-testid="stMetric"] {
            background-color: #1E1E1E; /* Fondo oscuro elegante */
            border: 1px solid #333;    /* Borde sutil */
            border-radius: 8px;        /* Bordes redondeados */
            padding: 10px 5px;         /* Espacio interno */
            text-align: center;        /* Centrar todo */
            box-shadow: 0 2px 4px rgba(0,0,0,0.2); /* Sombra suave */
        }
        
        /* Ocultar el label "normal" de las métricas si ocupa mucho espacio */
        div[data-testid="stMetricLabel"] {
            display: flex;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_datos_asistencia(df):
    if df.empty: return df
    # Identificamos columnas por posición
    col_fecha = df.columns[0]
    col_nombre = df.columns[1]

    # 1. Limpiar Nombres
    df[col_nombre] = df[col_nombre].astype(str).str.strip() 

    # 2. Limpiar Fechas
    df['fecha_dt'] = pd.to_datetime(df[col_fecha], dayfirst=True, format='mixed', errors='coerce').dt.date
    
    # 3. Eliminar filas sin fecha
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
    # INYECTAMOS EL CSS AQUÍ
    inyectar_css()
    
    st.title("📊 Tablero de Comando")
    
    df_asistencia = conector.cargar_datos("DB_Asistencia")
    
    # Mapa de tipos
    mapa_tipos = {}
    if not df_jugadores.empty and 'Nombre' in df_jugadores.columns and 'Tipo' in df_jugadores.columns:
        for index, row in df_jugadores.iterrows():
            nombre_norm = str(row['Nombre']).strip().lower()
            if 'Apellido' in df_jugadores.columns:
                nombre_norm = (str(row['Nombre']).strip() + " " + str(row['Apellido']).strip()).lower()
            mapa_tipos[nombre_norm] = str(row['Tipo']).lower()

    # --- MÉTRICAS GLOBALES (3 Columnas) ---
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

    # Usamos st.columns normal, el CSS se encargará de mantenerlos horizontales en móvil
    c1, c2, c3 = st.columns(3)
    c1.metric("Plantel", total_plantel)
    c2.metric("Disponibles", disponibles, delta=f"{porcentaje_disp:.0%}")
    c3.metric("Bajas", lesionados_activos, delta=-lesionados_activos, delta_color="inverse")
    
    st.divider()

    # --- DETALLE ASISTENCIA POR DÍA ---
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
            
            # --- AJUSTE PARA 4 MÉTRICAS ---
            # En móvil 4 en una fila es muy apretado. El CSS intentará ajustarlo,
            # pero reducimos los textos de los títulos para ayudar.
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total", total_hoy)
            k2.metric("Fwds 🐗", fwds)
            k3.metric("Backs 🏃", backs)
            # Si hay muchos sin ID, se muestra rojo
            delta_id = f"-{sin_id}" if sin_id > 0 else None
            color_id = "inverse" if sin_id > 0 else "off"
            k4.metric("S/Identif.", sin_id, delta=delta_id, delta_color=color_id)
            
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
        
        # Aquí también inyectamos CSS para que estas métricas se vean bien
        inyectar_css()
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

# --- MAIN ---
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