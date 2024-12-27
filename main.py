import boto3
import json
import base64
import logging
import time
from botocore.exceptions import BotoCoreError, ClientError
from src.textract.textract import process_file
from src.models.llm import refine_data
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

def process_request(event, context):
    try:
        logger.info("Iniciando a execução da função Lambda")

        # Obtém o conteúdo do arquivo da requisição
        get_file_content = event.get('content')
        if not get_file_content:
            logger.error("Nenhum conteúdo encontrado no evento.")
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Arquivo não enviado na requisição."})
            }

        logger.info("Conteúdo do arquivo recebido com sucesso")
        decode_content = base64.b64decode(get_file_content)
        logger.info("Conteúdo do arquivo decodificado com sucesso")

        # Processa o arquivo (armazenar e extrair dados com Textract)
        logger.info("Processando o arquivo")
        extracted_data = process_file(decode_content)
        logger.info(f"Dados extraídos do Textract: {extracted_data}")

        # Refina os dados extraídos
        logger.info("Refinando os dados extraídos")
        refined_data = refine_data(extracted_data)
        logger.info(f"Dados refinados: {refined_data}")

        # Retorna os dados refinados como resposta
        logger.info("Retornando a resposta para o cliente")
        return {
            "statusCode": 200,
            "body": json.dumps({"extracted_data": refined_data}, ensure_ascii=False)
        }

    except (BotoCoreError, ClientError) as error:
        logger.error(f"Erro AWS: {str(error)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Erro ao processar o arquivo com AWS Textract."})
        }
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Erro inesperado no processamento."})
        }
