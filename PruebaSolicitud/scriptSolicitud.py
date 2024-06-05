import requests

# URL de la API
url = "http://127.0.0.1:5000/analyze_image"

# Archivo de imagen que quieres enviar
archivo_imagen = {'image': open('img/foto3.jpg', 'rb')} #Lectura y binario

# Hacer la solicitud POST a la API
response = requests.post(url, files=archivo_imagen)

# Imprimir la respuesta
print(response.json())
