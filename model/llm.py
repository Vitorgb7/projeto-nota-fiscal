import json
from groq import Groq
import re

# Configuração da chave da API Groq
client = Groq(api_key="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")

def adjust_value_format(value):
    """
    Ajusta o valor total, removendo os últimos três números e posicionando a vírgula na segunda casa decimal corretamente.
    """
    if value:
        # Remove caracteres não numéricos (exceto vírgula e ponto)
        value = re.sub(r'[^\d.,]', '', value)

        # Remove separadores de milhares (pontos ou vírgulas)
        value = value.replace('.', '').replace(',', '')

        # Garantir que o valor tenha pelo menos 4 dígitos
        if len(value) <= 3:
            value = value.zfill(4)

        # Se o valor tiver mais de 4 dígitos, remove os 3 últimos
        if len(value) > 4:
            value = value[:-3]
        
        # Formatação do valor para 4 casas decimais e inserção da vírgula
        adjusted_value = value[:-2] + ',' + value[-2:]

        # Caso o valor tenha apenas 1 ou 2 dígitos, coloca o zero à esquerda
        if adjusted_value.startswith(','):
            adjusted_value = '0' + adjusted_value
        
        # Garantir que tenha 4 casas decimais (adicionando zeros, se necessário)
        if not adjusted_value.endswith(',00'):
            adjusted_value += '00'

        return adjusted_value

    return "0,00"





def adjust_serie_data(extracted_data):
    """
    Ajusta a série da nota fiscal, caso esteja disponível nos dados extraídos.
    """
    series_pattern = re.search(r"Série:\s*(\S+)", extracted_data)
    if series_pattern:
        return series_pattern.group(1)
    return None


def refine_data(extracted_data):
    """
    Refinamento dos dados utilizando a LLM Groq para complementar e validar os resultados.
    """
    refined_data = {
        "nome_emissor": None,
        "CNPJ_emissor": None,
        "endereco_emissor": None,
        "CNPJ_CPF_consumidor": None,
        "data_emissao": None,
        "numero_nota_fiscal": None,
        "serie_nota_fiscal": None,
        "valor_total": None,
        "forma_pgto": None
    }

    # Prompt base para a LLM Groq
    base_prompt = """
Você é um modelo de IA especializado em análise e extração de dados estruturados e semi-estruturados de documentos como notas fiscais. 
Sua tarefa é analisar os dados fornecidos e refinar, validar e complementar as informações de forma precisa, garantindo que nenhum dado relevante seja ignorado. 
A resposta deve ser fornecida em formato JSON.

### Estrutura do JSON esperada:
{
    "nome_emissor": "nome da empresa ou pessoa que emitiu a nota",
    "CNPJ_emissor": "CNPJ da empresa emitente",
    "endereco_emissor": "endereço completo da empresa emitente",
    "CNPJ_CPF_consumidor": "CNPJ ou CPF do consumidor",
    "data_emissao": "data da emissão no formato YYYY-MM-DD",
    "numero_nota_fiscal": "número da nota fiscal",
    "serie_nota_fiscal": "série da nota fiscal",
    "valor_total": "valor total da nota fiscal (com ou sem vírgula)",
    "forma_pgto": "forma de pagamento (ex: Cartão, Dinheiro, PIX, etc.)"
}

### Importante:
1. Caso algum dado esteja ausente, você deve retornar o valor como null.
2. Caso não consiga identificar claramente algum dado, forneça uma explicação razoável no campo correspondente.
3. Garanta que os campos sejam preenchidos corretamente de acordo com os padrões estabelecidos. Em casos onde os dados não sigam o formato esperado, busque normalizar ao máximo.
4. Se algum dado estiver em um formato ambíguo ou não puder ser determinado com certeza, marque como null e, se possível, explique.
5. Quando os dados não estiverem completos ou faltando informações, forneça um valor default adequado, como "null", e não deixe campos vazios.

### Dados fornecidos:
"""

    # Preparando os dados para enviar no prompt
    input_data = "\n".join(extracted_data)
    final_prompt = base_prompt + input_data + "\n"

    print("Prompt final enviado:", final_prompt)  # Depuração

    try:
        # Usando o modelo 'llama3-8b-8192' ou outro modelo Groq disponível
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "system", "content": "Você é um assistente útil."
            }, {
                "role": "user", "content": final_prompt
            }],
            model="llama3-8b-8192"
        )

        # Captura a resposta da LLM
        llm_output = chat_completion.choices[0].message.content.strip()
        print("Resposta da API:", llm_output)  # Depuração

        # Ajustar o conteúdo para JSON válido
        refined_data = _validate_and_convert_to_json(llm_output)

        # Ajuste do campo valor_total
        refined_data["valor_total"] = adjust_value_format(refined_data.get("valor_total"))

        # Ajuste do campo serie_nota_fiscal
        refined_data["serie_nota_fiscal"] = adjust_serie_data(extracted_data)

    except json.JSONDecodeError as e:
        print("Erro ao decodificar JSON:", e)
        print("Saída original da LLM:", llm_output)  # Depuração para análise do formato errado
    except Exception as e:
        print("Erro ao usar a LLM Groq:", e)

    return refined_data


def _validate_and_convert_to_json(response_text):
    """
    Valida e converte o texto retornado pela LLM em JSON válido.
    """
    try:
        if not response_text.startswith("{") or not response_text.endswith("}"):
            # Extrai apenas a parte relevante se houver texto extra
            response_text = response_text.split("{", 1)[-1]
            response_text = "{" + response_text.split("}")[-2] + "}"

        # Substitui aspas simples por aspas duplas
        response_text = response_text.replace("'", '"')

        # Valida se as chaves têm aspas duplas e ajusta se necessário
        response_text = _ensure_double_quoted_keys(response_text)

        # Converte a string JSON em um dicionário Python
        return json.loads(response_text)
    except Exception as e:
        print("Erro ao validar ou ajustar a resposta JSON:", e)
        raise


def _ensure_double_quoted_keys(json_string):
    """
    Garante que as chaves do JSON estão com aspas duplas.
    """
    pattern = r"(?<=\{|,)\s*'([^']+)'\s*:"
    return re.sub(pattern, r'"\1":', json_string)


# Simulação de dados extraídos
extracted_data_example = [
    "Loja Exemplo Ltda",
    "CNPJ: 12.345.678/0001-99",
    "Rua das Flores, 123, São Paulo, SP",
    "Consumidor: CPF 987.654.321-00",
    "Data: 27/11/2024",
    "Nota Fiscal: 123456 Série: A1",
    "Valor Total: R$ 1.234,56",
    "Forma de Pagamento: Cartão de Crédito"
]

# Testando a função com os dados extraídos
refined_data_result = refine_data(extracted_data_example)
print("Dados Refinados:", json.dumps(refined_data_result, indent=1, ensure_ascii=False))