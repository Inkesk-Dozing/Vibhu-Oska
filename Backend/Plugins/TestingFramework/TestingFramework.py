"""
Vibhu-Oska AI-OS — TestingFramework Plugin
Autonomous code testing: runs pytest on AI-generated code snippets
in an isolated subprocess, returns pass/fail + error traces.
Forms the backbone of the closed-loop self-correction cycle.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class TestResult:
    """Result of a test run."""
    __slots__ = ("passed", "failed", "errors", "output", "duration_ms")

    def __init__(self, passed: int, failed: int, errors: list[str], output: str, duration_ms: int) -> None:
        self.passed      = passed
        self.failed      = failed
        self.errors      = errors
        self.output      = output
        self.duration_ms = duration_ms

    @property
    def success(self) -> bool:
        return self.failed == 0 and len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success":     self.success,
            "passed":      self.passed,
            "failed":      self.failed,
            "errors":      self.errors,
            "output":      self.output[-2000:],  # Cap output
            "duration_ms": self.duration_ms,
        }


class TestingFramework(BaseService):
    """
    Autonomous testing plugin — runs code in an isolated subprocess.

    Actions:
      - run_tests(code, test_code, language): Run tests against generated code
      - run_existing(test_path): Run existing test files in the Tests/ directory
      - validate_syntax(code, language): Quick AST syntax validation
    """

    TIMEOUT_SECS = 30  # Max time per test run

    def __init__(self) -> None:
        self._initialized = False
        self._python_executable = sys.executable
        self._log = Logger.get("TestingFramework")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="testing_framework",
            version="0.1.0",
            description="Autonomous code testing for self-correction loop (pytest + subprocess)",
            capabilities=["run_tests", "run_existing", "validate_syntax"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return
        # Verify pytest is available
        result = await asyncio.to_thread(
            subprocess.run,
            [self._python_executable, "-m", "pytest", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            self._log.info("TestingFramework ready", pytest_version=result.stdout.strip())
        else:
            self._log.warning("pytest not found — install with: pip install pytest pytest-asyncio")
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "run_tests":
            return (await self.run_tests(
                code=kwargs["code"],
                test_code=kwargs.get("test_code", ""),
                language=kwargs.get("language", "python"),
            )).to_dict()
        elif action == "run_existing":
            return (await self.run_existing(
                test_path=kwargs["test_path"]
            )).to_dict()
        elif action == "validate_syntax":
            return self.validate_syntax(
                code=kwargs["code"],
                language=kwargs.get("language", "python"),
            )
        else:
            raise ValueError(f"Unknown TestingFramework action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Run Tests (AI-Generated Code)
    # ══════════════════════════════════════════════════════════════

    async def run_tests(
        self,
        code: str,
        test_code: str,
        language: str = "python",
    ) -> TestResult:
        """
        Write code + test_code to temp files, run pytest, return result.
        If test_code is empty, generates a minimal syntax-check test.
        """
        if language != "python":
            return TestResult(0, 1, [f"Language '{language}' not yet supported"], "", 0)

        # Auto-generate a basic smoke test if no test code provided
        if not test_code.strip():
            test_code = textwrap.dedent("""
                import importlib, sys, types

                def test_syntax_and_import():
                    \"\"\"Verify the generated code has no syntax errors.\"\"\"
                    import ast
                    try:
                        ast.parse(open('_vibhu_generated_code.py').read())
                    except SyntaxError as e:
                        raise AssertionError(f'Syntax error: {e}')
            """)

        return await asyncio.to_thread(self._run_subprocess, code, test_code)

    def _run_subprocess(self, code: str, test_code: str) -> TestResult:
        import time
        start = time.time()

        with tempfile.TemporaryDirectory(prefix="vibhu_test_") as tmpdir:
            code_file = Path(tmpdir) / "_vibhu_generated_code.py"
            test_file = Path(tmpdir) / "test_generated.py"
            code_file.write_text(code, encoding="utf-8")
            test_file.write_text(test_code, encoding="utf-8")

            # Load configuration
            config = ConfigLoader.load()
            sandbox_enabled = config.get("sandbox.enabled", False)
            
            # Check if Docker is available
            docker_available = False
            if sandbox_enabled:
                try:
                    res = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=3)
                    docker_available = (res.returncode == 0)
                except Exception:
                    pass

            if sandbox_enabled and docker_available:
                self._log.info("Running test in Docker sandbox...")
                image = config.get("sandbox.docker_image", "python:3.11-slim")
                mem_limit = config.get("sandbox.memory_limit", "4g")
                cpu_limit = config.get("sandbox.cpu_limit", "2.0")
                timeout_secs = config.get("sandbox.timeout_seconds", self.TIMEOUT_SECS)
                
                # Resolve directory path in volume mount compatibility
                host_path = str(Path(tmpdir).resolve()).replace("\\", "/")
                
                # Build command: docker run --rm -v <tmpdir>:/app -w /app --network none -m <mem> --cpus <cpu> <image> ...
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{host_path}:/app",
                    "-w", "/app",
                    "--network", "none",
                    "-m", mem_limit,
                    "--cpus", cpu_limit,
                    image,
                    "pytest", "test_generated.py", "-v", "--tb=short", "--no-header", "-q"
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_secs
                    )
                except subprocess.TimeoutExpired:
                    elapsed = int((time.time() - start) * 1000)
                    return TestResult(0, 1, [f"Test timed out inside Docker after {timeout_secs}s"], "", elapsed)
                except Exception as ex:
                    # Fallback log and switch back to local subprocess
                    self._log.warning("Docker sandbox failed to execute, falling back to local host execution", error=str(ex))
                    sandbox_enabled = False  # Triggers local fallback below
            
            if not sandbox_enabled or not docker_available:
                # Local host subprocess execution
                try:
                    result = subprocess.run(
                        [self._python_executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header", "-q"],
                        capture_output=True,
                        text=True,
                        timeout=self.TIMEOUT_SECS,
                        cwd=tmpdir,
                    )
                except subprocess.TimeoutExpired:
                    elapsed = int((time.time() - start) * 1000)
                    return TestResult(0, 1, [f"Test timed out after {self.TIMEOUT_SECS}s"], "", elapsed)

            elapsed = int((time.time() - start) * 1000)
            output  = (result.stdout + result.stderr).strip()

            # Parse pytest output
            passed = failed = 0
            errors = []
            for line in output.splitlines():
                if "passed" in line:
                    try: passed = int(line.split("passed")[0].strip().split()[-1])
                    except ValueError: pass
                if "failed" in line:
                    try: failed = int(line.split("failed")[0].strip().split()[-1])
                    except ValueError: pass
                if "FAILED" in line or "ERROR" in line:
                    errors.append(line.strip())

            return TestResult(passed, failed, errors[:10], output, elapsed)

    # ══════════════════════════════════════════════════════════════
    # Run Existing Tests
    # ══════════════════════════════════════════════════════════════

    async def run_existing(self, test_path: str) -> TestResult:
        """Run an existing test file or directory with pytest."""
        path = Path(test_path)
        if not path.exists():
            return TestResult(0, 1, [f"Test path not found: {test_path}"], "", 0)

        return await asyncio.to_thread(self._run_subprocess_path, str(path))

    def _run_subprocess_path(self, test_path: str) -> TestResult:
        import time
        start = time.time()
        
        # Load configuration
        config = ConfigLoader.load()
        sandbox_enabled = config.get("sandbox.enabled", False)
        
        # Check if Docker is available
        docker_available = False
        if sandbox_enabled:
            try:
                res = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=3)
                docker_available = (res.returncode == 0)
            except Exception:
                pass

        if sandbox_enabled and docker_available:
            self._log.info("Running existing test path in Docker sandbox...")
            image = config.get("sandbox.docker_image", "python:3.11-slim")
            mem_limit = config.get("sandbox.memory_limit", "4g")
            cpu_limit = config.get("sandbox.cpu_limit", "2.0")
            
            # Mount the test file's parent directory and target the test file name
            path_obj = Path(test_path).resolve()
            parent_dir = str(path_obj.parent).replace("\\", "/")
            test_file_name = path_obj.name
            
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{parent_dir}:/app",
                "-w", "/app",
                "--network", "none",
                "-m", mem_limit,
                "--cpus", cpu_limit,
                image,
                "pytest", test_file_name, "-v", "--tb=short", "-q"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            except subprocess.TimeoutExpired:
                return TestResult(0, 1, ["Test suite timed out inside Docker after 60s"], "", 60000)
            except Exception as ex:
                self._log.warning("Docker sandbox failed to execute path, falling back to local host execution", error=str(ex))
                sandbox_enabled = False  # Triggers local fallback below

        if not sandbox_enabled or not docker_available:
            try:
                result = subprocess.run(
                    [self._python_executable, "-m", "pytest", test_path, "-v", "--tb=short", "-q"],
                    capture_output=True, text=True, timeout=60
                )
            except subprocess.TimeoutExpired:
                return TestResult(0, 1, ["Test suite timed out after 60s"], "", 60000)

        elapsed = int((time.time() - start) * 1000)
        output  = (result.stdout + result.stderr).strip()
        passed = failed = 0
        errors = []
        for line in output.splitlines():
            if "passed" in line:
                try: passed = int(line.split("passed")[0].strip().split()[-1])
                except ValueError: pass
            if "failed" in line:
                try: failed = int(line.split("failed")[0].strip().split()[-1])
                except ValueError: pass
            if "FAILED" in line or "ERROR" in line:
                errors.append(line.strip())
        return TestResult(passed, failed, errors[:10], output, elapsed)

    # ══════════════════════════════════════════════════════════════
    # Syntax Validation
    # ══════════════════════════════════════════════════════════════

    def validate_syntax(self, code: str, language: str = "python") -> dict[str, Any]:
        """Quick syntax validation without running tests."""
        if language == "python":
            import ast
            try:
                ast.parse(code)
                return {"valid": True, "errors": []}
            except SyntaxError as e:
                return {"valid": False, "errors": [f"Line {e.lineno}: {e.msg} — {e.text}"]}
        return {"valid": True, "errors": [], "note": f"Syntax check for '{language}' not implemented"}
