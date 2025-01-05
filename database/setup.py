import sqlite3

# Conexión a la base de datos
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Crear la tabla de usuarios
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Confirmar los cambios y cerrar la conexión
conn.commit()
conn.close()

print("Base de datos creada con éxito.")
