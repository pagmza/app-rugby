import pandas as pd
import gspread
import streamlit as st
from datetime import datetime

def conectar():
    """Conexión híbrida: Intenta usar Secretos de Nube, si falla, busca archivo local."""
    try:
        # 1. Intento Nube (Streamlit Cloud)
        # Busca las credenciales dentro de la configuración segura del servidor
        dict_credenciales = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(dict_credenciales)
    except:
        # 2. Intento Local (Tu computadora)
        # Si falla lo anterior, busca el archivo json clásico
        gc = gspread.service_account(filename='credentials.json')
        
    sh = gc.open("Gestion_Plantel_Rugby")
    return sh

def cargar_datos(nombre_hoja="Jugadores"):
    sh = conectar()
    try:
        worksheet = sh.worksheet(nombre_hoja)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()

def guardar_registro(nombre_hoja, lista_datos):
    sh = conectar()
    try:
        worksheet = sh.worksheet(nombre_hoja)
        
        # --- LÓGICA ANTI-DUPLICADOS (Solo para DB_Asistencia) ---
        if nombre_hoja == "DB_Asistencia":
            jugador_a_guardar = lista_datos[0]
            registros = worksheet.get_all_values()
            
            if len(registros) > 1:
                df_temp = pd.DataFrame(registros[1:], columns=registros[0])
                col_fecha = df_temp.columns[0]
                col_jugador = df_temp.columns[1]
                
                # Conversión de fecha robusta
                df_temp['fecha_dt'] = pd.to_datetime(df_temp[col_fecha], dayfirst=True, errors='coerce').dt.date
                fecha_hoy = datetime.now().date()
                
                duplicado = df_temp[
                    (df_temp[col_jugador] == jugador_a_guardar) & 
                    (df_temp['fecha_dt'] == fecha_hoy)
                ]
                
                if not duplicado.empty:
                    return "DUPLICADO" 

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        fila_a_guardar = [ahora] + lista_datos
        worksheet.append_row(fila_a_guardar)
        return True

    except Exception as e:
        print(f"Error al guardar: {e}")
        return False