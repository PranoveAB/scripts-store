# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.db import engine, Base
from src.service.router import router
from src.static.scheduler import scheduler
from src.utils.logger_config import setup_logging
from loguru import logger

# Initialize FastAPI app
app = FastAPI(
    title="Script Store API",
    description="API for managing and scheduling script execution",
    version="1.0.0"
)

# Set up logging
setup_logging()
log = logger.bind(log_type="system")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include router
app.include_router(router, prefix="/api", tags=["scripts"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    log.info("Starting Script Store API")
    scheduler.start()
    log.info("Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    log.info("Shutting down Script Store API")
    scheduler.stop()
    log.info("Scheduler stopped")

# Root endpoint for health check
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Script Store API",
        "version": "1.0.0"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )