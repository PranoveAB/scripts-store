# src/utils/logger_config.py
from loguru import logger
import sys
import os
from datetime import datetime

def setup_logging():
    # Remove default logger
    logger.remove()
    
    # Add executor logger
    logger.add(
        "/opt/logs/executor.log",
        filter=lambda record: record["extra"].get("log_type") == "execute",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[log_type]}: {message}",
        rotation="1 day",
        retention="7 days"
    )

    # Add scheduler logger
    logger.add(
        "/opt/logs/scheduler.log",
        filter=lambda record: record["extra"].get("log_type") == "schedule",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[log_type]}: {message}",
        rotation="1 day",
        retention="7 days"
    )

    # Add system logger
    logger.add(
        "/opt/logs/system.log",
        filter=lambda record: record["extra"].get("log_type") == "system",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[log_type]}: {message}",
        rotation="1 day",
        retention="7 days"
    )

def get_run_logger(project_name: str, script_name: str) -> str:
    """Create a log file for a specific script run"""
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    log_dir = f"/opt/logs/scripts-store-logs/{project_name}/{script_name}"
    os.makedirs(log_dir, exist_ok=True)
    log_path = f"{log_dir}/run_{timestamp}.log"
    return log_path