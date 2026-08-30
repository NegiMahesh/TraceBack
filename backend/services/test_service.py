"""
TraceBack test execution service.

Generated regression tests are isolated from the user's project tests.
When a Python file is being verified, TraceBack can execute that file
directly instead of importing it. This avoids failures caused by modules
that execute application code during import.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
import time
from pathlib import Path

from backend.config import GENERATED_TESTS_DIR
from backend.models.analysis import TestResult

logger = logging.getLogger("traceback.tests")


# ---------------------------------------------------------------------------
# Pytest
# ---------------------------------------------------------------------------

def run_pytest(
    target: str | None = None,
    cwd: str | None = None,
    timeout: int = 60,
) -> TestResult:
    """Run pytest and return a structured result."""

    result = TestResult()

    timeout = max(
        1,
        min(int(timeout), 300),
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        "--no-header",
    ]

    if target:
        command.append(target)

    started = time.time()

    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result.exit_code = process.returncode
        result.stdout = process.stdout
        result.stderr = process.stderr

        result.success = (
            process.returncode == 0
        )

        result.duration_ms = int(
            (time.time() - started) * 1000
        )

        _parse_pytest_summary(
            process.stdout,
            result,
        )

    except subprocess.TimeoutExpired:
        result.exit_code = -1
        result.stderr = (
            f"Test execution timed out after {timeout}s"
        )
        result.duration_ms = timeout * 1000

    except FileNotFoundError:
        result.exit_code = -1
        result.stderr = (
            "pytest could not be started. "
            "Make sure pytest is installed."
        )
        result.duration_ms = int(
            (time.time() - started) * 1000
        )

    except Exception as exc:
        logger.exception(
            "pytest execution failed"
        )

        result.exit_code = -1
        result.stderr = (
            f"Test execution error: {exc}"
        )
        result.duration_ms = int(
            (time.time() - started) * 1000
        )

    return result


# ---------------------------------------------------------------------------
# Generated tests
# ---------------------------------------------------------------------------

def save_generated_test(
    test_code: str,
    test_name: str = "test_generated_regression.py",
    repo_path: str | None = None,
) -> str:
    """
    Save an AI-generated test.

    IMPORTANT:
    The generated test is stored outside the target project's tests/
    directory so TraceBack does not mutate the user's test suite.

    We deliberately do NOT inject:

        from auth import *
        import auth

    because importing a script can execute application code and create
    unrelated failures.
    """

    if not test_code or not test_code.strip():
        raise ValueError(
            "Generated test code is empty."
        )

    tests_dir = Path(
        GENERATED_TESTS_DIR
    ).resolve()

    tests_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = Path(
        test_name
    ).name

    if not safe_name.endswith(
        ".py"
    ):
        safe_name += ".py"

    repo_root = (
        Path(repo_path).resolve()
        if repo_path
        else Path.cwd().resolve()
    )

    header = f'''"""
TraceBack generated regression test.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(
    r"{repo_root}"
)

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(_REPO_ROOT),
    )

'''

    code = test_code.strip()

    # Remove known bad patterns that TraceBack used to inject.
    code = re.sub(
        r"^\s*try:\s*\n\s*from\s+auth\s+import\s+\*\s*\n"
        r"\s*except\s+ImportError:\s*\n\s*pass\s*$",
        "",
        code,
        flags=re.MULTILINE,
    )

    final_code = (
        header
        + "\n"
        + code
        + "\n"
    )

    path = (
        tests_dir
        / safe_name
    )

    path.write_text(
        final_code,
        encoding="utf-8",
    )

    logger.info(
        "Generated test saved: %s",
        path,
    )

    return str(path)


def create_file_execution_test(
    file_path: str,
    repo_path: str,
    test_name: str = "test_traceback_file_execution.py",
    args: list[str] | None = None,
) -> str:
    """
    Create a regression test that executes the crashed Python file
    as a subprocess.

    This is much safer than importing the module because Python files
    frequently contain executable top-level code.
    """

    tests_dir = Path(
        GENERATED_TESTS_DIR
    ).resolve()

    tests_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = Path(
        test_name
    ).name

    if not safe_name.endswith(
        ".py"
    ):
        safe_name += ".py"

    file_absolute = (
        Path(file_path)
        .resolve()
    )

    repo_absolute = (
        Path(repo_path)
        .resolve()
    )

    args = args or []

    args_literal = repr(
        [str(x) for x in args]
    )

    test_code = f'''"""
TraceBack execution regression test.

This test executes the repaired file directly instead of importing it.
"""

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(
    r"{repo_absolute}"
)

TARGET_FILE = Path(
    r"{file_absolute}"
)

ARGS = {args_literal}


def test_repaired_file_runs_without_crash():
    command = [
        sys.executable,
        str(TARGET_FILE),
        *ARGS,
    ]

    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "Repaired file still crashes.\\n\\n"
        f"STDOUT:\\n{{result.stdout}}\\n\\n"
        f"STDERR:\\n{{result.stderr}}"
    )
'''

    path = (
        tests_dir
        / safe_name
    )

    path.write_text(
        test_code,
        encoding="utf-8",
    )

    logger.info(
        "Created execution regression test: %s",
        path,
    )

    return str(path)


# ---------------------------------------------------------------------------
# Direct Python execution
# ---------------------------------------------------------------------------

def run_python_file(
    file_path: str,
    cwd: str | None = None,
    timeout: int = 30,
    args: list[str] | None = None,
) -> dict:
    """Run a Python file directly."""

    timeout = max(
        1,
        min(int(timeout), 300),
    )

    target = (
        Path(file_path)
        .resolve()
    )

    if not target.is_file():
        return {
            "stdout": "",
            "stderr": (
                f"Python file not found: "
                f"{target}"
            ),
            "exit_code": -1,
            "duration_ms": 0,
            "crashed": True,
        }

    command = [
        sys.executable,
        str(target),
    ]

    if args:
        command.extend(
            str(arg)
            for arg in args
        )

    started = time.time()

    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "exit_code": process.returncode,
            "duration_ms": int(
                (time.time() - started)
                * 1000
            ),
            "crashed": (
                process.returncode != 0
            ),
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": (
                f"Execution timed out after {timeout}s"
            ),
            "exit_code": -1,
            "duration_ms": timeout * 1000,
            "crashed": True,
        }

    except Exception as exc:
        logger.exception(
            "Python execution failed"
        )

        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "duration_ms": int(
                (time.time() - started)
                * 1000
            ),
            "crashed": True,
        }


# ---------------------------------------------------------------------------
# Pytest summary parser
# ---------------------------------------------------------------------------

def _parse_pytest_summary(
    output: str,
    result: TestResult,
) -> None:
    """Extract pytest statistics."""

    for line in output.splitlines():

        match = re.search(
            r"(\d+)\s+passed",
            line,
        )

        if match:
            result.passed = int(
                match.group(1)
            )

        match = re.search(
            r"(\d+)\s+failed",
            line,
        )

        if match:
            result.failed = int(
                match.group(1)
            )

        match = re.search(
            r"(\d+)\s+skipped",
            line,
        )

        if match:
            result.skipped = int(
                match.group(1)
            )

        match = re.search(
            r"(\d+)\s+errors?",
            line,
        )

        if match:
            result.errors = int(
                match.group(1)
            )