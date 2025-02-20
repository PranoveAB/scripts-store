# Scripts Store - Script Automation Service

## Overview
The Scripts Store is a service that automates deployment and scheduling of Python scripts from GitHub repositories within an organization. It features:
- Automatic script deployment from GitHub pushes
- Isolated Poetry environments for each script
- Cron-based scheduling using APScheduler
- Automatic version management
- Script validation and testing

## Architecture
The service consists of:
1. FastAPI backend service for:
   - Managing script uploads
   - Handling GitHub webhooks
   - Managing script schedules
   - Running scripts in isolated environments
2. Poetry for dependency and environment management
3. SQLite database for script metadata and versions
4. APScheduler for cron-based script execution

## Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd scripts-store
```

2. Set up environment variables:
```bash
cp .env.example .env
# Required variables:
# - GITHUB_ORG: Your GitHub organization name
# - GITHUB_WEBHOOK_SECRET: For webhook validation
# - SCRIPTS_STORE_PATH: Path for script storage
```

3. Start the service:
```bash
docker-compose up --build
```

## Creating Scripts
Your script repository should contain:
- `main.py` - Script entry point
- `pyproject.toml` - Poetry dependencies
- `config/` - Configuration directory
  - `schedule.txt` - Cron expression for scheduling
- `tests/` - Test files for validation

## GitHub Integration
1. Configure GitHub webhook:
   - URL: `https://your-service/api/webhook/github`
   - Content type: `application/json`
   - Events: Push events

2. When you push to main:
   - Service receives webhook
   - Validates script structure
   - Creates Poetry environment
   - Schedules execution based on cron expression

## API Endpoints
- POST `/api/webhook/github` - Handle GitHub webhooks
- POST `/api/scripts/upload` - Manual script upload
- GET `/api/scripts` - List registered scripts
- POST `/api/scripts/{script_name}/run` - Run script immediately
- GET `/api/scripts/{script_name}/status` - Get script status

## Development
Built with:
- Python 3.9
- FastAPI & Uvicorn
- Poetry for dependency management
- SQLAlchemy with SQLite
- APScheduler for task scheduling
- Loguru for logging
