# src/static/package_manager.py
import subprocess
import os
import hashlib
from loguru import logger
import shutil

class PackageManager:
    def __init__(self, project_name: str, script_name: str):
        self.project_name = project_name
        self.script_name = script_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.log = logger.bind(log_type="execute", script_name=script_name)
        
    def get_venv_name(self) -> str:
        """Generate a unique virtualenv name for the script"""
        sanitized_name = f"{self.project_name}-{self.script_name}".lower()
        hash_input = f"{self.script_path}-py3.9"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"{sanitized_name}-{hash_value}-py3.9"

    def virtualenv_exists(self) -> bool:
        """Check if virtualenv already exists"""
        result = subprocess.run(
            ['poetry', 'env', 'list'], 
            cwd=self.script_path,
            capture_output=True,
            text=True
        )
        return self.get_venv_name() in result.stdout
        
    def setup_environment(self) -> tuple[bool, str]:
        """Set up a Poetry virtual environment for the script."""
        try:
            if not os.path.exists(os.path.join(self.script_path, 'pyproject.toml')):
                raise Exception("pyproject.toml not found")

            venv_name = self.get_venv_name()
            
            # Check if virtualenv already exists
            if self.virtualenv_exists():
                self.log.info(f"Using existing virtualenv: {venv_name}")
                return True, venv_name

            # Create new virtualenv and install dependencies
            self.log.info("Installing dependencies in new virtualenv")
            result = subprocess.run(
                ['poetry', 'install', '--no-root'],
                cwd=self.script_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.log.info(f"Created new virtualenv: {venv_name}")
            return True, venv_name

        except subprocess.CalledProcessError as e:
            self.log.error(f"Poetry command failed: {e.stderr}")
            return False, ""
        except Exception as e:
            self.log.error(f"Error setting up environment: {str(e)}")
            return False, ""

    def run_in_environment(self, script_path: str, params: str = None) -> tuple[bool, str, str]:
        """Run a Python script in its Poetry environment"""
        try:
            # Get Poetry run command
            command = ['poetry', 'run', 'python', script_path]
            if params:
                command.extend(params.split())
            
            # Run with environment settings
            env = dict(os.environ)
            env['PYTHONUNBUFFERED'] = '1'
            
            # Run the script
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.script_path,
                env=env
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except Exception as e:
            self.log.error(f"Error running script: {str(e)}")
            return False, "", str(e)

    def cleanup_environment(self):
        """Clean up the Poetry virtual environment"""
        try:
            if self.virtualenv_exists():
                subprocess.run(
                    ['poetry', 'env', 'remove', self.get_venv_name()],
                    cwd=self.script_path
                )
                self.log.info(f"Cleaned up environment: {self.get_venv_name()}")
        except Exception as e:
            self.log.error(f"Error cleaning up environment: {str(e)}")