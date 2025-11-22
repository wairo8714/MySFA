#!/bin/bash
set -e

echo "🚀 Preparing Django application..."

cd /app/src

# Run migrations on cold start
if [ ! -f /tmp/migrations_done ]; then
    echo "📦 Running database migrations..."
    poetry run python manage.py migrate --noinput || true
    touch /tmp/migrations_done
fi

# Always sync static assets (no-op if unchanged)
echo "🗂  Collecting static files..."
poetry run python manage.py collectstatic --noinput || true

echo "🔥 Starting Gunicorn..."
poetry run gunicorn src.config.wsgi:application \
    --bind 0.0.0.0:80 \
    --workers 1 \
    --access-logfile - \
    --error-logfile - \
    --chdir /app/src \
    --timeout 120 \
    --keep-alive 5

