# ベースイメージ
FROM python:3.12-slim

# Python の基本環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod

WORKDIR /app

# 必要なシステムパッケージのインストール
# → MySQLクライアント関連, nginx, curl, build-essential など
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libmariadb-dev \
    libmariadb-dev-compat \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Poetry のインストール
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

# Poetry の依存関係インストール
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

# アプリケーションコードをコピー
COPY . /app/

# Nginx 設定ファイルをコンテナに配置
RUN mkdir -p /etc/nginx/conf.d
COPY nginx/nginx.prod.conf /etc/nginx/conf.d/default.conf

# 起動スクリプトに実行権限を付与
RUN chmod +x /app/start.sh

# ポート80を公開 (NginxがListen)
EXPOSE 80

# 最終実行コマンド
CMD ["/app/start.sh"]
