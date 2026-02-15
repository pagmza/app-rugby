import pandas as pd
import gspread
import streamlit as st
import os

def conectar():
    """
    Establece la conexión con Google Sheets.
    Prioriza el archivo local 'credentials.json' para evitar errores en tu PC.
    """
    try:
        # 1. MODO LOCAL: ¿Tienes el archivo 'credentials.json' en la carpeta?
        if os.path.exists("credentials.json"):
            gc = gspread.service_account(filename="credentials.json")
            
        # 2. MODO NUBE: Si no hay archivo local, buscamos en los Secrets de Streamlit
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # Corrección para la clave privada
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            gc = gspread.service_account_from_dict(creds_dict)
            
        else:
            st.error("🚨 Error Crítico: No se encontraron credenciales (ni archivo local ni secrets).")
            return None

        # --- ABRIMOS EL ARCHIVO POR SU NOMBRE EXACTO ---
        sh = gc.open("Gestion_Plantel_Rugby")
        return sh

    except Exception as e:
        st.error(f"Error de Conexión: No se pudo abrir la hoja de cálculo. Detalle: {e}")
        return None

def cargar_datos(nombre_hoja):
    """
    Descarga los datos de una pestaña específica.
    """
    sh = conectar()
    
    if sh is None:
        return pd.DataFrame()

    try:
        worksheet = sh.worksheet(nombre_hoja)
        datos_crudos = worksheet.get_all_values()
        
        if not datos_crudos:
            return pd.DataFrame()

        encabezados = datos_crudos.pop(0)
        df = pd.DataFrame(datos_crudos, columns=encabezados)
        df.columns = [str(c).strip() for c in df.columns]
        
        return df

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: No existe la pestaña llamada '{nombre_hoja}' en 'Gestion_Plantel_Rugby'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error leyendo la hoja '{nombre_hoja}': {e}")
        return pd.DataFrame()

def guardar_registro(nombre_hoja, datos_nuevos):
    """
    Agrega una fila nueva al final de la hoja especificada.
    """
    sh = conectar()
    
    if sh is None:
        return False

    try:
        worksheet = sh.worksheet(nombre_hoja)
        worksheet.append_row(datos_nuevos)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        return False