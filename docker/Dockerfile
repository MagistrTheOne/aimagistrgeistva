# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio libraries
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    alsa-utils \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # PostgreSQL client
    postgresql-client \
    # Redis client
    redis-tools \
    # Build tools
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy source code first
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/audio_cache && \
    chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.core.config; print('OK')" || exit 1

# Expose port
EXPOSE 8000

# Default command - Railway provides PORT variable
CMD ["sh", "-c", "uvicorn app.api.http.app:app --host 0.0.0.0 --port ${PORT:-8000} --reload"]
