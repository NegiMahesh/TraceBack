"""
TraceBack deterministic verification service.

The service verifies the EXACT modified source produced during analysis.

Pipeline:

1. Baseline tests
2. Verify source has not changed since analysis
3. Apply frozen modified source
4. Run repaired application
5. Run existing tests
6. Compare against baseline
7. Verify or rollback
"""

from __future__ import annotations

import logging
import time

from backend.models.analysis import (
    TestResult,
    VerificationReport,
    VerificationStep,
)

from backend.services import (
    patch_service,
    test_service,
)

logger = logging.getLogger(
    "traceback.verification"
)


# ============================================================================
# MAIN
# ============================================================================

async def verify_fix(
    patch: str,
    target_file: str,
    repo_path: str,
    investigation_id: str,
    generated_test: str = "",
    crash_file: str = "",
    expected_original_sha256: str = "",
    expected_modified_code: str = "",
) -> VerificationReport:

    report = VerificationReport()

    # ========================================================================
    # STEP 1 — BASELINE
    # ========================================================================

    baseline_step = VerificationStep(
        name="Baseline Tests",
        status="running",
    )

    report.steps.append(
        baseline_step
    )

    started = time.time()

    try:

        baseline_result = (
            test_service.run_pytest(
                cwd=repo_path,
                timeout=120,
            )
        )

        baseline_step.duration_ms = int(
            (time.time() - started)
            * 1000
        )

        if baseline_result.success:

            baseline_step.status = (
                "passed"
            )

            baseline_step.message = (
                f"{baseline_result.passed} "
                f"existing test(s) passed before patch."
            )

        elif (
            baseline_result.exit_code
            == 5
        ):

            baseline_step.status = (
                "warning"
            )

            baseline_step.message = (
                "No existing pytest tests were collected."
            )

        else:

            baseline_step.status = (
                "warning"
            )

            baseline_step.message = (
                "Pre-existing test failures detected: "
                + _failure_names(
                    baseline_result
                )
            )

    except Exception as exc:

        logger.exception(
            "Baseline test failure"
        )

        baseline_result = None

        baseline_step.status = (
            "warning"
        )

        baseline_step.message = (
            f"Could not establish baseline: {exc}"
        )

    # ========================================================================
    # STEP 2 — APPLY FROZEN SOURCE
    # ========================================================================

    patch_step = VerificationStep(
        name="Patch Applied",
        status="running",
    )

    report.steps.append(
        patch_step
    )

    started = time.time()

    apply_result = (
        patch_service.apply_patch(
            patch=patch,
            target_file=target_file,
            repo_path=repo_path,
            investigation_id=investigation_id,
            expected_original_sha256=(
                expected_original_sha256
            ),
            expected_modified_code=(
                expected_modified_code
            ),
        )
    )

    patch_step.duration_ms = int(
        (time.time() - started)
        * 1000
    )

    if not apply_result.success:

        patch_step.status = (
            "failed"
        )

        patch_step.message = (
            apply_result.message
        )

        report.verdict = (
            "PATCH FAILED"
        )

        return report

    patch_step.status = (
        "passed"
    )

    patch_step.message = (
        "Patch applied successfully."
    )

    backup_ref = (
        apply_result.backup_ref
    )

    report.backup_ref = (
        backup_ref
    )

    # ========================================================================
    # STEP 3 — REPAIRED FILE EXECUTION
    # ========================================================================

    if crash_file:

        regression_step = VerificationStep(
            name="Regression Test",
            status="running",
        )

        report.steps.append(
            regression_step
        )

        started = time.time()

        try:

            direct_result = (
                test_service.run_python_file(
                    file_path=crash_file,
                    cwd=repo_path,
                    timeout=30,
                )
            )

            report.generated_test_result = (
                _python_to_test_result(
                    direct_result
                )
            )

            regression_step.duration_ms = int(
                (time.time() - started)
                * 1000
            )

            if not direct_result.get(
                "crashed",
                True,
            ):

                regression_step.status = (
                    "passed"
                )

                regression_step.message = (
                    "Repaired file executes successfully."
                )

            else:

                regression_step.status = (
                    "failed"
                )

                regression_step.message = (
                    _python_failure(
                        direct_result
                    )
                )

                _rollback(
                    report,
                    backup_ref,
                    target_file,
                    repo_path,
                )

                return report

        except Exception as exc:

            logger.exception(
                "Regression execution failed"
            )

            regression_step.status = (
                "failed"
            )

            regression_step.message = (
                f"Regression test failed: {exc}"
            )

            _rollback(
                report,
                backup_ref,
                target_file,
                repo_path,
            )

            return report

    else:

        report.steps.append(
            VerificationStep(
                name="Regression Test",
                status="skipped",
                message=(
                    "No crash file was supplied."
                ),
            )
        )

    # ========================================================================
    # STEP 4 — EXISTING TESTS
    # ========================================================================

    existing_step = VerificationStep(
        name="Existing Tests",
        status="running",
    )

    report.steps.append(
        existing_step
    )

    started = time.time()

    try:

        existing_result = (
            test_service.run_pytest(
                cwd=repo_path,
                timeout=120,
            )
        )

        report.existing_test_result = (
            existing_result
        )

        existing_step.duration_ms = int(
            (time.time() - started)
            * 1000
        )

    except Exception as exc:

        logger.exception(
            "Existing test execution failed"
        )

        existing_result = None

        existing_step.status = (
            "warning"
        )

        existing_step.message = (
            f"Could not execute existing tests: {exc}"
        )

    if existing_result is None:

        pass

    elif existing_result.success:

        existing_step.status = (
            "passed"
        )

        existing_step.message = (
            f"{existing_result.passed} "
            f"existing test(s) passed."
        )

    elif existing_result.exit_code == 5:

        existing_step.status = (
            "warning"
        )

        existing_step.message = (
            "No existing pytest tests were collected."
        )

    else:

        before_failures = (
            _extract_test_failures(
                baseline_result
            )
            if baseline_result
            else set()
        )

        after_failures = (
            _extract_test_failures(
                existing_result
            )
        )

        new_failures = (
            after_failures
            - before_failures
        )

        if (
            baseline_result
            and
            not baseline_result.success
            and
            not new_failures
        ):

            existing_step.status = (
                "warning"
            )

            existing_step.message = (
                "Pre-existing test failures remain; "
                "no new regression was introduced."
            )

        else:

            existing_step.status = (
                "failed"
            )

            if new_failures:

                existing_step.message = (
                    "New regression detected: "
                    + ", ".join(
                        sorted(
                            new_failures
                        )
                    )
                )

            else:

                existing_step.message = (
                    _best_test_error(
                        existing_result
                    )
                )

            _rollback(
                report,
                backup_ref,
                target_file,
                repo_path,
            )

            return report

    # ========================================================================
    # STEP 5 — VERIFIED
    # ========================================================================

    report.steps.append(
        VerificationStep(
            name="Fix Verified",
            status="passed",
            message=(
                "Frozen patch applied successfully, "
                "repaired file runs successfully, "
                "and no new existing-test regressions were detected."
            ),
        )
    )

    report.overall_success = True

    report.verdict = (
        "FIX VERIFIED"
    )

    report.backup_ref = (
        backup_ref
    )

    return report


# ============================================================================
# HELPERS
# ============================================================================

def _python_to_test_result(
    result: dict,
) -> TestResult:

    crashed = bool(
        result.get(
            "crashed",
            True,
        )
    )

    return TestResult(
        passed=(
            0
            if crashed
            else 1
        ),
        failed=(
            1
            if crashed
            else 0
        ),
        errors=(
            1
            if result.get(
                "exit_code",
                0,
            ) == -1
            else 0
        ),
        duration_ms=int(
            result.get(
                "duration_ms",
                0,
            )
        ),
        exit_code=int(
            result.get(
                "exit_code",
                -1,
            )
        ),
        stdout=str(
            result.get(
                "stdout",
                "",
            )
            or ""
        ),
        stderr=str(
            result.get(
                "stderr",
                "",
            )
            or ""
        ),
        success=not crashed,
    )


def _python_failure(
    result: dict,
) -> str:

    stderr = str(
        result.get(
            "stderr",
            "",
        )
        or ""
    ).strip()

    stdout = str(
        result.get(
            "stdout",
            "",
        )
        or ""
    ).strip()

    if stderr:

        return (
            "Repaired file still crashes:\n"
            + stderr[:1500]
        )

    if stdout:

        return (
            "Repaired file exited unsuccessfully:\n"
            + stdout[:1500]
        )

    return (
        "Repaired file exited with a non-zero status."
    )


def _failure_names(
    result,
) -> str:

    names = (
        _extract_test_failures(
            result
        )
    )

    if names:
        return ", ".join(
            sorted(names)
        )

    return "existing tests"


def _extract_test_failures(
    result,
) -> set[str]:

    if result is None:
        return set()

    text = (
        str(
            getattr(
                result,
                "stdout",
                "",
            )
            or ""
        )
        + "\n"
        +
        str(
            getattr(
                result,
                "stderr",
                "",
            )
            or ""
        )
    )

    import re

    failures: set[str] = set()

    for match in re.finditer(
        r"(?m)^\s*(?:FAILED|ERROR)\s+(.+?)(?:\s+-|$)",
        text,
    ):

        value = match.group(
            1
        ).strip()

        if value:
            failures.add(
                value
            )

    return failures


def _best_test_error(
    result,
) -> str:

    stderr = str(
        getattr(
            result,
            "stderr",
            "",
        )
        or ""
    ).strip()

    stdout = str(
        getattr(
            result,
            "stdout",
            "",
        )
        or ""
    ).strip()

    if stderr:
        return stderr[:1500]

    if stdout:
        return stdout[:1500]

    failed = getattr(
        result,
        "failed",
        0,
    )

    errors = getattr(
        result,
        "errors",
        0,
    )

    if failed:
        return (
            f"{failed} test(s) failed."
        )

    if errors:
        return (
            f"{errors} test error(s) occurred."
        )

    return (
        "Existing test suite failed."
    )


def _rollback(
    report: VerificationReport,
    backup_ref: str,
    target_file: str,
    repo_path: str,
) -> None:

    rollback_step = VerificationStep(
        name="Auto-Rollback",
        status="running",
    )

    report.steps.append(
        rollback_step
    )

    started = time.time()

    rollback_result = (
        patch_service.rollback(
            backup_ref=backup_ref,
            target_file=target_file,
            repo_path=repo_path,
        )
    )

    rollback_step.duration_ms = int(
        (time.time() - started)
        * 1000
    )

    if rollback_result.success:

        rollback_step.status = (
            "passed"
        )

        rollback_step.message = (
            "Original source restored."
        )

    else:

        rollback_step.status = (
            "failed"
        )

        rollback_step.message = (
            "Rollback failed: "
            + rollback_result.message
        )

    report.overall_success = False

    report.verdict = (
        "VERIFICATION FAILED"
    )

    report.backup_ref = (
        backup_ref
    )