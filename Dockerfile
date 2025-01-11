# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /opt

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} \
    && ln -s /root/.local/share/pypoetry/venv/bin/poetry /usr/local/bin/poetry \
    && poetry config virtualenvs.in-project false

# Create necessary directories with proper permissions
RUN mkdir -p /opt/scripts-store \
    && mkdir -p /opt/logs/scheduler \
    && mkdir -p /opt/logs/executor \
    && mkdir -p /opt/logs/scripts-store-logs \
    && chmod -R 777 /opt/logs \
    && chmod -R 777 /opt/scripts-store

# Copy source code first
COPY src/ /opt/src/
COPY pyproject.toml poetry.lock start_services.sh ./

# Make start script executable
RUN chmod +x start_services.sh

# Install dependencies
RUN poetry install --no-root

# Default command
CMD ["./start_services.sh"]