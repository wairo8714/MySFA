#!/bin/bash
set -e

# Gunicorn をバックグラウンドで起動
poetry run gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 &

# Nginx をフォアグラウンドで起動
nginx -g "daemon off;"
