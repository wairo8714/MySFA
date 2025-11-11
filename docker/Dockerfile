# ベースイメージ
FROM python:3.12-slim

# 環境変数
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# システム依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential pkg-config libmariadb-dev libmariadb-dev-compat curl nginx \
    && rm -rf /var/lib/apt/lists/*

# Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

# アプリ依存関係インストール
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

# アプリケーションコードをコピー
COPY . /app/

# start.sh を追加
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 作業ディレクトリ
WORKDIR /app/src

# ポート 80 を開放
EXPOSE 80

# コンテナ起動時に start.sh を実行
CMD ["/app/start.sh"]
