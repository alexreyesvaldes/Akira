from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import pandas as pd
import csv
import sys

# CONFIGURAR LA BASE DE DATOS
DATABASE_URL = "sqlite:///tienda_online.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()  # Base para las tablas
Session = sessionmaker(bind=engine)
session = Session()

# Definición de la tabla
class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)

Base.metadata.create_all(engine)

# Funciones del sistema
def agregar_producto(nombre, precio, stock):
    nuevo_producto = Producto(nombre=nombre, precio=precio, stock=stock)
    session.add(nuevo_producto)
    session.commit()
    print(f"Producto '{nombre}' agregado con éxito.")

def listar_productos():
    productos = session.query(Producto).all()
    if not productos:
        print("No hay productos en la base de datos.")
        return
    for producto in productos:
        print(f"ID: {producto.id}, Nombre: {producto.nombre}, Precio: {producto.precio}, Stock: {producto.stock}")

def editar_producto(producto_id, nombre=None, precio=None, stock=None):
    producto = session.get(Producto, producto_id)
    if not producto:
        print("Producto no encontrado.")
        return
    if nombre:
        producto.nombre = nombre
    if precio:
        producto.precio = precio
    if stock:
        producto.stock = stock
    session.commit()
    print(f"Producto con ID {producto_id} actualizado con éxito.")

def eliminar_producto(producto_id):
    producto = session.get(Producto, producto_id)
    if not producto:
        print("Producto no encontrado.")
        return
    session.delete(producto)
    session.commit()
    print(f"Producto con ID {producto_id} eliminado con éxito.")

def exportar_a_csv(nombre_archivo="productos.csv"):
    productos = session.query(Producto).all()
    if not productos:
        print("No hay productos para exportar.")
        return

    with open(nombre_archivo, mode="w", newline="", encoding="utf-8") as archivo_csv:
        escritor = csv.writer(archivo_csv)
        escritor.writerow(["ID", "Nombre", "Precio", "Stock"])
        for producto in productos:
            escritor.writerow([producto.id, producto.nombre, producto.precio, producto.stock])
    print(f"Productos exportados a {nombre_archivo} con éxito.")

def exportar_a_excel(nombre_archivo="productos.xlsx"):
    productos = session.query(Producto).all()
    if not productos:
        print("No hay productos en la base de datos.")
        return

    datos = [{"ID": p.id, "Nombre": p.nombre, "Precio": p.precio, "Stock": p.stock} for p in productos]
    df = pd.DataFrame(datos)
    df.to_excel(nombre_archivo, index=False)
    print(f"Productos exportados a {nombre_archivo} con éxito.")

def importar_productos_desde_csv(nombre_archivo):
    try:
        with open(nombre_archivo, mode="r", encoding="utf-8") as archivo_csv:
            lector = csv.DictReader(archivo_csv)
            for fila in lector:
                agregar_producto(fila["Nombre"], float(fila["Precio"]), int(fila["Stock"]))
        print("Productos importados con éxito.")
    except Exception as e:
        print(f"Error al importar productos: {e}")

def buscar_producto(nombre=None, rango_precio=None):
    query = session.query(Producto)
    if nombre:
        query = query.filter(Producto.nombre.contains(nombre))
    if rango_precio:
        min_precio, max_precio = rango_precio
        query = query.filter(Producto.precio.between(min_precio, max_precio))
    resultados = query.all()
    if not resultados:
        print("No se encontraron productos.")
        return
    for producto in resultados:
        print(f"ID: {producto.id}, Nombre: {producto.nombre}, Precio: {producto.precio}, Stock: {producto.stock}")

def alerta_inventario(limite):
    productos = session.query(Producto).filter(Producto.stock < limite).all()
    if not productos:
        print("No hay productos con inventario bajo.")
        return
    for producto in productos:
        print(f"ID: {producto.id}, Nombre: {producto.nombre}, Stock: {producto.stock}")

def generar_reporte():
    productos = session.query(Producto).all()
    total_stock = sum(producto.stock for producto in productos)
    total_valor = sum(producto.precio * producto.stock for producto in productos)
    print("\n--- Reporte de Inventario ---")
    print(f"Total de productos: {len(productos)}")
    print(f"Cantidad total en stock: {total_stock}")
    print(f"Valor total del inventario: ${total_valor:.2f}")

# NUEVA FUNCIÓN PARA PRUEBA DE CONEXIÓN
def prueba_conexion():
    print("Conexión exitosa entre VBA y Python.")

# Definición del menú interactivo
def menu():
    while True:
        print("\n--- Menú de Productos ---")
        print("1. Agregar producto")
        print("2. Listar productos")
        print("3. Editar producto")
        print("4. Eliminar producto")
        print("5. Exportar a CSV")
        print("6. Exportar a Excel")
        print("7. Importar desde CSV")
        print("8. Buscar productos")
        print("9. Alerta de inventario bajo")
        print("10. Generar reporte")
        print("11. Salir")

        opcion = input("Elige una opción: ")

        if opcion == "1":
            nombre = input("Nombre del producto: ")
            precio = float(input("Precio del producto: "))
            stock = int(input("Stock del producto: "))
            agregar_producto(nombre, precio, stock)
        elif opcion == "2":
            listar_productos()
        elif opcion == "3":
            producto_id = int(input("ID del producto a editar: "))
            nombre = input("Nuevo nombre (dejar vacío para no cambiar): ") or None
            precio = input("Nuevo precio (dejar vacío para no cambiar): ")
            precio = float(precio) if precio else None
            stock = input("Nuevo stock (dejar vacío para no cambiar): ")
            stock = int(stock) if stock else None
            editar_producto(producto_id, nombre, precio, stock)
        elif opcion == "4":
            producto_id = int(input("ID del producto a eliminar: "))
            eliminar_producto(producto_id)
        elif opcion == "5":
            exportar_a_csv()
        elif opcion == "6":
            exportar_a_excel()
        elif opcion == "7":
            archivo = input("Nombre del archivo CSV a importar: ")
            importar_productos_desde_csv(archivo)
        elif opcion == "8":
            nombre = input("Buscar por nombre (dejar vacío para omitir): ") or None
            rango = input("Rango de precio (ejemplo: 10-100, dejar vacío para omitir): ")
            rango_precio = tuple(map(float, rango.split("-"))) if rango else None
            buscar_producto(nombre, rango_precio)
        elif opcion == "9":
            limite = int(input("Límite para alerta de inventario bajo: "))
            alerta_inventario(limite)
        elif opcion == "10":
            generar_reporte()
        elif opcion == "11":
            print("Saliendo del programa...")
            break
        else:
            print("Opción inválida, intenta de nuevo.")

# Manejador principal
if __name__ == "__main__":
    if len(sys.argv) < 2:
        menu()
    else:
        comando = sys.argv[1]

        if comando == "prueba":
            prueba_conexion()
        elif comando == "agregar":
            agregar_producto(sys.argv[2], float(sys.argv[3]), int(sys.argv[4]))
        elif comando == "listar":
            listar_productos()
        elif comando == "editar":
            editar_producto(int(sys.argv[2]), sys.argv[3], float(sys.argv[4]), int(sys.argv[5]))
        elif comando == "eliminar":
            eliminar_producto(int(sys.argv[2]))
        elif comando == "exportar_csv":
            exportar_a_csv()
        elif comando == "exportar_excel":
            exportar_a_excel()
        elif comando == "importar_csv":
            importar_productos_desde_csv(sys.argv[2])
        elif comando == "menu":
            menu()
        else:
            print("Comando no reconocido.")
