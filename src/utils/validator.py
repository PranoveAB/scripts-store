# src/utils/validator.py
import os
import toml
import subprocess
from loguru import logger
from typing import Tuple

class ScriptValidator:
    def __init__(self, project_name: str, script_name: str):
        self.project_name = project_name
        self.script_name = script_name
        self.script_path = f"/opt/scripts-store/{project_name}/{script_name}"
        self.log = logger.bind(log_type="validate", script_name=script_name)

    def validate_structure(self) -> Tuple[bool, str]:
        """
        Validate the basic structure of the script package
        """
        try:
            # Check required directories
            required_dirs = ['config', 'tests']
            for dir_name in required_dirs:
                dir_path = os.path.join(self.script_path, dir_name)
                if not os.path.isdir(dir_path):
                    return False, f"Missing required directory: {dir_name}"

            # Check required files
            required_files = ['pyproject.toml', 'main.py']
            for file_name in required_files:
                file_path = os.path.join(self.script_path, file_name)
                if not os.path.isfile(file_path):
                    return False, f"Missing required file: {file_name}"

            return True, "Structure validation passed"
        except Exception as e:
            return False, f"Structure validation error: {str(e)}"

    def validate_pyproject(self) -> Tuple[bool, str]:
        """
        Validate pyproject.toml content and structure
        """
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

            # Check Python version specification
            if 'python' not in config['tool']['poetry']['dependencies']:
                return False, "Missing Python version specification"

            # Validate poetry configuration
            result = subprocess.run(
                ['poetry', 'check'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False, f"Poetry check failed: {result.stderr}"

            return True, "pyproject.toml validation passed"
        except Exception as e:
            return False, f"pyproject.toml validation error: {str(e)}"

    def run_tests(self) -> Tuple[bool, str]:
        """
        Run unit tests in the tests directory
        """
        try:
            self.log.info("Setting up test environment")
            
            # Install dependencies including dev dependencies
            install_result = subprocess.run(
                ['poetry', 'install'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )
            if install_result.returncode != 0:
                return False, f"Failed to install dependencies: {install_result.stderr}"

            self.log.info("Running tests")
            # Run pytest
            test_result = subprocess.run(
                ['poetry', 'run', 'python', '-m', 'pytest', 'tests/', '-v'],
                cwd=self.script_path,
                capture_output=True,
                text=True
            )

            if test_result.returncode != 0:
                return False, f"Tests failed:\n{test_result.stdout}\n{test_result.stderr}"

            return True, f"All tests passed:\n{test_result.stdout}"
        except Exception as e:
            return False, f"Test execution error: {str(e)}"

    def validate_all(self) -> Tuple[bool, str]:
        """
        Run all validations
        """
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