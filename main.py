from flask import Flask, request, jsonify
import logging
from src.nlp.nlp import process_file
from src.model.llm import refine_data
import os
import easyocr
from PIL import Image
import io

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializa o Flask
app = Flask(__name__)

# Função de processamento que só será chamada quando houver uma requisição POST
def process_file_content(file_content):
    try:
        # Inicializar o leitor EasyOCR
        logger.info("Inicializando EasyOCR para extração de texto")
        reader = easyocr.Reader(['pt', 'en'])  # Suporte para português e inglês

        # Convertendo o conteúdo binário para imagem
        logger.info("Convertendo o conteúdo para imagem")
        image = Image.open(io.BytesIO(file_content))

        # Usar o EasyOCR para extrair o texto da imagem
        logger.info("Extraindo texto da imagem usando EasyOCR")
        result = reader.readtext(image)

        # Extraindo o texto
        extracted_data = " ".join([text[1] for text in result])
        logger.info(f"Texto extraído: {extracted_data}")

        # Refina os dados extraídos
        logger.info("Refinando os dados extraídos com LLM")
        refined_data = refine_data(extracted_data.splitlines())
        logger.info(f"Dados refinados: {refined_data}")

        return refined_data

    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return {"message": "Erro inesperado no processamento."}, 500

@app.route('/api', methods=['POST'])
def process_request():
    try:
        # Obtém o conteúdo binário do arquivo da requisição
        file_content = request.data
        if not file_content:
            logger.error("Nenhum conteúdo encontrado na requisição.")
            return jsonify({"message": "Arquivo não enviado na requisição."}), 400

        logger.info("Conteúdo do arquivo recebido com sucesso")

        # Chama a função de processamento
        refined_data = process_file_content(file_content)

        # Se houve erro no processamento, a função retornará uma mensagem de erro
        if isinstance(refined_data, tuple):
            return jsonify(refined_data[0]), refined_data[1]

        # Retorna os dados refinados como resposta
        logger.info("Retornando a resposta para o cliente")
        return jsonify({"extracted_data": refined_data})

    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return jsonify({"message": "Erro inesperado no processamento."}), 500

# Inicia o servidor Flask
if __name__ == '__main__':
    try:
        # Log para indicar que o servidor está iniciando
        logger.info("Servidor iniciado e esperando o envio do documento.")
        # Rodar o servidor na interface 0.0.0.0 e na porta 5000
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Erro ao iniciar o servidor: {str(e)}")
