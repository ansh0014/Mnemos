# Mnemos Dockerfile: Portable Learning Pipeline
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pipeline dependency definition
COPY Mnemo/pipeline/pyproject.toml /app/Mnemo/pipeline/

# Install dependencies (pypdf, fastapi, uvicorn for web serving, httpx)
RUN pip install --no-cache-dir \
    "pypdf>=4" \
    "fastapi>=0.110.0" \
    "uvicorn>=0.28.0" \
    "httpx>=0.27.0"

# Copy source code
COPY Mnemo/ /app/Mnemo/

# Install the pipeline package in editable mode
RUN pip install --no-cache-dir -e /app/Mnemo/pipeline

# Create data directories
RUN mkdir -p /data/books && mkdir -p /data/cache

ENV DATA_DIR=/data/books
ENV PORT=8080

EXPOSE 8080

# Run entrypoint
CMD ["python", "Mnemo/pipeline/nl_book.py", "--help"]
