#!/bin/bash
set -e

echo "🚀 Starting Gunicorn and Nginx..."

# Run migrations on startup (only once)
if [ ! -f /tmp/migrations_done ]; then
    echo "📦 Running database migrations..."
    cd /app/src
    poetry run python manage.py migrate --noinput || true
    touch /tmp/migrations_done
fi

# Start NGINX first
nginx

# Start Gunicorn
poetry run gunicorn src.config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 1 \
    --access-logfile - \
    --error-logfile - \
    --chdir /app/src \
    --timeout 120 \
    --keep-alive 5
