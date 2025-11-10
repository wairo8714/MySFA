FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential pkg-config libmariadb-dev libmariadb-dev-compat curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

COPY . /app/

# collectstatic は USE_S3=True の場合に実行（S3へ静的ファイルを配置）
ARG USE_S3=False
RUN if [ "$USE_S3" = "True" ]; then \
        cd /app/src && \
        poetry run python manage.py collectstatic --noinput; \
    else \
        echo "Skipping collectstatic (USE_S3=$USE_S3)"; \
    fi

WORKDIR /app/src
EXPOSE 8000
CMD ["poetry", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]