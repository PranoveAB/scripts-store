# src/service/models/register_model.py
from pydantic import BaseModel
from typing import Optional

class ScriptRegistration(BaseModel):
    """Model for script registration from GitHub workflow"""
    script_name: str
    project_name: str
    repository: str
    branch: str
    commit_sha: str
    cron_expression: Optional[str] = None