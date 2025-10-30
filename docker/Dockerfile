FROM python:3.12-slim

# 必要パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Poetry インストール
RUN pip install --no-cache-dir poetry

# プロジェクトファイルコピー
COPY pyproject.toml poetry.lock* /app/
COPY src/ /app/

# Poetry 設定（仮想環境は作らない）
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi

# アプリ用ユーザー作成
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Gunicorn 起動 (collectstatic は S3 使用前提なら削除可)
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
