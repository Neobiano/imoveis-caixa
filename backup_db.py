import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

from propriedades.models import Propriedade

# Buscar todas as propriedades
propriedades = Propriedade.objects.all()

# Converter para dicionário
data = []
for prop in propriedades:
    data.append({
        'model': 'propriedades.propriedade',
        'pk': prop.id,
        'fields': {
            'titulo': prop.titulo,
            'descricao': prop.descricao,
            'valor': str(prop.valor),
            'cidade': prop.cidade,
            'estado': prop.estado,
            'bairro': prop.bairro,
            'link': prop.link,
            'area_privativa': prop.area_privativa,
            'area_terreno': prop.area_terreno,
            'quartos': prop.quartos,
            'banheiros': prop.banheiros,
            'vagas': prop.vagas,
            'tipo_imovel': prop.tipo_imovel,
            'latitude': prop.latitude,
            'longitude': prop.longitude,
        }
    })

# Salvar em arquivo JSON
with open('backup_propriedades.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2) 