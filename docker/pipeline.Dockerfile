FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY pipelines/ pipelines/
COPY data/ data/

CMD ["uv", "run", "python", "-c", "from pipelines.schedule_to_pdf_pipeline import ScheduleToPDFPipeline; from pipelines.pdf_to_speech_pipeline import PDFToSpeechPipeline; from pipelines.vectorize_pipeline import VectorizePipeline; ScheduleToPDFPipeline().run(); PDFToSpeechPipeline().run(); VectorizePipeline().run()"]
