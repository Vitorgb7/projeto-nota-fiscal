import pytesseract
from PIL import Image
import logging
import re
import string
from dotenv import load_dotenv
import os
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import RSLPStemmer

# Baixar pacotes necessários do NLTK
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('rslp')  # Baixando o recurso necessário para stemming em português

# Carregar variáveis de ambiente do arquivo .env, se necessário
load_dotenv()

# Configura o logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Stopwords do NLTK em português
STOPWORDS = set(stopwords.words('portuguese'))

# Inicializar o stemmer para português
stemmer = RSLPStemmer()

def process_text_with_nltk(text):
    """Processa texto usando NLTK: tokenização, remoção de stopwords e stemming."""
    # Tokeniza o texto
    tokens = word_tokenize(text.lower())  # Converte para minúsculas e tokeniza

    # Remove pontuação e filtra stopwords
    filtered_tokens = [
        token for token in tokens 
        if token.isalnum() and token not in STOPWORDS
    ]

    # Aplica stemming nos tokens restantes
    stemmed_tokens = [stemmer.stem(token) for token in filtered_tokens]

    return stemmed_tokens

def process_file(image_path):
    try:
        logger.info("Iniciando o processamento do arquivo")

        # Realiza OCR na imagem
        image = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(image, lang='por')  # Especifica o idioma português

        # Dividir o texto em linhas
        extracted_data = extracted_text.splitlines()

        # Verificar forma de pagamento
        forma_pagamento = "outros"
        for line in extracted_data:
            if "dinheiro" in line.lower() or "pix" in line.lower():
                forma_pagamento = "dinheiro"
                break

        # Processar cada linha de texto com NLTK
        refined_data = []
        for text in extracted_data:
            tokens = process_text_with_nltk(text)
            refined_data.append(" ".join(tokens))

        logger.info(f"Forma de pagamento detectada: {forma_pagamento}")
        return {"forma_pagamento": forma_pagamento, "refined_data": refined_data}

    except Exception as e:
        logger.error(f"Erro no processamento do arquivo: {str(e)}")
        return {"error": str(e)}
