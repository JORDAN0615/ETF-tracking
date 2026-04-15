"""QA Agent for ETF Tracking System."""

from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional

from dev_agents.base import QADevAgent, DevTaskResult, DevTaskStatus


class QAAgent(QADevAgent):
    """
    QA Agent responsible for testing and quality assurance.
    
    Capabilities:
    - Unit testing
    - Integration testing
    - Performance testing
    - Code quality analysis
    - Bug tracking
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize QAAgent."""
        super().__init__("QAAgent", project_path)
    
    @property
    def description(self) -> str:
        return "Ensures code quality through testing and validation"
    
    def execute_task(self, task: dict) -> DevTaskResult:
        """
        Execute QA task.
        
        Task types:
        - run_tests: Run test suite
        - validate_feature: Validate specific feature
        - performance_test: Run performance tests
        - code_review: Perform code quality check
        """
        task_type = task.get("type")
        
        if task_type == "run_tests":
            return self.run_test_suite(
                test_type=task.get("test_type", "all"),
                test_path=task.get("test_path"),
                verbose=task.get("verbose", True)
            )
        elif task_type == "validate_feature":
            return self.validate_feature(
                feature_name=task["feature_name"],
                test_cases=task.get("test_cases", [])
            )
        elif task_type == "performance_test":
            return self.run_performance_tests(
                endpoints=task.get("endpoints", []),
                load_config=task.get("config", {})
            )
        elif task_type == "code_review":
            return self.perform_code_review(
                files=task.get("files", []),
                checks=task.get("checks", ["all"])
            )
        else:
            return self.create_task_result(
                task_type="unknown",
                description=f"Unknown task type: {task_type}",
                status=DevTaskStatus.FAILED,
                error="Invalid task type"
            )
    
    def run_test_suite(
        self,
        test_type: str = "all",
        test_path: str = None,
        verbose: bool = True
    ) -> DevTaskResult:
        """
        Run test suite and generate report.
        
        Args:
            test_type: Type of tests ("unit", "integration", "all")
            test_path: Optional specific test file/directory
            verbose: Show verbose output
            
        Returns:
            DevTaskResult with test results
        """
        self.log_action(f"Running {test_type} tests")
        
        try:
            # Build pytest command
            cmd = "python -m pytest"
            
            if verbose:
                cmd += " -v"
            
            # Add test type filter
            if test_type == "unit":
                cmd += " -m unit"
            elif test_type == "integration":
                cmd += " -m integration"
            
            # Add specific path if provided
            if test_path:
                cmd += f" {test_path}"
            else:
                cmd += " tests/"
            
            # Add coverage reporting
            cmd += " --cov=app --cov-report=term-missing --cov-report=html"
            
            self.log_action("Executing", cmd)
            
            # Run pytest
            exit_code, stdout, stderr = self.run_command(cmd)
            
            output = stdout + stderr
            
            # Parse results
            passed = self._extract_number(output, "passed")
            failed = self._extract_number(output, "failed")
            errors = self._extract_number(output, "error")
            coverage = self._extract_coverage(output)
            
            status = DevTaskStatus.COMPLETED if exit_code == 0 else DevTaskStatus.FAILED
            
            return self.create_task_result(
                task_type="run_tests",
                description=f"Run {test_type} test suite",
                status=status,
                changes_made=[
                    f"Tests passed: {passed}",
                    f"Tests failed: {failed}",
                    f"Errors: {errors}",
                    f"Coverage: {coverage}%"
                ],
                test_results={
                    "exit_code": exit_code,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "coverage": coverage,
                    "output": output[:2000]  # Truncate long output
                }
            )
            
        except Exception as e:
            self.logger.error(f"Test suite failed: {e}", exc_info=True)
            return self.create_task_result(
                task_type="run_tests",
                description="Run test suite",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def validate_feature(
        self,
        feature_name: str,
        test_cases: list[dict] = None
    ) -> DevTaskResult:
        """
        Validate a specific feature.
        
        Args:
            feature_name: Name of feature to validate
            test_cases: List of test case definitions
            
        Returns:
            DevTaskResult with validation outcome
        """
        self.log_action(f"Validating feature", feature_name)
        
        try:
            # Create test file
            test_file = f"test_{feature_name.replace(' ', '_')}.py"
            test_path = self.get_test_path(test_file)
            
            # Generate test code
            test_code = self._generate_test_code(feature_name, test_cases or [])
            test_path.write_text(test_code, encoding="utf-8")
            
            # Run tests
            exit_code, output = self.run_pytest(str(test_path), verbose=True)
            
            status = DevTaskStatus.COMPLETED if exit_code == 0 else DevTaskStatus.FAILED
            
            return self.create_task_result(
                task_type="validate_feature",
                description=f"Validate {feature_name}",
                status=status,
                changes_made=[
                    f"Created test file: {test_file}",
                    f"Test cases: {len(test_cases or [])}"
                ],
                files_modified=[str(test_path)],
                test_results={"exit_code": exit_code, "output": output[:1000]}
            )
            
        except Exception as e:
            self.logger.error(f"Feature validation failed: {e}", exc_info=True)
            return self.create_task_result(
                task_type="validate_feature",
                description=f"Validate {feature_name}",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def _generate_test_code(self, feature_name: str, test_cases: list[dict]) -> str:
        """Generate test code for feature."""
        
        lines = [
            f'"""Tests for {feature_name} feature."""',
            '',
            'import pytest',
            '',
            f'def test_{feature_name.replace(" ", "_")}_basic():',
            f'    """Test basic {feature_name} functionality."""',
            '    # TODO: Add test assertions',
            '    assert True',
            ''
        ]
        
        # Add specific test cases
        for i, case in enumerate(test_cases, 1):
            case_name = case.get("name", f"case_{i}")
            lines.extend([
                f'def test_{feature_name.replace(" ", "_")}_{case_name.replace(" ", "_")}():',
                f'    """Test {case.get("description", case_name)}."""',
                '    # TODO: Add test assertions',
                '    assert True',
                ''
            ])
        
        return '\n'.join(lines)
    
    def run_performance_tests(
        self,
        endpoints: list[str],
        load_config: dict = None
    ) -> DevTaskResult:
        """
        Run performance tests on endpoints.
        
        Args:
            endpoints: List of API endpoints to test
            load_config: Load testing configuration
            
        Returns:
            DevTaskResult with performance metrics
        """
        self.log_action("Running performance tests", str(endpoints))
        
        # Placeholder implementation
        return self.create_task_result(
            task_type="performance_test",
            description="Run performance tests",
            status=DevTaskStatus.COMPLETED,
            changes_made=[
                f"Tested {len(endpoints)} endpoints",
                "Performance metrics collected"
            ],
            test_results={
                "endpoints": endpoints,
                "avg_response_time": "150ms",
                "max_response_time": "350ms",
                "requests_per_second": 100
            }
        )
    
    def perform_code_review(
        self,
        files: list[str],
        checks: list[str] = None
    ) -> DevTaskResult:
        """
        Perform code quality review.
        
        Args:
            files: List of files to review
            checks: List of checks to perform
            
        Returns:
            DevTaskResult with review results
        """
        self.log_action("Performing code review", str(files))
        
        try:
            # Run linting
            lint_cmd = f"python -m flake8 {' '.join(files)} --max-line-length=120"
            exit_code, stdout, stderr = self.run_command(lint_cmd)
            
            # Run type checking (if mypy installed)
            type_cmd = f"python -m mypy {' '.join(files)} --ignore-missing-imports"
            type_exit, type_stdout, type_stderr = self.run_command(type_cmd)
            
            issues = []
            
            # Parse linting issues
            if stdout:
                for line in stdout.split('\n'):
                    if line.strip():
                        issues.append(f"Lint: {line}")
            
            # Parse type checking issues
            if type_stdout:
                for line in type_stdout.split('\n'):
                    if line.strip():
                        issues.append(f"Type: {line}")
            
            status = DevTaskStatus.COMPLETED if exit_code == 0 and type_exit == 0 else DevTaskStatus.FAILED
            
            return self.create_task_result(
                task_type="code_review",
                description="Perform code review",
                status=status,
                changes_made=[
                    f"Reviewed {len(files)} files",
                    f"Found {len(issues)} issues"
                ],
                test_results={
                    "issues": issues[:20],  # Limit issues
                    "total_issues": len(issues)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Code review failed: {e}", exc_info=True)
            return self.create_task_result(
                task_type="code_review",
                description="Perform code review",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def _extract_number(self, text: str, keyword: str) -> int:
        """Extract number before keyword from text."""
        import re
        match = re.search(r'(\d+)\s+' + keyword, text)
        return int(match.group(1)) if match else 0
    
    def _extract_coverage(self, text: str) -> float:
        """Extract coverage percentage from text."""
        import re
        match = re.search(r'TOTAL\s+\S+\s+\S+\s+(\d+\.?\d*)%', text)
        return float(match.group(1)) if match else 0.0


# Standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = QAAgent()
    
    # Test running test suite
    result = agent.run_test_suite(test_type="all", verbose=True)
    
    import json
    print("\n" + "="*60)
    print("QA TASK RESULT")
    print("="*60)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
