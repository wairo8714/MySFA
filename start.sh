#!/bin/bash
set -e

# Gunicorn 起動（バックグラウンド）
poetry run gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 &

# Nginx 起動（フォアグラウンド）
nginx -g "daemon off;"
