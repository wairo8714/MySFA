# ベースイメージ
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod 

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential pkg-config libmariadb-dev libmariadb-dev-compat curl nginx \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

COPY . /app/

# 環境に応じて nginx.conf をコピー
RUN mkdir -p /etc/nginx/conf.d
RUN if [ "$ENVIRONMENT" = "prod" ]; then \
        cp nginx/nginx.prod.conf /etc/nginx/conf.d/default.conf; \
    else \
        cp nginx/nginx.dev.conf /etc/nginx/conf.d/default.conf; \
    fi

WORKDIR /app/src
EXPOSE 8000

CMD ["/app/start.sh"]
