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
    PATH="/root/.poetry/bin:/root/.local/bin:$PATH" \
    RUNNER_VERSION=2.321.0 \
    RUNNER_ALLOW_RUNASROOT=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    build-essential \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.poetry \
    && mkdir -p /root/.cache/pypoetry \
    && mkdir -p /root/.cache/pypoetry/virtualenvs \
    && mkdir -p /opt/scripts-store \
    && mkdir -p /opt/logs \
    && mkdir -p /actions-runner \
    && chmod -R 777 /opt/logs \
    && chmod -R 777 /opt/scripts-store \
    && chmod -R 777 /root/.cache/pypoetry

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} \
    && poetry config virtualenvs.path ${POETRY_VIRTUALENVS_PATH} \
    && poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project false \
    && poetry config cache-dir ${POETRY_CACHE_DIR}

# Download and extract GitHub runner
RUN cd /actions-runner && \
    curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    ./bin/installdependencies.sh

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY src/ src/
COPY start_services.sh /start.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make start script executable
RUN chmod +x /start.sh

# Install dependencies and ensure they're in PATH
RUN poetry install --no-root \
    && poetry env info > env_info.txt \
    && echo 'export PATH="$(poetry env info --path)/bin:$PATH"' >> ~/.bashrc

# Expose FastAPI port
EXPOSE 8000

# Default command
CMD ["/start.sh"]