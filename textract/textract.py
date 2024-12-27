import boto3
import logging
import re
import string
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env, se necessário
load_dotenv()

# Configura o logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Nome do bucket S3
BUCKET_NAME = os.getenv('BUCKET_NAME')

# Lista personalizada de stopwords em português
STOPWORDS = set([
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "um", "uma", "uns", "umas",
    "e", "em", "para", "com", "por", "não", "se", "mas", "como", "mais", "foi", "isso", 
    "pela", "pelos", "à", "ao", "nas", "nos", "depois", "antes", "só", "toda"
])

def simple_tokenize(text):
    """Tokenização simples: remove pontuação e divide palavras."""
    text = text.lower()  # Converte para minúsculas
    text = text.translate(str.maketrans('', '', string.punctuation))  # Remove pontuação
    return text.split()

def simple_lemmatize(word):
    """Retorna a palavra original (placeholder para lematização)."""
    return word

def process_file(decode_content):
    try:
        logger.info("Iniciando o processamento do arquivo")

        # Inicializa os clientes AWS usando SSO
        s3_client = boto3.client('s3')
        textract_client = boto3.client('textract')

        # Listar arquivos existentes no bucket
        existing_files = []
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            existing_files = [obj['Key'] for obj in response['Contents']]

        # Determinar o próximo número disponível
        numbers = [
            int(re.match(r"(\d+)_nota\.jpg", key).group(1))
            for key in existing_files if re.match(r"(\d+)_nota\.jpg", key)
        ]
        next_number = max(numbers) + 1 if numbers else 1
        file_key = f"{next_number}_nota.jpg"

        # Upload do arquivo para o S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=file_key, Body=decode_content, ContentType="image/jpg")

        # Processamento com Textract
        textract_response = textract_client.detect_document_text(
            Document={"S3Object": {"Bucket": BUCKET_NAME, "Name": file_key}}
        )

        # Extrair texto do Textract
        text_blocks = textract_response.get('Blocks', [])
        extracted_data = [block['Text'] for block in text_blocks if block['BlockType'] == 'LINE']

        # Verificar forma de pagamento
        forma_pagamento = "outros"
        for line in extracted_data:
            if "dinheiro" in line.lower() or "pix" in line.lower():
                forma_pagamento = "dinheiro"
                break

        folder = "dinheiro" if forma_pagamento == "dinheiro" else "outros"

        # Verificar arquivos na pasta de destino
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{folder}/")
        existing_files = []
        if 'Contents' in response:
            existing_files = [obj['Key'] for obj in response['Contents']]

        # Determinar o próximo número disponível
        numbers = [
            int(re.match(rf"{folder}/(\d+)_nota\.jpg", key).group(1))
            for key in existing_files if re.match(rf"{folder}/(\d+)_nota\.jpg", key)
        ]
        next_number = max(numbers) + 1 if numbers else 1
        dest_file_key = f"{folder}/{next_number}_nota.jpg"

        # Mover arquivo para a pasta correta
        s3_client.copy_object(
            Bucket=BUCKET_NAME,
            CopySource={'Bucket': BUCKET_NAME, 'Key': file_key},
            Key=dest_file_key
        )
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_key)

        # Processar dados com tokenização e filtragem
        refined_data = []
        for text in extracted_data:
            tokens = simple_tokenize(text)
            filtered_tokens = [word for word in tokens if word not in STOPWORDS]
            lemmatized_tokens = [simple_lemmatize(word) for word in filtered_tokens]
            refined_data.append(" ".join(lemmatized_tokens))

        return refined_data

    except Exception as e:
        logger.error(f"Erro no processamento do arquivo: {str(e)}")
        return []
