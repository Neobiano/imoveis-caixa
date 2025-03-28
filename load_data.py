import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

def importar_dados():
    # Limpar dados existentes
    Propriedade.objects.all().delete()
    
    # Tentar diferentes codificações
    encodings = ['utf-8', 'latin1', 'cp1252']
    data = None
    
    for encoding in encodings:
        try:
            with open('backup_propriedades.json', 'r', encoding=encoding) as f:
                data = json.load(f)
            break
        except UnicodeDecodeError:
            continue
    
    if data is None:
        print("Erro: Não foi possível ler o arquivo JSON com nenhuma das codificações tentadas.")
        return
    
    # Importar cada propriedade
    for item in data:
        fields = item['fields']
        try:
            Propriedade.objects.create(
                titulo=fields['titulo'],
                descricao=fields['descricao'],
                valor=fields['valor'],
                cidade=fields['cidade'],
                estado=fields['estado'],
                bairro=fields['bairro'],
                link=fields['link'],
                area_privativa=fields.get('area_privativa'),
                area_terreno=fields.get('area_terreno'),
                quartos=fields.get('quartos'),
                banheiros=fields.get('banheiros'),
                vagas=fields.get('vagas'),
                tipo_imovel=fields.get('tipo_imovel'),
                latitude=fields.get('latitude'),
                longitude=fields.get('longitude')
            )
        except Exception as e:
            print(f"Erro ao importar propriedade: {e}")
            print(f"Dados: {fields}")
            continue
    
    print(f"Importados {len(data)} imóveis com sucesso!")

if __name__ == '__main__':
    importar_dados() 