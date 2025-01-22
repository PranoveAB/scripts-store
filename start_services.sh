#!/bin/bash

set -e  # Exit on error

# Check required environment variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_ACCOUNT" ]; then
    echo "Error: GITHUB_TOKEN and GITHUB_ACCOUNT must be set"
    exit 1
fi

# Configure the GitHub runner
if [ ! -f /actions-runner/.runner ]; then
    cd /actions-runner
    
    echo "Configuring GitHub runner for organization: ${GITHUB_ACCOUNT}"
    
    # Organization URL format for Scripts-Store
    REGISTRATION_URL="https://github.com/${GITHUB_ACCOUNT}"
    
    ./config.sh \
        --url "${REGISTRATION_URL}" \
        --token "${GITHUB_TOKEN}" \
        --name "${RUNNER_NAME:-script-service-runner}" \
        --labels "script-service,python" \
        --unattended \
        --replace

    if [ $? -eq 0 ]; then
        echo "Runner configured successfully for organization: ${GITHUB_ACCOUNT}"
    else
        echo "Failed to configure runner"
        exit 1
    fi
fi

# Create necessary directories
mkdir -p /opt/scripts-store
mkdir -p /opt/logs/scheduler
mkdir -p /opt/logs/executor
mkdir -p /opt/logs/scripts-store-logs
mkdir -p /root/.cache/pypoetry/virtualenvs

# Set permissions
chmod -R 777 /opt/logs
chmod -R 777 /opt/scripts-store
chmod -R 777 /root/.cache/pypoetry

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf