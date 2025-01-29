#!/bin/bash

# Function to cleanup runner on container stop
cleanup_runner() {
    echo "Cleaning up runner..."
    if [ -f /opt/actions-runner/config.sh ]; then
        cd /opt/actions-runner
        ./config.sh remove --token ${GITHUB_RUNNER_TOKEN}
    fi
    exit
}

# Setup cleanup trap
trap cleanup_runner SIGTERM SIGINT

# Configure GitHub Actions Runner
cd /opt/actions-runner
./config.sh \
    --unattended \
    --url https://github.com/${GITHUB_ORG} \
    --token ${GITHUB_RUNNER_TOKEN} \
    --name ${GITHUB_RUNNER_NAME:-$(hostname)} \
    --labels ${GITHUB_RUNNER_LABELS:-self-hosted} \
    --work ${RUNNER_WORK_DIR:-/opt/actions-runner/_work} \
    --replace
    

# Start the runner in background
./run.sh &

# Start FastAPI application
cd /opt
exec poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1