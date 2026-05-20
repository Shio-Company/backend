#!/bin/sh

set -e

echo 'Migrating database...'
python manage.py migrate --noinput

echo 'Creating superuser...'
python manage.py initadmin

DJANGO_DEBUG=$(python manage.py shell -c "from django.conf import settings; print(settings.DEBUG)" 2>/dev/null)

if [ "$DJANGO_DEBUG" = "True" ]; then
    echo 'Seeding database...'
    python manage.py seed --reset
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi

python manage.py collectstatic --noinput
exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3