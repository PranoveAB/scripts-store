import subprocess
import os
from loguru import logger

class PackageManager:
    def __init__(self, project_name: str, script_name: str):
        self.project_name = project_name
        self.script_name = script_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.log = logger.bind(log_type="execute", script_name=script_name)

    def get_active_env_name(self) -> str:
        """Get the name of the currently active Poetry environment"""
        try:
            venv_path = os.path.join(self.script_path, '.venv')
            return '.venv' if os.path.exists(venv_path) else None
        except Exception as e:
            self.log.error(f"Error getting environment name: {str(e)}")
            return None

    def setup_environment(self) -> bool:
        """Set up Poetry virtual environment"""
        try:
            if not os.path.exists(os.path.join(self.script_path, 'pyproject.toml')):
                self.log.error("pyproject.toml not found")
                raise Exception("pyproject.toml not found")

            # Force Poetry to use an in-project virtual environment
            subprocess.run(
                ['/opt/.poetry/bin/poetry', 'config', 'virtualenvs.in-project', 'true'],
                cwd=self.script_path,
                check=True
            )

            # Remove any existing Poetry environment to prevent conflicts
            subprocess.run(
                ['/opt/.poetry/bin/poetry', 'env', 'remove', 'python'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )

            # Install dependencies in project-local virtualenv
            result = subprocess.run(
                ['/opt/.poetry/bin/poetry', 'install', '--no-root'],
                cwd=self.script_path,
                capture_output=True,
                text=True,
                check=True
            )
            self.log.info(f"Poetry install output: {result.stdout}")

            # Verify installation location
            env_info = subprocess.run(
                ['/opt/.poetry/bin/poetry', 'env', 'info'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )
            self.log.info(f"Poetry environment info:\n{env_info.stdout}")
            
            return True
        except Exception as e:
            self.log.error(f"Error setting up environment: {str(e)}")
            return False

    def run_in_environment(self, script_path: str, params: str = None) -> tuple[bool, str, str]:
        """Run a Python script in Poetry environment"""
        try:
            command = ['/opt/.poetry/bin/poetry', 'run', 'python', script_path]
            if params:
                command.extend(params.split())

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.script_path,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        except Exception as e:
            self.log.error(f"Error running script: {str(e)}")
            return False, "", str(e)

    def cleanup_environment(self):
        """Clean up virtual environment"""
        try:
            venv_path = os.path.join(self.script_path, '.venv')
            if os.path.exists(venv_path):
                import shutil
                shutil.rmtree(venv_path)
                self.log.info("Removed virtualenv directory")

            lock_file = os.path.join(self.script_path, 'poetry.lock')
            if os.path.exists(lock_file):
                os.remove(lock_file)
                self.log.info("Removed poetry.lock file")
        except Exception as e:
            self.log.error(f"Error cleaning up environment: {str(e)}")
