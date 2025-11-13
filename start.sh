#!/bin/bash
set -e

echo "🚀 Starting Gunicorn and Nginx..."

# PYTHONPATHを設定して、srcディレクトリをPythonパスに追加
export PYTHONPATH=/app/src:$PYTHONPATH

# 静的ファイルをS3にアップロード（本番環境では必ずS3を使用）
echo "📦 Collecting static files to S3..."
cd /app/src

# 環境変数を確認（S3使用時は必須）
if [ "${USE_S3:-false}" = "true" ]; then
    if [ -z "$AWS_STORAGE_BUCKET_NAME" ]; then
        echo "⚠️  AWS_STORAGE_BUCKET_NAME is not set, trying S3_BUCKET_NAME..."
        export AWS_STORAGE_BUCKET_NAME="${S3_BUCKET_NAME:-}"
    fi
    
    if [ -z "$AWS_STORAGE_BUCKET_NAME" ]; then
        echo "❌ AWS_STORAGE_BUCKET_NAME is not set. Cannot collect static files to S3."
        exit 1
    fi
    
    echo "Using S3 bucket: $AWS_STORAGE_BUCKET_NAME"
    
    # collectstaticを実行（S3にアップロード）
    poetry run python manage.py collectstatic --noinput --clear || {
        echo "⚠️  collectstatic failed, retrying with verbose output..."
        poetry run python manage.py collectstatic --noinput --clear --verbosity 2 || {
            echo "❌ collectstatic failed. This may cause static file 404 errors."
            echo "Continuing anyway, but static files may not be available..."
        }
    }
    
    echo "✅ Static files collection completed"
else
    echo "⚠️  USE_S3 is not set to 'true'. Static files will not be collected to S3."
    echo "⚠️  This may cause static file 404 errors in production."
fi

# Gunicorn をバックグラウンドで起動（/appから実行、src.configを指定）
poetry run gunicorn src.config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --chdir /app/src \
    --timeout 120 \
    --keep-alive 5 &

# Gunicorn起動確認（最大60秒待機）
echo "⏳ Waiting for Gunicorn to start..."
GUNICORN_READY=false
for i in {1..60}; do
    if curl -f -s http://127.0.0.1:8000/health/ > /dev/null 2>&1; then
        echo "✅ Gunicorn is ready! (attempt $i/60)"
        GUNICORN_READY=true
        break
    fi
    if [ $i -eq 1 ]; then
        echo "Waiting for Gunicorn to respond to health checks..."
    fi
    sleep 1
done

if [ "$GUNICORN_READY" = false ]; then
    echo "❌ Gunicorn failed to start within 60 seconds"
    echo "Checking Gunicorn process..."
    ps aux | grep gunicorn || echo "Gunicorn process not found"
    exit 1
fi

# Nginx をフォアグラウンドで起動
nginx -g "daemon off;"