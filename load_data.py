import os
import django
import json
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

def importar_dados():
    # Limpar dados existentes
    Propriedade.objects.all().delete()
    
    # Carregar dados do arquivo JSON
    with open('backup_propriedades.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Importar cada propriedade
    for item in data:
        fields = item['fields']
        Propriedade.objects.create(
            titulo=fields['titulo'],
            descricao=fields['descricao'],
            valor=fields['valor'],
            cidade=fields['cidade'],
            estado=fields['estado'],
            bairro=fields['bairro'],
            link=fields['link'],
            area_privativa=fields['area_privativa'],
            area_terreno=fields['area_terreno'],
            quartos=fields['quartos'],
            banheiros=fields['banheiros'],
            vagas=fields['vagas'],
            tipo_imovel=fields['tipo_imovel'],
            latitude=fields['latitude'],
            longitude=fields['longitude']
        )
    
    print(f"Importados {len(data)} imóveis com sucesso!")

if __name__ == '__main__':
    importar_dados() 