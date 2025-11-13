#!/bin/bash
set -e

echo "🚀 Starting Gunicorn and Nginx..."

# srcディレクトリに移動
cd /app/src

# Gunicorn をバックグラウンドで起動
poetry run gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - &

# Gunicorn起動確認（5秒待機）
sleep 5

# Nginx をフォアグラウンドで起動
nginx -g "daemon off;"