FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY backend/ backend/

CMD ["uv", "run", "python", "-c", "from backend.modules.pipeline.schedule_to_pdf_pipeline import ScheduleToPDFPipeline; from backend.modules.pipeline.pdf_to_speech_pipeline import PDFToSpeechPipeline; from backend.modules.pipeline.vectorize_pipeline import VectorizePipeline; ScheduleToPDFPipeline().run(); PDFToSpeechPipeline().run(); VectorizePipeline().run()"]
