# src/utils/validator.py
import os
import toml
from loguru import logger
from typing import Tuple
from src.static.package_manager import PackageManager
import subprocess

class ScriptValidator:
    def __init__(self, project_name: str, script_name: str):
        self.project_name = project_name
        self.script_name = script_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.log = logger.bind(log_type="validate", script_name=script_name)
        self.package_manager = PackageManager(project_name, script_name)

    def validate_structure(self) -> Tuple[bool, str]:
        """Validate the basic structure of the script package"""
        try:
            # Check required directories
            required_dirs = ['config', 'tests']
            for dir_name in required_dirs:
                dir_path = os.path.join(self.script_path, dir_name)
                if not os.path.isdir(dir_path):
                    return False, f"Missing required directory: {dir_name}"
            logger.bind(log_type="execute").info(f"Required directories exist for {self.project_name}/{self.script_name}")
            
            # Check required files
            required_files = ['pyproject.toml', 'main.py']
            for file_name in required_files:
                file_path = os.path.join(self.script_path, file_name)
                if not os.path.isfile(file_path):
                    return False, f"Missing required file: {file_name}"
            logger.bind(log_type="execute").info(f"Required files exist for {self.project_name}/{self.script_name}")

            logger.bind(log_type="execute").info(f"Structure validation passed for {self.project_name}/{self.script_name}")
            return True, "Structure validation passed"
        except Exception as e:
            return False, f"Structure validation error: {str(e)}"

    def validate_pyproject(self) -> Tuple[bool, str]:
        """Validate pyproject.toml content and structure"""
        try:
            pyproject_path = os.path.join(self.script_path, 'pyproject.toml')
            with open(pyproject_path, 'r') as f:
                config = toml.load(f)

            # Check required sections
            required_sections = [
                ('tool.poetry', "Missing [tool.poetry] section"),
                ('tool.poetry.dependencies', "Missing dependencies section"),
                ('build-system', "Missing [build-system] section")
            ]

            for section, error_msg in required_sections:
                parts = section.split('.')
                current = config
                for part in parts:
                    if part not in current:
                        return False, error_msg
                    current = current[part]

            # Verify Python version
            if 'python' not in config['tool']['poetry']['dependencies']:
                logger.bind(log_type="execute").info("Missing Python version in dependencies")
                return False, "Missing Python version in dependencies"

            return True, "pyproject.toml validation passed"
        except Exception as e:
            return False, f"pyproject.toml validation error: {str(e)}"

    def run_tests(self) -> Tuple[bool, str]:
        """Run unit tests"""
        try:
            self.log.info("Running tests")

            # Use PackageManager to set up environment
            if not self.package_manager.setup_environment():
                return False, "Failed to set up test environment"

            # Run tests using Poetry with PYTHONPATH set to include script directory
            env = os.environ.copy()
            env['PYTHONPATH'] = self.script_path  # Add script directory to Python path

            test_result = subprocess.run(
                ['poetry', 'run', 'pytest', 'tests/', '-v'],
                cwd=self.script_path,
                env=env,  # Pass the modified environment
                capture_output=True,
                text=True
            )

            if test_result.returncode != 0:
                self.log.error(f"Tests failed:\n{test_result.stdout}\n{test_result.stderr}")
                self.package_manager.cleanup_environment()
                return False, f"Tests failed:\n{test_result.stdout}\n{test_result.stderr}"
            
            self.log.info(f"All tests passed:\n{test_result.stdout}")
            return True, f"All tests passed:\n{test_result.stdout}"
            
        except Exception as e:
            self.log.error(f"Test execution error: {str(e)}")
            self.package_manager.cleanup_environment()
            return False, f"Test execution error: {str(e)}"

    def validate_all(self) -> Tuple[bool, str]:
        """Run all validations"""
        # Check structure
        structure_valid, structure_msg = self.validate_structure()
        if not structure_valid:
            return False, structure_msg

        # Check pyproject.toml
        pyproject_valid, pyproject_msg = self.validate_pyproject()
        if not pyproject_valid:
            return False, pyproject_msg

        # Run tests
        tests_passed, test_msg = self.run_tests()
        if not tests_passed:
            return False, test_msg

        return True, "All validations passed successfully"