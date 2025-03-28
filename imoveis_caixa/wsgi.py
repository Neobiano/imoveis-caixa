"""
WSGI config for imoveis_caixa project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imoveis_caixa.settings')

application = get_wsgi_application() 