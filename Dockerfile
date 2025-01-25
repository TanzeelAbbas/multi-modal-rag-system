# Stage 1: Builder stage
FROM python:3.11-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    poppler-utils \
    openjdk-17-jdk \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies into user space
ENV PYTHONUSERBASE=/app/.local
RUN pip install --upgrade pip \
    && pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    openjdk-17-jre-headless \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user with fixed UID/GID
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g 1001 -m appuser && \
    mkdir -p /app/data/processed_documents && \
    chown -R appuser:appuser /app

# Copy Python dependencies from builder
COPY --from=builder /app/.local /home/appuser/.local

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app \
    DOCUMENT_STORAGE_PATH=/app/data/documents \
    PROCESSED_DOCUMENTS_PATH=/app/data/processed_documents

# Copy application code with proper permissions
COPY --chown=appuser:appuser . .

USER appuser

# Create data directories on startup
RUN mkdir -p ${DOCUMENT_STORAGE_PATH} ${PROCESSED_DOCUMENTS_PATH}

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]