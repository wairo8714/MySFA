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
    --chdir /app/src \
    --timeout 120 \
    --keep-alive 5 &

# Gunicorn起動確認（最大30秒待機）
echo "⏳ Waiting for Gunicorn to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health/ > /dev/null 2>&1; then
        echo "✅ Gunicorn is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Gunicorn failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Nginx をフォアグラウンドで起動
nginx -g "daemon off;"