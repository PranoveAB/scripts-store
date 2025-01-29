# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /opt

# Create a non-root user for the runner
RUN useradd -m -d /home/runner runner && \
    adduser runner sudo

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1 \
    POETRY_HOME="/opt/.poetry" \
    POETRY_CACHE_DIR="/opt/.cache/pypoetry" \
    POETRY_VIRTUALENVS_PATH="/opt/.cache/pypoetry/virtualenvs" \
    POETRY_VIRTUALENVS_CREATE=true \
    PATH="/opt/.poetry/bin:/opt/.local/bin:$PATH" \
    RUNNER_VERSION=2.322.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    build-essential \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories with appropriate permissions
RUN mkdir -p /opt/.poetry \
    && mkdir -p /opt/.cache/pypoetry \
    && mkdir -p /opt/.cache/pypoetry/virtualenvs \
    && mkdir -p /opt/scripts-store \
    && mkdir -p /opt/logs \
    && mkdir -p /opt/actions-runner \
    && mkdir -p /opt/data \
    && chmod -R 777 /opt/scripts-store \
    && chmod -R 777 /opt/logs \
    && chmod -R 777 /opt/data \
    && chmod -R 777 /opt/actions-runner \
    && chown -R runner:runner /opt/.poetry \
    && chown -R runner:runner /opt/.cache \
    && chown -R runner:runner /opt/scripts-store \
    && chown -R runner:runner /opt/logs \
    && chown -R runner:runner /opt/actions-runner \
    && chown -R runner:runner /opt/data \
    && echo "runner ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER runner

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION} \
    && poetry config virtualenvs.path ${POETRY_VIRTUALENVS_PATH} \
    && poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project false \
    && poetry config cache-dir ${POETRY_CACHE_DIR}

# Download and extract GitHub runner
WORKDIR /opt/actions-runner
RUN curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Install runner dependencies (this needs to run as root)
USER root
RUN ./bin/installdependencies.sh
USER runner

# Return to main directory
WORKDIR /opt

# Copy project files with correct ownership
COPY --chown=runner:runner pyproject.toml poetry.lock ./
COPY --chown=runner:runner src/ src/

# Install dependencies
RUN poetry install --no-root

# Copy and prepare startup script
COPY --chown=runner:runner start_services.sh ./
RUN chmod +x start_services.sh

EXPOSE 8000

CMD ["./start_services.sh"]