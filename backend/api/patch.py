"""
TraceBack Patch API.

Important design rule:
Patch verification must not depend entirely on the in-memory
investigation list.

The frontend can keep an investigation object while the backend
reloads/restarts. Therefore /patch/verify supports two modes:

1. Investigation exists:
   Use its frozen source state and metadata.

2. Investigation is missing:
   Fall back to the request's patch + target file and verify directly.

This prevents a backend reload from making an otherwise valid
Approve & Verify action unusable.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.config import DEFAULT_REPO_PATH

from backend.models.patch import (
    PatchApplyRequest,
    RollbackRequest,
)

from backend.services import (
    patch_service,
    verification_service,
)

logger = logging.getLogger(
    "traceback.patch_api"
)

router = APIRouter(
    prefix="/patch",
    tags=["patch"],
)


# ============================================================================
# HELPERS
# ============================================================================

def get_repo_path(
    repo_path: str | None,
) -> str:
    """Return supplied repository path or configured default."""

    value = (
        repo_path or ""
    ).strip()

    return (
        value
        if value
        else DEFAULT_REPO_PATH
    )


def get_investigation(
    investigation_id: str,
):
    """
    Find investigation in the current backend process.

    This may return None after a server reload because investigations
    are currently stored in memory.
    """

    try:
        from backend.api.analysis import (
            _investigations,
        )
    except Exception:
        return None

    for investigation in _investigations:

        if (
            investigation.id
            == investigation_id
        ):
            return investigation

    return None


def normalize_path_for_compare(
    repo_path: str,
    file_path: str,
):
    """Resolve a source file for safe path comparison."""

    return (
        patch_service.resolve_target_file(
            repo_path,
            file_path,
        )
    )


# ============================================================================
# VALIDATE
# ============================================================================

@router.post("/validate")
async def validate_patch(
    request: PatchApplyRequest,
):
    """Validate an AI-generated patch."""

    repo_path = get_repo_path(
        request.repo_path
    )

    try:

        result = (
            patch_service.validate_patch(
                patch=request.patch,
                target_file=request.target_file,
                repo_path=repo_path,
            )
        )

    except Exception as exc:

        logger.exception(
            "Patch validation failed"
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return result.model_dump()


# ============================================================================
# APPLY
# ============================================================================

@router.post("/apply")
async def apply_patch(
    request: PatchApplyRequest,
):
    """
    Apply a patch.

    When the investigation exists, use its frozen original/modified state.

    When it does not exist, safely apply the supplied patch directly.
    """

    repo_path = get_repo_path(
        request.repo_path
    )

    investigation = get_investigation(
        request.investigation_id
    )

    expected_original_sha256 = ""
    expected_modified_code = ""

    if investigation is not None:

        expected_original_sha256 = (
            getattr(
                investigation,
                "original_sha256",
                "",
            )
        )

        expected_modified_code = (
            getattr(
                investigation,
                "modified_code",
                "",
            )
        )

        # Prevent applying to a different file.
        try:

            analyzed = normalize_path_for_compare(
                repo_path,
                investigation.file,
            )

            requested = normalize_path_for_compare(
                repo_path,
                request.target_file,
            )

            if analyzed != requested:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "The requested target file does not "
                        "match the file used during analysis."
                    ),
                )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    result = (
        patch_service.apply_patch(
            patch=request.patch,
            target_file=request.target_file,
            repo_path=repo_path,
            investigation_id=(
                request.investigation_id
            ),
            expected_original_sha256=(
                expected_original_sha256
            ),
            expected_modified_code=(
                expected_modified_code
            ),
        )
    )

    return result.model_dump()


# ============================================================================
# VERIFY
# ============================================================================

@router.post("/verify")
async def verify_patch(
    request: PatchApplyRequest,
):
    """
    Verify an approved patch.

    This endpoint deliberately does NOT require an investigation to exist.

    Why?

    The current frontend holds the investigation state, while backend
    investigations are currently in-memory. A backend reload can therefore
    erase the backend copy while the browser still has the investigation.

    Verification must remain usable in that situation.
    """

    repo_path = get_repo_path(
        request.repo_path
    )

    investigation = get_investigation(
        request.investigation_id
    )

    # ------------------------------------------------------------------------
    # Case A:
    # Investigation still exists.
    # ------------------------------------------------------------------------

    if investigation is not None:

        crash_file = (
            investigation.file
        )

        generated_test = (
            getattr(
                investigation,
                "test_case",
                "",
            )
            or ""
        )

        expected_original_sha256 = (
            getattr(
                investigation,
                "original_sha256",
                "",
            )
            or ""
        )

        expected_modified_code = (
            getattr(
                investigation,
                "modified_code",
                "",
            )
            or ""
        )

        target_file = (
            investigation.file
        )

        # Validate that the request refers to the same target.
        try:

            analyzed_target = (
                normalize_path_for_compare(
                    repo_path,
                    investigation.file,
                )
            )

            requested_target = (
                normalize_path_for_compare(
                    repo_path,
                    request.target_file,
                )
            )

            if (
                analyzed_target
                != requested_target
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Target file does not match "
                        "the investigation."
                    ),
                )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        try:

            report = (
                await verification_service.verify_fix(
                    patch=request.patch,
                    target_file=target_file,
                    repo_path=repo_path,
                    investigation_id=(
                        request.investigation_id
                    ),
                    generated_test=generated_test,
                    crash_file=crash_file,
                    expected_original_sha256=(
                        expected_original_sha256
                    ),
                    expected_modified_code=(
                        expected_modified_code
                    ),
                )
            )

        except Exception as exc:

            logger.exception(
                "Verification failed unexpectedly"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Verification error: {exc}"
                ),
            ) from exc

        # Update backend investigation.
        investigation.verification = (
            report
        )

        if report.overall_success:

            investigation.status = (
                "VERIFIED"
            )

        else:

            investigation.status = (
                "FAILED"
            )

        return report.model_dump()

    # ------------------------------------------------------------------------
    # Case B:
    # Backend lost investigation after reload/restart.
    #
    # Fall back to direct verification using the request.
    # ------------------------------------------------------------------------

    logger.warning(
        "Investigation %s was not found. "
        "Using stateless verification fallback.",
        request.investigation_id,
    )

    if not request.patch.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "No patch was supplied."
            ),
        )

    if not request.target_file.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "No target file was supplied."
            ),
        )

    # In stateless mode:
    #
    # - patch = request patch
    # - target_file = request target
    # - crash_file = same target
    # - no frozen modified source
    #
    # The patch service will validate the patch against the current source
    # before applying it.

    try:

        report = (
            await verification_service.verify_fix(
                patch=request.patch,
                target_file=request.target_file,
                repo_path=repo_path,
                investigation_id=(
                    request.investigation_id
                ),
                generated_test="",
                crash_file=request.target_file,
                expected_original_sha256="",
                expected_modified_code="",
            )
        )

    except Exception as exc:

        logger.exception(
            "Stateless verification failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Verification error: {exc}"
            ),
        ) from exc

    return report.model_dump()


# ============================================================================
# ROLLBACK
# ============================================================================

@router.post("/rollback")
async def rollback_patch(
    request: RollbackRequest,
):
    """
    Roll back an applied patch.

    The investigation is normally available, but we return a clear
    message when a backend restart removed the in-memory investigation.
    """

    repo_path = get_repo_path(
        request.repo_path
    )

    investigation = get_investigation(
        request.investigation_id
    )

    if investigation is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Investigation is no longer available "
                "in the backend process. "
                "Run a new analysis before using rollback."
            ),
        )

    target_file = (
        investigation.file
    )

    result = patch_service.rollback(
        backup_ref=request.backup_ref,
        target_file=target_file,
        repo_path=repo_path,
    )

    if result.success:

        investigation.status = (
            "ROLLED_BACK"
        )

    return result.model_dump()


# ============================================================================
# HISTORY
# ============================================================================

@router.get("/history")
async def patch_history():
    """Return patch history."""

    return [
        item.model_dump()
        for item
        in patch_service.get_patch_history()
    ]