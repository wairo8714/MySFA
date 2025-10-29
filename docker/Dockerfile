FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
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

# Create app user before collectstatic
RUN useradd --create-home --shell /bin/bash app

# Collect static files as root (collectstatic needs write permissions)
# データベース接続なしでcollectstaticを実行するため、環境変数を設定
ENV DATABASE_URL=""
RUN python manage.py collectstatic --noinput --clear || \
    (echo "Collectstatic warning: Continuing despite errors" && python manage.py collectstatic --noinput --clear --skip-checks)

# Set permissions and switch to app user
RUN chown -R app:app /app

USER app

EXPOSE 8000

# Use gunicorn for production
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
