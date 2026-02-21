import streamlit as st
import pandas as pd
import altair as alt 
from datetime import datetime, timedelta
import conector

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Gestión Rugby", layout="centered", page_icon="🏉")
URL_FORMULARIO_ASISTENCIA = "https://docs.google.com/forms/d/e/1FAIpQLSfZF8sRpapNBPzpGxh07vr_W2sv6mPv2yfsmyM5EyG7MKCoJA/viewform"

# --- 1. FUNCIÓN DE UNIFICACIÓN ---
def cargar_asistencia_unificada():
    df_manual = conector.cargar_datos("DB_Asistencia")
    df_qr = conector.cargar_datos("Respuestas de formulario 3")
    
    dfs_a_unir = []

    if not df_manual.empty:
        temp = df_manual.iloc[:, 0:2].copy()
        temp.columns = ["fecha", "nombre"]
        dfs_a_unir.append(temp)

    if not df_qr.empty:
        temp = df_qr.iloc[:, 0:2].copy()
        temp.columns = ["fecha", "nombre"]
        dfs_a_unir.append(temp)

    if not dfs_a_unir:
        return pd.DataFrame(columns=["fecha", "nombre"])

    df_total = pd.concat(dfs_a_unir, ignore_index=True)
    return df_total

# --- 2. FUNCIÓN DE VISUALIZACIÓN (TARJETAS) ---
def renderizar_tarjetas(metricas):
    estilo = """
<style>
.flex-wrapper {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    width: 100%;
    margin-bottom: 20px;
}
.custom-card {
    background-color: #262730;
    border: 1px solid #464b59;
    border-radius: 8px;
    padding: 10px 5px;
    text-align: center;
    flex: 1 1 85px;
    min-width: 85px;
    max-width: 150px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.card-label {
    font-size: 11px;
    color: #b0b0b0;
    margin-bottom: 2px;
    font-weight: 600;
    text-transform: uppercase;
}
.card-value {
    font-size: 20px;
    font-weight: bold;
    color: #ffffff;
    margin: 0;
    line-height: 1.2;
}
.card-delta {
    font-size: 10px;
    margin-top: 2px;
}
.delta-pos { color: #00cc66; }
.delta-neg { color: #ff4b4b; }
.delta-neu { color: #888; }
.border-alert { border-color: #ff4b4b !important; }
.text-alert { color: #ff4b4b !important; }
</style>
"""
    cards_html = ""
    for m in metricas:
        clase_borde = "border-alert" if m.get('alert') else ""
        clase_texto = "text-alert" if m.get('alert') else ""
        valor = m['value']
        label = m['label']
        
        delta_html = ""
        if 'delta' in m and m['delta'] != 0:
            d_val = m['delta']
            color = "delta-pos" if d_val > 0 else "delta-neg"
            simbolo = "▲" if d_val > 0 else "▼"
            delta_html = f'<div class="card-delta {color}">{simbolo} {abs(d_val)}</div>'
        elif 'subtext' in m:
             delta_html = f'<div class="card-delta delta-neu">{m["subtext"]}</div>'
             
        cards_html += f'<div class="custom-card {clase_borde}"><div class="card-label">{label}</div><div class="card-value {clase_texto}">{valor}</div>{delta_html}</div>'

    st.markdown(f"{estilo}<div class='flex-wrapper'>{cards_html}</div>", unsafe_allow_html=True)

# --- 3. FUNCIONES AUXILIARES (AQUÍ ESTÁ LA NUEVA MAGIA) ---
def limpiar_datos_asistencia(df):
    if df.empty: return df
    
    # 1. Aseguramos que la columna nombre sea texto puro
    df['nombre'] = df['nombre'].astype(str)
    
    # 2. Función súper estricta para separar las celdas agrupadas
    def extraer_nombres(texto):
        # Si está vacío o es un error de pandas, devolver lista vacía
        if texto.lower() in ['nan', 'none', '']: 
            return []
        
        # Separar por comas (formato Formulario de Google) y limpiar espacios
        # Ej: "Juan , Diego" -> ["Juan", "Diego"]
        lista_nombres = [nombre.strip() for nombre in texto.split(',') if nombre.strip()]
        return lista_nombres

    # 3. Aplicamos la función (ahora cada celda es una lista real de Python)
    df['nombre'] = df['nombre'].apply(extraer_nombres)
    
    # 4. EXPLODE: Esta es la instrucción que clona las filas. 
    # 1 fila con 3 nombres -> 3 filas con 1 nombre cada una.
    df = df.explode('nombre').reset_index(drop=True)
    
    # 5. Limpiamos las fechas normalmente
    df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, format='mixed', errors='coerce').dt.date
    
    # 6. Borramos filas que hayan quedado sin fecha o sin nombre tras la explosión
    df = df.dropna(subset=['fecha_dt', 'nombre'])
    
    return df

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
    
    col_nombre = "nombre"
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
    
    df_asistencia = cargar_asistencia_unificada()
    
    mapa_tipos = {}
    if not df_jugadores.empty:
        for index, row in df_jugadores.iterrows():
            if 'Nombre' in df_jugadores.columns and 'Tipo' in df_jugadores.columns:
                n = str(row['Nombre']).strip()
                if 'Apellido' in df_jugadores.columns:
                    n += " " + str(row['Apellido']).strip()
                mapa_tipos[n.lower()] = str(row['Tipo']).lower()

    total_plantel = len(df_jugadores)
    df_lesionados = conector.cargar_datos("Lesionados")
    lesionados_activos = 0
    if not df_lesionados.empty:
        df_lesionados.columns = [str(c).strip().lower() for c in df_lesionados.columns]
        col_gravedad = next((c for c in df_lesionados.columns if 'gravedad' in c or 'estado' in c), None)
        if col_gravedad:
            activos = df_lesionados[df_lesionados[col_gravedad].astype(str).str.lower().str.contains("rojo|amarillo", na=False)]
            lesionados_activos = len(activos)
            
    disponibles = total_plantel - lesionados_activos
    pct_disp = (disponibles / total_plantel * 100) if total_plantel > 0 else 0

    renderizar_tarjetas([
        {'label': 'Plantel', 'value': total_plantel},
        {'label': 'Disponibles', 'value': disponibles, 'subtext': f"{pct_disp:.0f}% Ok"},
        {'label': 'Lesionados', 'value': lesionados_activos, 'alert': lesionados_activos > 0}
    ])
    
    st.divider()
    st.subheader("📅 Asistencia por Día")
    
    if not df_asistencia.empty:
        df_asistencia = limpiar_datos_asistencia(df_asistencia)
        
        fechas_unicas = sorted(df_asistencia['fecha_dt'].unique(), reverse=True)
        fecha_selecc = st.selectbox("Selecciona Fecha:", fechas_unicas)
        
        if fecha_selecc:
            asistentes = df_asistencia[df_asistencia['fecha_dt'] == fecha_selecc]
            lista_presentes = sorted(asistentes['nombre'].unique())
            
            total = len(lista_presentes)
            fwds = 0
            backs = 0
            sin_id = 0
            
            for p in lista_presentes:
                tipo = mapa_tipos.get(str(p).strip().lower(), "desconocido")
                if any(x in tipo for x in ["forward", "foward", "fwd", "pilar", "hooker", "segunda", "ala", "octavo"]):
                    fwds += 1
                elif any(x in tipo for x in ["back", "3/4", "medio", "apertura", "centro", "wing", "fullback"]):
                    backs += 1
                else:
                    sin_id += 1
            
            datos_dia = [
                {'label': 'Total', 'value': total},
                {'label': 'Fwds 🐗', 'value': fwds},
                {'label': 'Backs 🏃', 'value': backs}
            ]
            if sin_id > 0:
                datos_dia.append({'label': 'S/Identif.', 'value': sin_id, 'alert': True})
            else:
                datos_dia.append({'label': 'Identif.', 'value': '100%', 'subtext': 'Ok'})
                
            renderizar_tarjetas(datos_dia)
            
            st.write("---")
            with st.expander(f"📜 Ver lista ({total})"):
                st.dataframe(pd.DataFrame(lista_presentes, columns=["Nombre"]), use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de asistencia cargados.")

    st.divider()
    
    col1, col2 = st.columns(2)
    with col2:
        st.subheader("📈 Evolución")
        if not df_asistencia.empty:
            diaria = df_asistencia.groupby('fecha_dt')['nombre'].nunique().reset_index()
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

    df_asistencia = cargar_asistencia_unificada()
    mapa_asistencia = {}
    
    if not df_asistencia.empty:
        df_asistencia = limpiar_datos_asistencia(df_asistencia)
        total_days = df_asistencia['fecha_dt'].nunique()
        
        if total_days > 0:
            conteos = df_asistencia.groupby('nombre')['fecha_dt'].nunique()
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
        
        renderizar_tarjetas([
            {'label': 'Año', 'value': f"{p_anio:.0f}%"},
            {'label': 'Mes', 'value': f"{p_mes:.0f}%"},
            {'label': 'Semana', 'value': f"{p_sem:.0f}%"}
        ])
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
                st.success("Guardado. (Se unirá automáticamente con los QR)")

def modulo_medico(df):
    st.header("🏥 Médico")
    df_l = conector.cargar_datos("Lesionados")
    st.dataframe(df_l, use_container_width=True)

def main():
    menu = st.sidebar.radio("Ir a:", ["📊 Dashboard", "Plantel", "Asistencia", "Médico"])
    df_jugadores = conector.cargar_datos("Jugadores")
    
    if df_jugadores.empty:
        st.error("Error: No se pudo cargar la lista de Jugadores.")
        return
        
    df_jugadores.columns = [c.strip().capitalize() for c in df_jugadores.columns]
    
    if menu == "📊 Dashboard": mostrar_dashboard(df_jugadores)
    elif menu == "Plantel": mostrar_plantel(df_jugadores)
    elif menu == "Asistencia": modulo_asistencia(df_jugadores)
    elif menu == "Médico": modulo_medico(df_jugadores)

if __name__ == "__main__":
    main()