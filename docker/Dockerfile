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
RUN chmod +x /app/start.sh

WORKDIR /app
EXPOSE 80
CMD ["/app/start.sh"]
