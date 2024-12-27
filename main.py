from flask import Flask, request, jsonify
import boto3
import json
import base64
import logging
from botocore.exceptions import BotoCoreError, ClientError
from src.textract.textract import process_file
from src.model.llm import refine_data
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializa o cliente S3
s3_client = boto3.client('s3')

# Nome do bucket S3
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Inicializa o Flask
app = Flask(__name__)

# Função de processamento que só será chamada quando houver uma requisição POST
def process_file_content(file_content):
    try:
        # Decodificar conteúdo base64
        logger.info("Conteúdo do arquivo decodificado com sucesso")
        decode_content = base64.b64decode(file_content)

        # Processa o arquivo (armazenar e extrair dados com Textract)
        logger.info("Processando o arquivo com Textract")
        extracted_data = process_file(decode_content)
        logger.info(f"Dados extraídos do Textract: {extracted_data}")

        # Refina os dados extraídos
        logger.info("Refinando os dados extraídos com LLM")
        refined_data = refine_data(extracted_data)
        logger.info(f"Dados refinados: {refined_data}")

        return refined_data

    except (BotoCoreError, ClientError) as error:
        logger.error(f"Erro AWS: {str(error)}")
        return {"message": "Erro ao processar o arquivo com AWS Textract."}, 500
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return {"message": "Erro inesperado no processamento."}, 500

@app.route('/api', methods=['POST'])
def process_request():
    try:
        # Obtém o conteúdo do arquivo da requisição
        get_file_content = request.json.get('content')
        if not get_file_content:
            logger.error("Nenhum conteúdo encontrado no evento.")
            return jsonify({"message": "Arquivo não enviado na requisição."}), 400

        logger.info("Conteúdo do arquivo recebido com sucesso")

        # Chama a função de processamento
        refined_data = process_file_content(get_file_content)

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
    logger.info("Servidor iniciado e esperando o envio do documento.")
    app.run(debug=True)
