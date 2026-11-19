# Multi-arch: só imagem base oficial e wheels do PyPI (todas com aarch64 e x86_64).
FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
ENV PYTHONPATH=/app/src

RUN useradd --system --uid 10001 seismo
USER seismo

CMD ["python", "-m", "seismo_collector"]
