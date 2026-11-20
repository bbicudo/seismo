# Imagem da API. Também roda as migrações (serviço "migrate" do compose).
FROM python:3.12.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY src/ ./src/
ENV PYTHONPATH=/app/src

RUN useradd --system --uid 10001 seismo
USER seismo

EXPOSE 8000
CMD ["uvicorn", "seismo_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--root-path", "/api"]
