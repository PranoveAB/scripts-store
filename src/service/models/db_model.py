# src/service/models/db_model.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from src.database.db import Base

class Script(Base):
    """
    SQLAlchemy model for scripts table.
    
    Attributes:
        id: Primary key
        script_name: Name of the script
        project_name: Project this script belongs to
        version: Current version of the script
        is_active: Whether this version is active
        created_at: When this version was created
        last_run: When script was last executed
        last_status: Status of last execution (success/failed)
        run_count: Number of times script has been executed
        cron_expression: Schedule for automatic execution
        params: Additional parameters for script execution
        env_name: Poetry environment name
    """
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    script_name = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    version = Column(String, nullable=False, default="1.0.0")
    is_active = Column(Boolean, default=True)
    env_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String, nullable=True)  # success, failed
    run_count = Column(Integer, default=0)
    cron_expression = Column(String, nullable=True)
    params = Column(Text, nullable=True)
    repository = Column(String, nullable=True)  # GitHub repository URL
    branch = Column(String, nullable=True, default="main")
    commit_sha = Column(String, nullable=True)  # Last processed commit SHA

    def __repr__(self):
        return f"<Script {self.script_name}:{self.version} ({self.project_name})>"