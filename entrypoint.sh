#!/bin/sh
set -e

echo "Migration'lar uygulanıyor..."
python manage.py migrate --noinput

echo "Statik dosyalar toplanıyor..."
python manage.py collectstatic --noinput

echo "Gunicorn başlatılıyor..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3