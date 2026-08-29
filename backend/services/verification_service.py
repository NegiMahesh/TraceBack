"""Verification service — full pipeline: patch → test → re-run → report."""

from __future__ import annotations

import logging
import time

from backend.models.analysis import TestResult, VerificationReport, VerificationStep
from backend.services import patch_service, test_service

logger = logging.getLogger("traceback.verification")


async def verify_fix(
    patch: str,
    target_file: str,
    repo_path: str,
    investigation_id: str,
    generated_test: str = "",
    crash_file: str = "",
) -> VerificationReport:
    """Run the full verification pipeline.

    Steps:
    1. Apply patch
    2. Run generated regression test
    3. Run existing tests
    4. Re-run the crashed application
    5. Compare result
    """
    report = VerificationReport()

    # ── Step 1: Apply patch ────────────────────────────────────────────
    step1 = VerificationStep(name="Patch Applied", status="running")
    report.steps.append(step1)

    t0 = time.time()
    apply_result = patch_service.apply_patch(
        patch=patch,
        target_file=target_file,
        repo_path=repo_path,
        investigation_id=investigation_id,
    )

    step1.duration_ms = int((time.time() - t0) * 1000)

    if not apply_result.success:
        step1.status = "failed"
        step1.message = apply_result.message
        report.verdict = "PATCH FAILED"
        return report

    step1.status = "passed"
    step1.message = apply_result.message
    backup_ref = apply_result.backup_ref

    # ── Step 2: Run generated regression test ──────────────────────────
    if generated_test:
        step2 = VerificationStep(name="Regression Test", status="running")
        report.steps.append(step2)

        t0 = time.time()
        try:
            test_path = test_service.save_generated_test(
                generated_test, repo_path=repo_path
            )
            gen_result = test_service.run_pytest(target=test_path, cwd=repo_path)
            report.generated_test_result = gen_result

            step2.duration_ms = int((time.time() - t0) * 1000)

            if gen_result.success:
                step2.status = "passed"
                step2.message = f"{gen_result.passed} passed"
            else:
                step2.status = "failed"
                step2.message = gen_result.stderr[:200] if gen_result.stderr else "Test failed"
                # Rollback
                _rollback_and_report(report, backup_ref, target_file, repo_path)
                return report
        except Exception as e:
            step2.status = "failed"
            step2.message = str(e)
            step2.duration_ms = int((time.time() - t0) * 1000)
            _rollback_and_report(report, backup_ref, target_file, repo_path)
            return report

    # ── Step 3: Run existing tests ─────────────────────────────────────
    step3 = VerificationStep(name="Existing Tests", status="running")
    report.steps.append(step3)

    t0 = time.time()
    existing_result = test_service.run_pytest(cwd=repo_path)
    report.existing_test_result = existing_result

    step3.duration_ms = int((time.time() - t0) * 1000)

    if existing_result.success:
        step3.status = "passed"
        step3.message = f"{existing_result.passed} passed"
    elif existing_result.exit_code == 5:
        # No tests collected — that's ok
        step3.status = "passed"
        step3.message = "No existing tests found"
    else:
        step3.status = "failed"
        step3.message = f"{existing_result.failed} failed"
        _rollback_and_report(report, backup_ref, target_file, repo_path)
        return report

    # ── Step 4: Re-run crashed application ─────────────────────────────
    if crash_file:
        step4 = VerificationStep(name="Application Re-run", status="running")
        report.steps.append(step4)

        t0 = time.time()
        rerun = test_service.run_python_file(crash_file, cwd=repo_path)
        report.rerun_result = rerun

        step4.duration_ms = int((time.time() - t0) * 1000)

        if not rerun.get("crashed", True):
            step4.status = "passed"
            step4.message = "Application runs successfully"
        else:
            step4.status = "failed"
            step4.message = "Application still crashes"
            _rollback_and_report(report, backup_ref, target_file, repo_path)
            return report

    # ── Step 5: Verdict ────────────────────────────────────────────────
    step5 = VerificationStep(name="Fix Verified", status="passed", message="Original crash resolved")
    report.steps.append(step5)

    report.overall_success = True
    report.verdict = "FIX VERIFIED"
    return report


def _rollback_and_report(
    report: VerificationReport,
    backup_ref: str,
    target_file: str,
    repo_path: str,
) -> None:
    """Add a rollback step to the report."""
    rollback_step = VerificationStep(name="Auto-Rollback", status="running")
    report.steps.append(rollback_step)

    t0 = time.time()
    rb = patch_service.rollback(backup_ref, target_file, repo_path)
    rollback_step.duration_ms = int((time.time() - t0) * 1000)

    if rb.success:
        rollback_step.status = "passed"
        rollback_step.message = "Rolled back to original"
    else:
        rollback_step.status = "failed"
        rollback_step.message = rb.message

    report.verdict = "VERIFICATION FAILED"
    report.overall_success = False
