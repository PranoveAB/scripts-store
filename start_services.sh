#!/bin/bash

# Start FastAPI application using poetry
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1