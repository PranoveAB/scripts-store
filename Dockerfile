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
    POETRY_HOME="/root/.poetry" \
    POETRY_CACHE_DIR="/root/.cache/pypoetry" \
    POETRY_VIRTUALENVS_PATH="/root/.cache/pypoetry/virtualenvs" \
    POETRY_VIRTUALENVS_CREATE=true \
    PATH="/root/.poetry/bin:/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create all necessary directories
RUN mkdir -p /root/.poetry \
    && mkdir -p /root/.cache/pypoetry \
    && mkdir -p /root/.cache/pypoetry/virtualenvs \
    && mkdir -p /opt/scripts-store \
    && mkdir -p /opt/logs/scheduler \
    && mkdir -p /opt/logs/executor \
    && mkdir -p /opt/logs/scripts-store-logs \
    && chmod -R 777 /opt/logs \
    && chmod -R 777 /opt/scripts-store \
    && chmod -R 777 /root/.cache/pypoetry

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} \
    && poetry config virtualenvs.path ${POETRY_VIRTUALENVS_PATH} \
    && poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project false \
    && poetry config cache-dir ${POETRY_CACHE_DIR}

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY src/ src/
COPY start_services.sh ./

# Make start script executable
RUN chmod +x start_services.sh

# Install dependencies and ensure they're in PATH
RUN poetry install --no-root \
    && poetry env info > env_info.txt \
    && echo 'export PATH="$(poetry env info --path)/bin:$PATH"' >> ~/.bashrc

# Default command
CMD ["/bin/bash", "-c", "source ~/.bashrc && ./start_services.sh"]