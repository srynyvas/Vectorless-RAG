FROM python:3.11-slim

# Install system dependencies for parsers (pypdfium2, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (for Docker layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy entire project (includes config/, indexer/, retriever/, llm/, parsers/, backend/)
COPY . /app

# Create data directories
RUN mkdir -p /app/data/indices /app/data/uploads

# Set PYTHONPATH so imports work (e.g., from config.settings import settings)
ENV PYTHONPATH=/app

EXPOSE 8100

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
