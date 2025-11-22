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

# collectstatic は USE_S3=False の場合のみ実行
ARG USE_S3
RUN if [ "$USE_S3" = "False" ]; then \
        poetry run python manage.py collectstatic --noinput; \
    fi

WORKDIR /app/src
EXPOSE 80
CMD ["poetry", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:80"]
