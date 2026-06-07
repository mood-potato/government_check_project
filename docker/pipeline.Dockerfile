FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY pipelines/ pipelines/
COPY data/ data/

CMD ["uv", "run", "python", "-m", "pipelines.run_pipeline"]
