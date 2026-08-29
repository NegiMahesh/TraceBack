"""Patch management endpoints — validate, apply, rollback."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config import DEFAULT_REPO_PATH
from backend.models.patch import PatchApplyRequest, RollbackRequest
from backend.services import patch_service
from backend.services import verification_service

router = APIRouter(prefix="/patch", tags=["patch"])


@router.post("/validate")
async def validate_patch(request: PatchApplyRequest):
    """Validate a patch before applying it."""
    result = patch_service.validate_patch(
        patch=request.patch,
        target_file=request.target_file,
        repo_path=request.repo_path or DEFAULT_REPO_PATH,
    )
    return result.model_dump()


@router.post("/apply")
async def apply_patch(request: PatchApplyRequest):
    """Apply a patch with safety checks and backup."""
    repo_path = request.repo_path or DEFAULT_REPO_PATH

    # Validate first
    validation = patch_service.validate_patch(
        patch=request.patch,
        target_file=request.target_file,
        repo_path=repo_path,
    )

    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Patch validation failed: {validation.reason}",
        )

    result = patch_service.apply_patch(
        patch=request.patch,
        target_file=request.target_file,
        repo_path=repo_path,
        investigation_id=request.investigation_id,
    )

    return result.model_dump()


@router.post("/rollback")
async def rollback_patch(request: RollbackRequest):
    """Rollback a previously applied patch."""
    from backend.api.analysis import _investigations

    # Find the investigation to get target file
    target_file = ""
    for inv in _investigations:
        if inv.id == request.investigation_id:
            target_file = inv.file
            break

    if not target_file:
        raise HTTPException(status_code=404, detail="Investigation not found")

    result = patch_service.rollback(
        backup_ref=request.backup_ref,
        target_file=target_file,
        repo_path=request.repo_path or DEFAULT_REPO_PATH,
    )
    return result.model_dump()


@router.post("/verify")
async def verify_patch(request: PatchApplyRequest):
    """Apply patch and run full verification pipeline."""
    from backend.api.analysis import _investigations

    repo_path = request.repo_path or DEFAULT_REPO_PATH

    # Find investigation for test case and crash file
    generated_test = ""
    crash_file = ""
    for inv in _investigations:
        if inv.id == request.investigation_id:
            generated_test = inv.test_case
            crash_file = inv.file
            break

    report = await verification_service.verify_fix(
        patch=request.patch,
        target_file=request.target_file,
        repo_path=repo_path,
        investigation_id=request.investigation_id,
        generated_test=generated_test,
        crash_file=crash_file,
    )

    # Update investigation status
    for inv in _investigations:
        if inv.id == request.investigation_id:
            inv.verification = report
            if report.overall_success:
                inv.status = "VERIFIED"
            else:
                inv.status = "FAILED"
            break

    return report.model_dump()


@router.get("/history")
async def patch_history():
    """Get patch application history."""
    return [p.model_dump() for p in patch_service.get_patch_history()]
