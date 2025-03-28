"""
ASGI config for imoveis_caixa project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')

application = get_asgi_application() 