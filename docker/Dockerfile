FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

#pyprojectを使用するならばpip install -e .[dev]ではなくこっち
RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* /app/
COPY src/ /app/

RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set permissions and switch to app user
RUN chown -R app:app /app

USER app

EXPOSE 8000

# Use gunicorn for production
# collectstaticはEC2上でコンテナ起動時に実行（イメージサイズを小さくするため）
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
