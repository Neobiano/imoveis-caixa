import requests
import json
import os
from datetime import datetime

# Configurar a requisição para a API do Gemini
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={os.environ.get('GEMINI_API_KEY')}"

headers = {
    'Content-Type': 'application/json'
}

data = {
    "contents": [{
        "parts":[{
            "text": "Explique em Português-BR, a real situação do imovel citado neste documento e se eu preciso ter algum cuidado na aquisição https://venda-imoveis.caixa.gov.br/editais/matricula/CE/1444415131602.pdf"
        }]
    }]
}

response = requests.post(url, headers=headers, json=data)

# Criar nome do arquivo com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"resposta_gemini_{timestamp}.json"

# Salvar resposta em arquivo JSON
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=2)

print(f"Resposta salva em: {filename}") 