#!/bin/bash
set -e

echo "🚀 Starting Gunicorn and Nginx..."

# PYTHONPATHを設定して、srcディレクトリをPythonパスに追加
export PYTHONPATH=/app/src:$PYTHONPATH

# Gunicorn をバックグラウンドで起動（/appから実行、src.configを指定）
poetry run gunicorn src.config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --chdir /app/src &

# Gunicorn起動確認（5秒待機）
sleep 5

# Nginx をフォアグラウンドで起動
nginx -g "daemon off;"