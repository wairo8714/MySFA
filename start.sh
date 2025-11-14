#!/bin/bash
set -e

echo "🚀 Starting Gunicorn and Nginx..."

# Start NGINX first
nginx

# Start Gunicorn
poetry run gunicorn src.config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --chdir /app/src \
    --timeout 120 \
    --keep-alive 5
