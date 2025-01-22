from pydantic import BaseModel
from typing import Optional

class ScriptRegistration(BaseModel):
    script_name: str
    project_name: str
    repository: str
    branch: str = "main"
    commit_sha: str
    cron_expression: Optional[str] = None