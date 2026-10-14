#!/bin/sh
# Démarrage en conteneur (Railway, Render, Docker…) : prépare la base puis lance le serveur.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput -v0
python manage.py init_unipod
if [ "${DEMO:-false}" = "true" ]; then
  python manage.py donnees_demo
fi
# Compte administrateur créé une seule fois à partir des variables d'environnement
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.org}" 2>/dev/null \
    || echo "Compte administrateur déjà existant."
fi
exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --access-logfile -
