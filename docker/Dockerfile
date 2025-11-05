# ベースイメージ
FROM python:3.12-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 作業ディレクトリ作成
WORKDIR /app

# 必要パッケージインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libmariadb-dev-compat \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry インストール
RUN curl -sSL https://install.python-poetry.org | python3 -

# PATHに追加
ENV PATH="/root/.local/bin:$PATH"

# 依存関係コピーとインストール
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-root --without dev

# アプリケーションコピー
COPY . /app/

# Django collectstatic はコンテナ内で行う
RUN poetry run python manage.py collectstatic --noinput

# ポート開放
EXPOSE 8000

# 起動コマンド
CMD ["poetry", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
