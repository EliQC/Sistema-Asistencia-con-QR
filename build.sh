#!/usr/bin/env bash
# Instalar dependencias
pip install -r requirements.txt
# Aplicar migraciones a la base de datos
python manage.py migrate

# Crear un superusuario si no existe (usando variables de entorno)
echo "from django.contrib.auth import get_user_model; User = get_user_model(); import os; username=os.environ.get('DJANGO_SUPERUSER_USERNAME'); email=os.environ.get('DJANGO_SUPERUSER_EMAIL'); password=os.environ.get('DJANGO_SUPERUSER_PASSWORD'); User.objects.filter(username=username).exists() or User.objects.create_superuser(username, email, password)" | python manage.py shell
