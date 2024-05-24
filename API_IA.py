from flask import Flask, request, jsonify
import base64
import os
from werkzeug.utils import secure_filename
from langchain_openai import ChatOpenAI
from langchain.schema.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración del modelo y parser
class Producto(BaseModel):
    estado: str = Field(description="Estado del Producto. Posibles valores: perfecto estado, con marcas de uso, para reparar o piezas")
    marca: str = Field(description="Marca del produto")
    modelo: str = Field(description="Modelo del producto")
    daño: str = Field(description="Descripción de los daños/marcas de uso del producto")
    descripcion: str =Field(descripcion="Descripción de anuncio para atraer clientes")
    enfoque: bool = Field(description="La foto está enfocada")
    dedo: bool = Field(description="La foto contiene un dedo que impide ver parte del producto")

parser = JsonOutputParser(pydantic_object=Producto)

template = template = """You are a system that analyzes images of second-hand products.
You must indicate the following characteristics of the product in Spanish:
- Condition: product condition. Possible values: perfect condition, with signs of use, for repair or parts
- Brand: product brand
- Model: product model
- Damage/Signs of use: if the product has any damage or signs of use, describe it
- Description: description of the advertisement to attract customers where it is named and includes
- Focus: the photo is focused. True or False.
- Finger: the photo contains a finger that obscures part of the product. True or False.
{format_instructions}
"""

prompt = PromptTemplate(
    template=template,
    input_variables=[],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def analize_image(image_path,prompt):
    base64_image = encode_image(image_path)
    content_image = [{"type": "image_url", "image_url": f"data:image/png;base64,{base64_image}"}]

    system_messsage = SystemMessage(content=prompt.format())
    human_message = HumanMessage(
                content=content_image
            )

    chat = ChatOpenAI(model="gpt-4-vision-preview", max_tokens=256,openai_api_key="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")

    chain = chat | parser

    response = chain.invoke([system_messsage, human_message])
    return response

@app.route('/analyze_image', methods=['POST'])
def analyze_image_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files['image'] #diccionario con los archivos enviados en la solicitud
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename) #Nombre seguro para el archivo, (caŕacteres raros, intento inyección de rutas)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) #uploads/i'nombre de la imagen'
        file.save(file_path)

        try:
            response = analize_image(file_path, prompt) 
            os.remove(file_path)  # Opcional: eliminar la imagen después del procesamiento
            return jsonify(response)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
