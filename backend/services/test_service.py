"""Test execution service — runs pytest, captures real results."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

from backend.config import GENERATED_TESTS_DIR
from backend.models.analysis import TestResult

logger = logging.getLogger("traceback.tests")


def run_pytest(
    target: str | None = None,
    cwd: str | None = None,
    timeout: int = 60,
) -> TestResult:
    """Run pytest and capture real results.

    Never reports success unless exit_code == 0.
    """
    result = TestResult()

    args = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--no-header"]
    if target:
        args.append(target)

    start = time.time()

    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result.exit_code = proc.returncode
        result.stdout = proc.stdout
        result.stderr = proc.stderr
        result.success = proc.returncode == 0
        result.duration_ms = int((time.time() - start) * 1000)

        # Parse pytest output for counts
        _parse_pytest_summary(proc.stdout, result)

    except subprocess.TimeoutExpired:
        result.exit_code = -1
        result.stderr = f"Test execution timed out after {timeout}s"
        result.duration_ms = timeout * 1000
    except FileNotFoundError:
        result.exit_code = -1
        result.stderr = "pytest not found — is it installed?"
    except Exception as e:
        result.exit_code = -1
        result.stderr = f"Test execution error: {e}"
        result.duration_ms = int((time.time() - start) * 1000)

    return result


def save_generated_test(
    test_code: str,
    test_name: str = "test_generated_regression.py",
    repo_path: str | None = None,
) -> str:
    """Save an AI-generated test file safely.

    Returns the path to the saved test file.
    """
    if repo_path:
        tests_dir = Path(repo_path) / "tests"
    else:
        tests_dir = Path(GENERATED_TESTS_DIR)

    tests_dir.mkdir(parents=True, exist_ok=True)

    if not test_code.strip():
        raise ValueError("Empty test code")

    preamble = """import pytest
import sys
import os

_repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

try:
    from auth import *
except ImportError:
    pass
"""

    if "import pytest" not in test_code:
        test_code = preamble + "\n\n" + test_code
    elif "sys.path" not in test_code:
        test_code = preamble + "\n\n" + test_code

    test_path = tests_dir / test_name
    test_path.write_text(test_code, encoding="utf-8")

    logger.info("Saved generated test to %s", test_path)
    return str(test_path)



def run_python_file(
    file_path: str,
    cwd: str | None = None,
    timeout: int = 30,
    args: list[str] | None = None,
) -> dict:
    """Run a Python file and capture stdout/stderr/exit_code.

    Used for verification — running the application after fix.
    """
    cmd = [sys.executable, file_path]
    if args:
        cmd.extend(args)

    start = time.time()

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "duration_ms": int((time.time() - start) * 1000),
            "crashed": proc.returncode != 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "exit_code": -1,
            "duration_ms": timeout * 1000,
            "crashed": True,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": int((time.time() - start) * 1000),
            "crashed": True,
        }


def _parse_pytest_summary(output: str, result: TestResult) -> None:
    """Parse pytest output to extract pass/fail/skip counts."""
    import re

    # Pattern: "X passed, Y failed, Z skipped"
    for line in output.splitlines():
        # Match patterns like "5 passed", "2 failed", etc.
        passed = re.search(r"(\d+)\s+passed", line)
        failed = re.search(r"(\d+)\s+failed", line)
        skipped = re.search(r"(\d+)\s+skipped", line)
        errors = re.search(r"(\d+)\s+error", line)

        if passed:
            result.passed = int(passed.group(1))
        if failed:
            result.failed = int(failed.group(1))
        if skipped:
            result.skipped = int(skipped.group(1))
        if errors:
            result.errors = int(errors.group(1))
