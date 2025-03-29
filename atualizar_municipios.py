import json
import unidecode  # para remover acentos
import re

def carregar_ufs():
    """Carrega o mapeamento de códigos IBGE para UFs"""
    with open('importador/data/UF.json', 'r', encoding='utf-8-sig') as f:
        ufs = json.load(f)
    return {str(uf['codigo_ibge']).zfill(2): uf['uf'] for uf in ufs}

def normalizar_texto(texto):
    """Normaliza o texto removendo acentos e convertendo para maiúsculo"""
    # Remove acentos e caracteres especiais
    texto = unidecode.unidecode(texto)
    # Converte para maiúsculo
    texto = texto.upper()
    # Remove caracteres não alfanuméricos exceto espaços
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    return texto

def atualizar_municipios():
    # Carregar mapeamento de UFs
    ufs = carregar_ufs()
    
    # Carregar o arquivo GeoJSON
    with open('importador/data/municipios.geojson', 'r', encoding='utf-8-sig') as f:
        geojson = json.load(f)
    
    # Processar cada município
    for feature in geojson['features']:
        # Extrair os dois primeiros dígitos do ID
        municipio_id = feature['properties']['id']
        codigo_uf = str(municipio_id)[:2]
        
        # Adicionar a UF correspondente
        if codigo_uf in ufs:
            feature['properties']['UF'] = ufs[codigo_uf]
        
        # Normalizar o nome do município
        if 'name' in feature['properties']:
            nome_original = feature['properties']['name']
            nome_normalizado = normalizar_texto(nome_original)
            feature['properties']['name'] = nome_normalizado
    
    # Salvar o arquivo atualizado
    with open('importador/data/municipios.geojson', 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("Iniciando atualização dos municípios...")
    atualizar_municipios()
    print("Atualização concluída!") 