from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import requests
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de Shopify
SHOP_NAME = "dgcpih-00"
ACCESS_TOKEN = "SHOPIFY_TOKEN"
HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN,
}

USERS = {
    "admin": {"password": generate_password_hash("Sanandres10_10**h"), "role": "admin"},
    "user": {"password": generate_password_hash("123456"), "role": "user"}
}

FAILED_ATTEMPTS = {}

# Obtener location_id
def get_location_id():
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/locations.json"
    response = requests.get(url, headers=HEADERS)
    locations = response.json().get("locations", [])
    if locations:
        return locations[0]["id"]
    return None

LOCATION_ID = get_location_id()

# Función para registrar actividad
def log_activity(action, username=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("activity_log.txt", "a") as f:
        f.write(f"[{timestamp}] {username or 'System'}: {action}\n")

# Decorador para roles
def requires_role(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user" not in session or session.get("role") != role:
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in FAILED_ATTEMPTS and FAILED_ATTEMPTS[username]["count"] >= 3:
            last_attempt = FAILED_ATTEMPTS[username]["last_attempt"]
            elapsed_time = (datetime.now() - last_attempt).seconds
            if elapsed_time < 300:
                return render_template("login.html", error="Cuenta bloqueada temporalmente. Inténtalo en 5 minutos.")
            else:
                FAILED_ATTEMPTS.pop(username)

        if username in USERS and check_password_hash(USERS[username]["password"], password):
            session["user"] = username
            session["role"] = USERS[username]["role"]
            log_activity("Inicio de sesión exitoso", username)
            return redirect(url_for("index"))
        else:
            if username not in FAILED_ATTEMPTS:
                FAILED_ATTEMPTS[username] = {"count": 0, "last_attempt": datetime.now()}
            FAILED_ATTEMPTS[username]["count"] += 1
            FAILED_ATTEMPTS[username]["last_attempt"] = datetime.now()
            log_activity("Intento fallido de inicio de sesión", username)
            return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html")

@app.route("/logout")
def logout():
    user = session.pop("user", None)
    session.pop("role", None)
    if user:
        log_activity("Cierre de sesión", user)
    return redirect(url_for("login"))

@app.route("/")
@requires_role("admin")
def index():
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json"
    response = requests.get(url, headers=HEADERS)
    products = response.json().get("products", [])

    inventory_levels = {}
    for product in products:
        for variant in product.get("variants", []):
            inventory_item_id = variant.get("inventory_item_id")
            if inventory_item_id:
                inventory_url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/inventory_levels.json?inventory_item_ids={inventory_item_id}"
                inventory_response = requests.get(inventory_url, headers=HEADERS)
                inventory_data = inventory_response.json().get("inventory_levels", [])
                if inventory_data:
                    inventory_levels[variant["id"]] = inventory_data[0].get("available", 0)

    for product in products:
        for variant in product.get("variants", []):
            variant["available"] = inventory_levels.get(variant["id"], 0)

    return render_template("index.html", products=products)

@app.route("/create_product", methods=["POST"])
@requires_role("admin")
def create_product():
    try:
        data = request.json

        # Validar datos
        if not data.get("title") or not data.get("sku") or not data.get("price") or not data.get("inventory_quantity"):
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        # Validar precios y cantidades
        if float(data["price"]) <= 0 or int(data["inventory_quantity"]) < 0:
            return jsonify({"error": "Precio debe ser mayor a 0 y cantidad no negativa"}), 400

        # Preparar payload
        url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json"
        payload = {
            "product": {
                "title": data["title"],
                "body_html": data["description"],
                "variants": [
                    {
                        "price": data["price"],
                        "sku": data["sku"],
                        "inventory_management": "shopify"
                    }
                ]
            }
        }

        # Enviar solicitud a Shopify
        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 201:
            return jsonify({"message": "Producto creado exitosamente"}), 201
        else:
            return jsonify({"error": response.status_code, "message": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    response = requests.post(url, headers=HEADERS, json=payload)

    if response.status_code == 201:
        product = response.json().get("product", {})
        variant = product.get("variants", [{}])[0]
        inventory_item_id = variant.get("inventory_item_id")

        if inventory_item_id and "inventory_quantity" in data:
            inventory_url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/inventory_levels/set.json"
            inventory_payload = {
                "location_id": LOCATION_ID,
                "inventory_item_id": inventory_item_id,
                "available": data["inventory_quantity"]
            }
            inventory_response = requests.post(inventory_url, headers=HEADERS, json=inventory_payload)
            if inventory_response.status_code != 200:
                log_activity("Error al actualizar inventario", session["user"])
                return jsonify({"error": "Error al actualizar inventario", "details": inventory_response.json()}), 500

        log_activity("Producto creado con éxito", session["user"])
        return jsonify({"message": "Producto creado con éxito"})
    else:
        return jsonify({"error": response.status_code, "message": response.text})

@app.route("/export_excel")
@requires_role("admin")
def export_excel():
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json"
    response = requests.get(url, headers=HEADERS)
    products = response.json().get("products", [])

    data = []
    for product in products:
        data.append({
            "ID": product["id"],
            "Título": product["title"],
            "Precio": product["variants"][0]["price"],
            "SKU": product["variants"][0]["sku"],
            "Existencia": product["variants"][0].get("available", "N/A")
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Productos")
    output.seek(0)

    log_activity("Reporte exportado", session["user"])
    return send_file(output, as_attachment=True, download_name="productos.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Ruta para subir el archivo Excel
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'message': 'No se encontró ningún archivo'}), 400

    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'message': 'El archivo debe ser un Excel (.xlsx)'}), 400

    try:
        # Leer el archivo Excel con pandas
        df = pd.read_excel(file)

        # Validar que tenga las columnas necesarias
        required_columns = {'title', 'description', 'price', 'sku', 'inventory_quantity'}
        if not required_columns.issubset(df.columns):
            return jsonify({'message': 'El archivo debe contener las columnas: title, description, price, sku, inventory_quantity'}), 400

        # Crear productos en Shopify (lógica adicional)
        created_products = []
        for _, row in df.iterrows():
            product_payload = {
                "product": {
                    "title": row['title'],
                    "body_html": row['description'],
                    "variants": [
                        {
                            "price": row['price'],
                            "sku": row['sku'],
                            "inventory_management": "shopify"
                        }
                    ]
                }
            }
            response = requests.post(
                f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json",
                headers=HEADERS,
                json=product_payload
            )
            if response.status_code == 201:
                created_products.append(row['title'])
            else:
                return jsonify({'message': f"Error al crear el producto: {row['title']}", 'details': response.text}), 500

        return jsonify({'message': f"Productos creados exitosamente: {', '.join(created_products)}"}), 200

    except Exception as e:
        return jsonify({'message': f"Error al procesar el archivo: {str(e)}"}), 500
    

@app.route('/sync_inventory', methods=['GET'])
@requires_role('admin')  # Solo accesible para admins
def sync_inventory():
    try:
        # Consultar productos desde Shopify
        url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json"
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            return jsonify({'error': 'No se pudo obtener los productos de Shopify'}), response.status_code

        products = response.json().get('products', [])

        # Crear lista para almacenar inventarios
        inventory_data = []
        low_inventory_alerts = []

        for product in products:
            for variant in product.get("variants", []):
                inventory_item_id = variant.get("inventory_item_id")
                
                # Consultar niveles de inventario para cada variante
                inventory_url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/inventory_levels.json?inventory_item_ids={inventory_item_id}"
                inventory_response = requests.get(inventory_url, headers=HEADERS)
                
                if inventory_response.status_code == 200:
                    inventory_level = inventory_response.json().get("inventory_levels", [{}])[0].get("available", 0)
                    inventory_data.append({
                        "Product ID": product["id"],
                        "Title": product["title"],
                        "Variant ID": variant["id"],
                        "SKU": variant["sku"],
                        "Inventory": inventory_level
                    })

                    # Detectar inventarios bajos (menores a 10 unidades)
                    if inventory_level < 10:
                        low_inventory_alerts.append({
                            "title": product["title"],
                            "sku": variant["sku"],
                            "inventory": inventory_level
                        })

        # Guardar datos en un archivo Excel
        df = pd.DataFrame(inventory_data)
        output_file = 'inventory_report.xlsx'
        df.to_excel(output_file, index=False)

        # Enviar alertas si hay inventarios bajos
        if low_inventory_alerts:
            alert_message = "ALERTA: Productos con inventario bajo:\n\n"
            for alert in low_inventory_alerts:
                alert_message += f"Producto: {alert['title']} (SKU: {alert['sku']}) - Inventario: {alert['inventory']}\n"

            # Log de alertas en la consola
            print(alert_message)

            # Enviar correo electrónico con Flask-Mail
            if app.config.get("MAIL_USERNAME"):
                msg = Message(
                    subject="Alerta de Inventario Bajo",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=["alex70000000@gmail.com"],  # Cambia esto al correo del destinatario
                    body=alert_message
                )
                mail.send(msg)

        return send_file(
            output_file,
            as_attachment=True,
            download_name='inventory_report.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return jsonify({'error': f'Ocurrió un error al sincronizar el inventario: {str(e)}'}), 500


# Importar APScheduler para la tarea automática
from apscheduler.schedulers.background import BackgroundScheduler

def scheduled_sync():
    with app.app_context():
        sync_inventory()

# Configurar el programador
scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_sync, trigger="interval", hours=24)  # Ejecutar cada 24 horas
scheduler.start()

# Manejar cierre del programador al apagar el servidor
import atexit
atexit.register(lambda: scheduler.shutdown())

# Configurar Flask-Mail
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''  # Cambia esto por tu correo
app.config['MAIL_PASSWORD'] = ''        # Cambia esto por tu contraseña
mail = Mail(app)

@app.route('/send_test_email')
def send_test_email():
    try:
        msg = Message(
            subject="Correo de Prueba",
            sender=app.config['MAIL_USERNAME'],
            recipients=["alex70000000@gmail.com"],
            body="Este es un correo de prueba enviado desde Flask-Mail."
        )
        mail.send(msg)
        return "Correo enviado correctamente"
    except Exception as e:
        return f"Error al enviar correo: {e}"




if __name__ == "__main__":
    app.run(debug=True)


    


    
