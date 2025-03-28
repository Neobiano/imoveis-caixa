import os
import django
import json
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')
django.setup()

# Fazer o dump dos dados
call_command('dumpdata', 'propriedades', output='backup_propriedades.json', indent=2)

# Ler o arquivo e reescrever com codificação UTF-8
with open('backup_propriedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('backup_propriedades.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder) 