# ============================================================================
# GraphRAG Security Architect - Dockerfile
# ============================================================================
# Multi-stage build for optimized image size
#
# Build:   docker build -t graphrag-security .
# Run:     docker run -p 5000:5000 -v $(pwd)/data_store:/app/data_store graphrag-security
# ============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

LABEL maintainer="GraphRAG Security Architect"
LABEL description="Document-grounded security Q&A with knowledge graph support"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Create necessary directories
RUN mkdir -p /app/data_store \
    /app/chroma_graphrag_db \
    /app/guardrails \
    /app/templates \
    /app/static \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser *.py ./
COPY --chown=appuser:appuser guardrails/ ./guardrails/
COPY --chown=appuser:appuser templates/ ./templates/

# Copy static files if they exist
COPY --chown=appuser:appuser static/ ./static/ 2>/dev/null || true

# Copy configuration files
COPY --chown=appuser:appuser .env.example ./.env.example

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/config-status || exit 1

# Volumes for persistent data
VOLUME ["/app/data_store", "/app/chroma_graphrag_db"]

# Default environment variables
ENV FLASK_ENV=production
ENV ENABLE_KNOWLEDGE_GRAPH=false
ENV ENABLE_LLM_ENTITY_EXTRACTION=false
ENV LLM_MODEL=llama3.2
ENV EMBEDDING_MODEL=mxbai-embed-large

# Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["python", "graphrag_app.py"]
