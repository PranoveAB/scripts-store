# src/static/executor.py
from datetime import datetime
import os
from loguru import logger
from src.static.package_manager import PackageManager
from src.database.db import SessionLocal
from src.service.models.db_model import Script
from src.utils.logger_config import get_run_logger

class ScriptExecutor:
    def __init__(self, script_name: str, project_name: str):
        self.script_name = script_name
        self.project_name = project_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.package_manager = PackageManager(project_name, script_name)
        self.log = logger.bind(
            log_type="execute",
            script_name=script_name,
            project_name=project_name
        )

    def execute(self, params: str = None) -> dict:
        """Execute a script with optional parameters"""
        self.log.info(f"Executing script {self.script_name} from project {self.project_name}")
        
        try:
            # Set up run-specific logging
            log_path = get_run_logger(self.project_name, self.script_name)
            
            # Check if script exists
            main_script = os.path.join(self.script_path, 'main.py')
            self.log.info(f"Main script path: {main_script}")
            
            if not os.path.exists(main_script):
                raise Exception(f"Main script not found at {main_script}")
            
            # Set up environment if needed
            if not self.package_manager.setup_environment():
                raise Exception("Failed to set up Python environment")
            
            # Run the script
            success, output, error = self.package_manager.run_in_environment(
                main_script,
                params
            )
            
            # Update script status in database
            self._update_script_status(success)
            
            # Log output to run-specific log
            run_log = logger.bind(
                log_type=self.project_name,
                script_name=self.script_name
            )
            
            if success:
                run_log.info(f"Script output:\n{output}")
            else:
                run_log.error(f"Script error:\n{error}")
                raise Exception(f"Script execution failed: {error}")
            
            return {
                "status": "success" if success else "failed",
                "output": output,
                "error": error,
                "log_file": log_path
            }
            
        except Exception as e:
            self.log.error(f"Error executing script: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup any resources"""
        self.package_manager.cleanup_environment()

    def _update_script_status(self, success: bool):
        """Update script status in database"""
        db = SessionLocal()
        try:
            script = db.query(Script).filter(
                Script.script_name == self.script_name,
                Script.project_name == self.project_name,
                Script.is_active == True
            ).first()
            
            if script:
                script.last_run = datetime.utcnow()
                script.last_status = 'success' if success else 'failed'
                script.run_count += 1
                # Set the env_name based on PackageManager's naming
                script.env_name = self.package_manager.get_venv_name()
                db.commit()
                self.log.info(f"Updated script status: {script.last_status}")
        finally:
            db.close()