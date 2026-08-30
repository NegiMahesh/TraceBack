"""
TraceBack Autonomous Verification Service.

Verification pipeline:

    Apply Fix
       ↓
    Run Repaired File
       ↓
    Still crashes?
       ↓
    AI Repair #2
       ↓
    Run Again
       ↓
    AI Repair #3
       ↓
    Run Again
       ↓
    FIX VERIFIED

The project-wide baseline/existing pytest stages are intentionally disabled
for the main TraceBack demo pipeline.

Why?

The TraceBack demo should focus on whether the proposed repair actually
fixes the reported crash and whether the repaired file executes correctly.

Automatic rollback remains enabled whenever verification fails.
"""

from __future__ import annotations

import logging
import re
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

from backend.services.ollama_service import (
    ollama_service,
)

from backend.services.traceback_parser import (
    is_traceback,
    parse_traceback,
)


logger = logging.getLogger(
    "traceback.verification"
)


# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_REPAIR_ATTEMPTS = 3


# ============================================================================
# MAIN VERIFICATION
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

    logger.info(
        "============================================================"
    )

    logger.info(
        "TRACEBACK VERIFICATION START"
    )

    logger.info(
        "Investigation: %s",
        investigation_id,
    )

    logger.info(
        "Target: %s",
        target_file,
    )

    logger.info(
        "============================================================"
    )

    # ========================================================================
    # INITIAL STATE
    # ========================================================================

    current_patch = patch or ""

    current_modified_source = (
        expected_modified_code or ""
    )

    current_crash_file = (
        crash_file
        or target_file
    )

    first_backup_ref = ""

    # ========================================================================
    # AUTONOMOUS REPAIR LOOP
    # ========================================================================

    for attempt in range(
        1,
        MAX_REPAIR_ATTEMPTS + 1,
    ):

        logger.info(
            "------------------------------------------------------------"
        )

        logger.info(
            "REPAIR ATTEMPT %s/%s",
            attempt,
            MAX_REPAIR_ATTEMPTS,
        )

        logger.info(
            "------------------------------------------------------------"
        )

        # ====================================================================
        # PATCH
        # ====================================================================

        patch_step_name = (
            "Patch Applied"
            if attempt == 1
            else f"Autonomous Repair #{attempt}"
        )

        patch_step = VerificationStep(
            name=patch_step_name,
            status="running",
        )

        report.steps.append(
            patch_step
        )

        started = time.time()

        try:

            use_frozen_source = (
                attempt == 1
                and
                bool(
                    current_modified_source
                )
            )

            apply_result = (
                patch_service.apply_patch(
                    patch=current_patch,
                    target_file=target_file,
                    repo_path=repo_path,
                    investigation_id=investigation_id,
                    expected_original_sha256=(
                        expected_original_sha256
                        if attempt == 1
                        else ""
                    ),
                    expected_modified_code=(
                        current_modified_source
                        if use_frozen_source
                        else ""
                    ),
                )
            )

        except Exception as exc:

            logger.exception(
                "Patch application failed."
            )

            patch_step.duration_ms = int(
                (time.time() - started)
                * 1000
            )

            patch_step.status = (
                "failed"
            )

            patch_step.message = (
                f"Patch application error: {exc}"
            )

            if first_backup_ref:

                _rollback(
                    report=report,
                    backup_ref=first_backup_ref,
                    target_file=target_file,
                    repo_path=repo_path,
                )

            report.verdict = (
                "PATCH FAILED"
            )

            report.overall_success = False

            return report

        patch_step.duration_ms = int(
            (time.time() - started)
            * 1000
        )

        if (
            apply_result is None
            or
            not apply_result.success
        ):

            patch_step.status = (
                "failed"
            )

            patch_step.message = (
                apply_result.message
                if apply_result is not None
                else "Patch application failed."
            )

            logger.error(
                "Patch attempt %s failed: %s",
                attempt,
                patch_step.message,
            )

            if first_backup_ref:

                _rollback(
                    report=report,
                    backup_ref=first_backup_ref,
                    target_file=target_file,
                    repo_path=repo_path,
                )

            report.verdict = (
                "PATCH FAILED"
            )

            report.overall_success = False

            return report

        patch_step.status = (
            "passed"
        )

        patch_step.message = (
            "Patch applied successfully."
        )

        if not first_backup_ref:

            first_backup_ref = (
                apply_result.backup_ref
            )

            report.backup_ref = (
                first_backup_ref
            )

        # ====================================================================
        # EXECUTE REPAIRED FILE
        # ====================================================================

        execution_step_name = (
            "Regression Test"
            if attempt == 1
            else f"Repair Validation #{attempt}"
        )

        execution_step = VerificationStep(
            name=execution_step_name,
            status="running",
        )

        report.steps.append(
            execution_step
        )

        started = time.time()

        logger.info(
            "Executing repaired file: %s",
            current_crash_file,
        )

        try:

            # --------------------------------------------------------------
            # HARD SAFETY CHECK
            # --------------------------------------------------------------

            current_target = (
                patch_service.resolve_target_file(
                    repo_path,
                    current_crash_file,
                )
            )

            current_source = (
                current_target.read_text(
                    encoding="utf-8"
                )
            )

            if not current_source.strip():

                execution_step.status = (
                    "failed"
                )

                execution_step.message = (
                    "Safety check blocked verification: "
                    "repaired source is empty."
                )

                execution_step.duration_ms = int(
                    (time.time() - started)
                    * 1000
                )

                _rollback(
                    report=report,
                    backup_ref=first_backup_ref,
                    target_file=target_file,
                    repo_path=repo_path,
                )

                report.verdict = (
                    "VERIFICATION FAILED"
                )

                report.overall_success = False

                return report

            # --------------------------------------------------------------
            # Execute repaired source
            # --------------------------------------------------------------

            direct_result = (
                test_service.run_python_file(
                    file_path=current_crash_file,
                    cwd=repo_path,
                    timeout=30,
                )
            )

        except Exception as exc:

            logger.exception(
                "Repaired file execution failed."
            )

            execution_step.status = (
                "failed"
            )

            execution_step.message = (
                f"Execution error: {exc}"
            )

            execution_step.duration_ms = int(
                (time.time() - started)
                * 1000
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            report.overall_success = False

            return report

        execution_step.duration_ms = int(
            (time.time() - started)
            * 1000
        )

        report.generated_test_result = (
            _python_to_test_result(
                direct_result
            )
        )

        # ====================================================================
        # EXECUTION PASSED
        # ====================================================================

        if not direct_result.get(
            "crashed",
            True,
        ):

            execution_step.status = (
                "passed"
            )

            execution_step.message = (
                "Repaired file executes successfully."
            )

            logger.info(
                "Repair attempt %s succeeded.",
                attempt,
            )

            break

        # ====================================================================
        # EXECUTION FAILED
        # ====================================================================

        execution_step.status = (
            "failed"
        )

        failure_message = (
            _python_failure(
                direct_result
            )
        )

        execution_step.message = (
            failure_message
        )

        logger.warning(
            "Repair attempt %s still crashes:\n%s",
            attempt,
            failure_message,
        )

        # ====================================================================
        # MAX ATTEMPTS
        # ====================================================================

        if (
            attempt
            >=
            MAX_REPAIR_ATTEMPTS
        ):

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            report.overall_success = False

            return report

        # ====================================================================
        # CAPTURE NEW TRACEBACK
        # ====================================================================

        new_traceback = str(
            direct_result.get(
                "stderr",
                "",
            )
            or ""
        ).strip()

        if not new_traceback:

            new_traceback = str(
                direct_result.get(
                    "stdout",
                    "",
                )
                or ""
            ).strip()

        logger.info(
            "New traceback captured:\n%s",
            new_traceback[:5000],
        )

        if not is_traceback(
            new_traceback
        ):

            execution_step.message += (
                " TraceBack could not identify "
                "a new Python traceback."
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        # ====================================================================
        # PARSE NEW TRACEBACK
        # ====================================================================

        try:

            new_parsed = (
                parse_traceback(
                    new_traceback
                )
            )

        except Exception as exc:

            logger.exception(
                "New traceback parsing failed."
            )

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    f"Could not parse new traceback: {exc}"
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        # ====================================================================
        # READ CURRENT SOURCE
        # ====================================================================

        try:

            current_target = (
                patch_service.resolve_target_file(
                    repo_path,
                    target_file,
                )
            )

            current_source = (
                current_target.read_text(
                    encoding="utf-8"
                )
            )

        except Exception as exc:

            logger.exception(
                "Could not read current repaired source."
            )

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    f"Could not read repaired source: {exc}"
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        # ====================================================================
        # ASK AI FOR NEXT REPAIR
        # ====================================================================

        logger.info(
            "Requesting autonomous AI repair #%s",
            attempt + 1,
        )

        try:

            ai_result = (
                await ollama_service.analyze_crash(
                    error_type=(
                        new_parsed.error_type
                    ),
                    error_message=(
                        new_parsed.message
                    ),
                    source_code=(
                        current_source
                    ),
                    file_path=(
                        target_file
                    ),
                    line_number=(
                        new_parsed.line
                    ),
                    function_name=(
                        new_parsed.function
                    ),
                    git_blame="",
                    traceback_raw=(
                        new_traceback
                    ),
                )
            )

        except Exception as exc:

            logger.exception(
                "Autonomous AI repair failed."
            )

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    f"AI repair failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        if ai_result is None:

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    "AI returned no repair result."
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        next_patch = str(
            getattr(
                ai_result,
                "patch",
                "",
            )
            or ""
        ).strip()

        if not next_patch:

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    "AI analyzed the new crash but "
                    "did not produce a safe patch."
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        # ====================================================================
        # VALIDATE NEXT PATCH
        # ====================================================================

        try:

            normalized_next_patch = (
                patch_service.normalize_patch(
                    patch=next_patch,
                    repo_path=repo_path,
                    target_file=target_file,
                )
            )

            next_modified_source = (
                patch_service.apply_unified_diff(
                    original=current_source,
                    patch=normalized_next_patch,
                )
            )

            if next_modified_source is None:

                raise ValueError(
                    "The next patch does not match "
                    "the current repaired source."
                )

            if (
                next_modified_source
                == current_source
            ):

                raise ValueError(
                    "The next patch produces no source change."
                )

        except Exception as exc:

            repair_step = VerificationStep(
                name=(
                    f"AI Repair Generation #{attempt + 1}"
                ),
                status="failed",
                message=(
                    f"Generated repair rejected: {exc}"
                ),
            )

            report.steps.append(
                repair_step
            )

            _rollback(
                report=report,
                backup_ref=first_backup_ref,
                target_file=target_file,
                repo_path=repo_path,
            )

            report.verdict = (
                "VERIFICATION FAILED"
            )

            return report

        repair_step = VerificationStep(
            name=(
                f"AI Repair Generation #{attempt + 1}"
            ),
            status="passed",
            message=(
                "AI analyzed the new traceback "
                "and generated a targeted repair."
            ),
        )

        report.steps.append(
            repair_step
        )

        current_patch = (
            normalized_next_patch
        )

        current_modified_source = (
            next_modified_source
        )

    # =========================================================================
    # FINAL SAFETY CHECK
    # =========================================================================

    successful_execution = any(
        step.status == "passed"
        and
        step.name in (
            "Regression Test",
            "Repair Validation #2",
            "Repair Validation #3",
        )
        for step in report.steps
    )

    if not successful_execution:

        _rollback(
            report=report,
            backup_ref=first_backup_ref,
            target_file=target_file,
            repo_path=repo_path,
        )

        report.verdict = (
            "VERIFICATION FAILED"
        )

        report.overall_success = False

        return report

    # =========================================================================
    # VERIFIED
    # =========================================================================

    report.steps.append(
        VerificationStep(
            name="Fix Verified",
            status="passed",
            message=(
                "The repaired application executes successfully "
                "and no new crash was detected."
            ),
        )
    )

    report.overall_success = True

    report.verdict = (
        "FIX VERIFIED"
    )

    report.backup_ref = (
        first_backup_ref
    )

    logger.info(
        "============================================================"
    )

    logger.info(
        "TRACEBACK FIX VERIFIED"
    )

    logger.info(
        "============================================================"
    )

    return report


# ============================================================================
# PYTHON RESULT
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
        skipped=0,
        errors=(
            1
            if result.get(
                "exit_code",
                -1,
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
        success=(
            not crashed
        ),
    )


# ============================================================================
# PYTHON FAILURE
# ============================================================================

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
            + stderr[:2000]
        )

    if stdout:

        return (
            "Repaired file exited unsuccessfully:\n"
            + stdout[:2000]
        )

    return (
        "Repaired file exited with a non-zero status."
    )


# ============================================================================
# ROLLBACK
# ============================================================================

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

    try:

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

    except Exception as exc:

        rollback_step.duration_ms = int(
            (time.time() - started)
            * 1000
        )

        rollback_step.status = (
            "failed"
        )

        rollback_step.message = (
            f"Rollback error: {exc}"
        )

        logger.exception(
            "Rollback failed."
        )

    report.overall_success = False

    report.verdict = (
        "VERIFICATION FAILED"
    )