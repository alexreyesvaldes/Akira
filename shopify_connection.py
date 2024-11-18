import requests
import json

# Configuración de la conexión
SHOP_NAME = ""  # Subdominio de tu tienda Shopify
ACCESS_TOKEN = "SHOPIFY_TOKEN"  # Token de acceso generado en Shopify

# URL del endpoint para crear productos
url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2024-10/products.json"

# Encabezados de la solicitud
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN,
}

# Datos del producto que se va a crear
producto = {
    "product": {
        "title": "Producto de Prueba",
        "body_html": "<strong>Este es un producto creado mediante la API de Shopify</strong>",
        "vendor": "Mi Marca",
        "product_type": "Prueba",
        "variants": [
            {
                "option1": "Default Title",
                "price": "19.99",
                "sku": "PRUEBA-001"
            }
        ]
    }
}

# Enviar la solicitud POST
response = requests.post(url, headers=headers, data=json.dumps(producto))

# Manejo de la respuesta
if response.status_code == 201:
    print("Producto creado con éxito:")
    print(response.json())
else:
    print(f"Error al crear el producto: {response.status_code} - {response.text}")










