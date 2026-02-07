#!/usr/bin/env bash
# exit on error
set -o errexit
# Instalar las librerías de Python
pip install -r requirements.txt
python manage.py collectstatic --no-input
# Aplicar las migraciones (preparar la base de datos)
python manage.py migrate
python manage.py createsuperuser --no-input || true
python cargar_datos.py