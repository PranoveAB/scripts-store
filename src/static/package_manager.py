# src/static/package_manager.py
import subprocess
import os
from loguru import logger
import shutil

class PackageManager:
    POETRY_CACHE_DIR = "/root/.cache/pypoetry"
    POETRY_VENV_PATH = "/root/.cache/pypoetry/virtualenvs"

    def __init__(self, project_name: str, script_name: str):
        self.project_name = project_name
        self.script_name = script_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.log = logger.bind(log_type="execute", script_name=script_name)

    def get_active_env_name(self) -> str:
        """Get the name of the currently active Poetry environment"""
        try:
            result = subprocess.run(
                ['poetry', 'env', 'list', '--full-path'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )
            # Look for the line with the (Activated) marker
            for line in result.stdout.split('\n'):
                if '(Activated)' in line:
                    # Extract just the env name from the path
                    path = line.split()[0]
                    return os.path.basename(path)
            return None
        except Exception:
            return None

    def setup_environment(self) -> bool:
        """Set up Poetry virtual environment"""
        try:
            if not os.path.exists(os.path.join(self.script_path, 'pyproject.toml')):
                raise Exception("pyproject.toml not found")

            # Verify Poetry configuration
            subprocess.run(
                ['poetry', 'config', 'virtualenvs.path', self.POETRY_VENV_PATH],
                cwd=self.script_path,
                check=True
            )

            # Install dependencies
            self.log.info(f"Installing dependencies in {self.script_path}")
            result = subprocess.run(
                ['poetry', 'install', '--no-root'],
                cwd=self.script_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            self.log.info(f"Poetry install output: {result.stdout}")
            return True

        except subprocess.CalledProcessError as e:
            self.log.error(f"Poetry command failed: {e.stderr}")
            return False
        except Exception as e:
            self.log.error(f"Error setting up environment: {str(e)}")
            return False

    def run_in_environment(self, script_path: str, params: str = None) -> tuple[bool, str, str]:
        """Run a Python script in Poetry environment"""
        try:
            command = ['poetry', 'run', 'python', script_path]
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
        """Clean up Poetry virtual environment and lock file"""
        try:
            # Remove virtualenv if it exists
            env_name = self.get_active_env_name()
            if env_name:
                subprocess.run(
                    ['poetry', 'env', 'remove', env_name],
                    cwd=self.script_path
                )
                self.log.info(f"Cleaned up environment: {env_name}")
            
            # Remove poetry.lock file
            lock_file = os.path.join(self.script_path, 'poetry.lock')
            if os.path.exists(lock_file):
                os.remove(lock_file)
                self.log.info("Removed poetry.lock file")

        except Exception as e:
            self.log.error(f"Error cleaning up environment: {str(e)}")