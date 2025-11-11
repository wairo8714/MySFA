# 1. ベースイメージ
FROM python:3.11-slim

# 2. 必要パッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 作業ディレクトリ作成
WORKDIR /app

# 4. Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

# 5. プロジェクト依存関係コピー
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

# 6. アプリケーションコードコピー
COPY . .

# 7. Nginx 設定をコンテナ内にコピー
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 8. start.sh をコンテナにコピーして実行権限付与
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 9. コンテナ起動コマンド
CMD ["/start.sh"]
