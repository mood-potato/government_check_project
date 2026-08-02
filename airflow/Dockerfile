FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AIRFLOW_HOME=/opt/airflow \
    UV_HTTP_TIMEOUT=1800 \
    UV_HTTP_RETRIES=10

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project
COPY pipelines/ pipelines/
COPY data/ data/
COPY airflow/dags/ /app/airflow/dags/

EXPOSE 8080
CMD ["uv", "run", "airflow", "standalone"]
