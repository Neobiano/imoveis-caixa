#!/usr/bin/env bash
# exit on error
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Criar superusuário apenas se não existir
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Criar o site se não existir
echo "from django.contrib.sites.models import Site; Site.objects.get_or_create(id=1, defaults={'domain': 'imoveis-caixa.onrender.com', 'name': 'imoveis-caixa.onrender.com'})" | python manage.py shell 