from flask import Flask, request, jsonify  # Importa Flask para crear el servidor web y otros módulos necesarios
import base64  # Para codificar imágenes a base64
import os  # Para operaciones con el sistema de archivos
from werkzeug.utils import secure_filename  # Para asegurar nombres de archivo seguros
from langchain_openai import ChatOpenAI  # Para la comunicación con el modelo de lenguaje de OpenAI
from langchain.schema.messages import HumanMessage, SystemMessage  # Para estructurar los mensajes enviados al modelo de lenguaje
from langchain_core.output_parsers import JsonOutputParser  # Para analizar la salida del modelo y convertirla en objetos JSON
from langchain.prompts import PromptTemplate  # Para generar la plantilla de instrucciones
from langchain_core.pydantic_v1 import BaseModel, Field  # Para definir la estructura esperada de los datos del producto

app = Flask(__name__)  # Crea una instancia de Flask

UPLOAD_FOLDER = 'uploads'  # Carpeta donde se almacenarán las imágenes cargadas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Crea la carpeta si no existe
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Configura la carpeta de carga en la aplicación Flask

# Definición de la estructura esperada de los datos del producto utilizando Pydantic
class Producto(BaseModel):
    estado: str = Field(description="Estado del Producto. Posibles valores: perfecto estado, con marcas de uso, para reparar o piezas")
    marca: str = Field(description="Marca del producto")
    modelo: str = Field(description="Modelo del producto")
    daño: str = Field(description="Descripción de los daños/marcas de uso del producto")
    titulo: str =Field(description="Título llamativo sobre el producto")
    descripcion: str =Field(descripcion="Descripción de anuncio para atraer clientes")
    enfoque: bool = Field(description="La foto está enfocada")
    dedo: bool = Field(description="La foto contiene un dedo que impide ver parte del producto")

# Parser para convertir la salida del modelo en un objeto Pydantic Producto
parser = JsonOutputParser(pydantic_object=Producto)

# Plantilla de instrucciones para la interacción con el modelo de lenguaje
template = """You are a system that analyzes images of second-hand products.
You must indicate the following characteristics of the product in Spanish:
- Condition: product condition. Possible values: perfect condition, with signs of use, for repair or parts
- Brand: product brand
- Model: product model
- Damage/Signs of use: if the product has any damage or signs of use, describe it
- Title: catchy and short title about the product
- Description: description of the advertisement to attract customers where it is named and includes
- Focus: the photo is focused. True or False.
- Finger: the photo contains a finger that obscures part of the product. True or False.
{format_instructions}
"""

# Crea la plantilla de instrucciones con la plantilla y las instrucciones del parser
prompt = PromptTemplate(
    template=template,
    input_variables=[],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# Función para codificar una imagen a base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Analiza la imagen utilizando un modelo de lenguaje y un modelo de visión de OpenAI
def analize_image(image_path,prompt,retries=2):
    base64_image = encode_image(image_path)
    content_image = [{"type": "image_url", "image_url": f"data:image/png;base64,{base64_image}"}] #Se crea un diccionario con el tipo y la ruta

    system_messsage = SystemMessage(content=prompt.format()) #Mensaje del sistema
    human_message = HumanMessage(content=content_image) #Mensaje Humano

    chat = ChatOpenAI(model="gpt-4-vision-preview", max_tokens=256,openai_api_key="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",temperature=0.2) #Valor más bajo más determinista

    chain = chat | parser #Se crea la cadena de procesamiento

    for _ in range(retries):
        try:
            response = chain.invoke([system_messsage, human_message])
            if validate_response(response):
                return response
        except Exception as e:
            print(e)
            last_exception= e
            continue
    return{"error":str(last_exception)}

# Valida si la respuesta del modelo tiene todas las claves requeridas
def validate_response(response):
    required_keys = {"estado", "marca", "modelo", "daño", "titulo", "descripcion", "enfoque", "dedo"}
    return isinstance(response, dict) and required_keys.issubset(response.keys())

# Endpoint para analizar una imagen
@app.route('/analyze_image', methods=['POST'])
def analyze_image_endpoint(): 
    if 'image' not in request.files: #No se ha enviado imagen
        return jsonify({"error": "No image provided"}), 400

    file = request.files['image']  # Obtiene el archivo de la solicitud
    if file.filename == '': #Se envía la solicitud pero vacía
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)  # Asegura el nombre del archivo por si tiene carácteres extraños
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Genera la ruta del archivo
        file.save(file_path)  # Guarda el archivo en la carpeta

        try:
            response = analize_image(file_path, prompt)  # Analiza la imagen
            os.remove(file_path)  # Opcional: elimina la imagen después del procesamiento
            return jsonify(response)  # Devuelve la respuesta del análisis
        except Exception as e:
            return jsonify({"error": str(e)}), 500  

if __name__ == '__main__':
    app.run(debug=True)  
