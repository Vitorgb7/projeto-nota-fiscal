import json
import re
from groq import Groq
from dotenv import load_dotenv
import os
from nltk.tokenize import word_tokenize  # Exemplo de uso do nltk
import logging

# Carregar variáveis de ambiente
load_dotenv()

# Configuração da chave da API
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def adjust_value_format(value):
    """
    Ajusta o valor total, formatando corretamente para duas casas decimais.
    """
    if not value:
        return "0,00"

    # Normaliza o valor para remover caracteres indesejados
    value = re.sub(r'[^\d.,]', '', value)
    value = value.replace('.', '').replace(',', '')
    value = value.zfill(4)[:-3] if len(value) > 3 else value.zfill(4)
    adjusted_value = f"{value[:-2]},{value[-2:]}"
    return adjusted_value if ',' in adjusted_value else f"0,{adjusted_value}"

def adjust_serie_data(extracted_data):
    """
    Ajusta a série da nota fiscal a partir de um padrão definido.
    """
    series_pattern = re.search(r"Série:\s*(\S+)", extracted_data)
    return series_pattern.group(1) if series_pattern else None

def refine_data(extracted_data):
    """
    Refina os dados utilizando a LLM Groq.
    """
    refined_data = {key: None for key in [
        "nome_emissor", "CNPJ_emissor", "endereco_emissor", "CNPJ_CPF_consumidor",
        "data_emissao", "numero_nota_fiscal", "serie_nota_fiscal", "valor_total", "forma_pgto"
    ]}

    # Log do conteúdo extraído antes do refinamento
    logger.info(f"Conteúdo extraído antes do refinamento: {extracted_data}")
    
    # Prompt para refinar os dados
    prompt = f"""
Você é um modelo de IA especializado em extração de dados de notas fiscais. Analise os dados abaixo e extraia as informações no formato JSON especificado:

### Estrutura JSON:
{{
    "nome_emissor": "Nome do emissor da nota fiscal",
    "CNPJ_emissor": "CNPJ do emissor",
    "endereco_emissor": "Endereço completo do emissor",
    "CNPJ_CPF_consumidor": "CNPJ ou CPF do consumidor",
    "data_emissao": "Data de emissão da nota fiscal",
    "numero_nota_fiscal": "Número da nota fiscal",
    "serie_nota_fiscal": "Série da nota fiscal",
    "valor_total": "Valor total da nota fiscal",
    "forma_pgto": "Forma de pagamento"
}}

### Dados extraídos da imagem:
{'\n'.join(extracted_data)}
"""
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192"
        )
        
        # Obter resposta bruta do modelo
        raw_output = response.choices[0].message.content.strip()
        logger.info(f"Resposta bruta do modelo: {raw_output}")
        
        refined_data = _parse_and_validate_json(raw_output)
        
        if not refined_data or "valor_total" not in refined_data:
            logger.error(f"Erro nos dados refinados: {raw_output}")
            return refined_data
        
        # Ajustar o valor total e a série
        refined_data["valor_total"] = adjust_value_format(refined_data.get("valor_total"))
        refined_data["serie_nota_fiscal"] = adjust_serie_data('\n'.join(extracted_data))

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Erro ao processar JSON: {e}")
    except Exception as e:
        logger.error(f"Erro na LLM Groq: {e}")

    return refined_data

def _parse_and_validate_json(response_text):
    """
    Valida e converte uma string em JSON.
    """
    response_text = re.sub(r"(?<=\{|,)\s*'([^']+)'\s*:", r'"\1":', response_text.replace("'", '"'))
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {e}")
        return None

if __name__ == "__main__":
    # Exemplo de dados extraídos
    extracted_data_example = [
        "Loja Exemplo Ltda", "CNPJ: 12.345.678/0001-99",
        "Rua das Flores, 123, São Paulo, SP", "Consumidor: CPF 987.654.321-00",
        "Data: 27/11/2024", "Nota Fiscal: 123456 Série: A1",
        "Valor Total: R$ 1.234,56", "Forma de Pagamento: Cartão de Crédito"
    ]
    print("Dados Refinados:", json.dumps(refine_data(extracted_data_example), indent=2, ensure_ascii=False))
