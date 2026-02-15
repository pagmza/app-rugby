import conector

# Conectamos
print("🔌 Conectando a Google Sheets...")
sh = conector.conectar()
worksheet = sh.worksheet("DB_Asistencia")

# Leemos TODO a lo bruto
print("📖 Leyendo valores crudos...")
datos = worksheet.get_all_values()

total_filas = len(datos)
print(f"📊 TOTAL DE FILAS ENCONTRADAS: {total_filas}")

print("-" * 30)
print("🔍 REVISANDO LA ZONA DEL CRIMEN (Filas 360 a 370):")

# Imprimimos las filas sospechosas para ver qué tienen
inicio = 360
fin = min(total_filas, 375)

for i in range(inicio, fin):
    # i es el índice (empieza en 0), así que la fila Excel es i+1
    contenido = datos[i]
    print(f"Fila {i+1}: {contenido}")

print("-" * 30)