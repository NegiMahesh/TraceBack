"""TraceBack AI investigation pipeline."""

from __future__ import annotations

import hashlib
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import (
    DEFAULT_REPO_PATH,
    DEMO_PROJECT_DIR,
)

from backend.models.analysis import (
    Investigation,
    InvestigationStatus,
)

from backend.models.crash import (
    CrashRunResult,
)

from backend.services import (
    git_service,
)

from backend.services.ollama_service import (
    ollama_service,
)

from backend.services.patch_service import (
    preview_patch,
)

from backend.services.source_analyzer import (
    get_source_context,
    read_file_safe,
)

from backend.services.traceback_parser import (
    is_traceback,
    parse_traceback,
)


logger = logging.getLogger(
    "traceback.analysis"
)


router = APIRouter(
    tags=["analysis"]
)


# In-memory investigation store for hackathon.
_investigations: list[
    Investigation
] = []


class AnalyzeRequest(BaseModel):

    traceback_text: str = ""

    crash_result: Optional[
        CrashRunResult
    ] = None

    repo_path: Optional[
        str
    ] = None

    explanation_mode: str = (
        "developer"
    )


class DemoRequest(BaseModel):

    repo_path: Optional[
        str
    ] = None


# ============================================================================
# HELPERS
# ============================================================================

def normalize_repo_path(
    repo_path: Optional[str],
) -> str:

    value = (
        repo_path or ""
    ).strip()

    return (
        value
        if value
        else DEFAULT_REPO_PATH
    )


def source_hash(
    text: str,
) -> str:

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================================
# ANALYZE
# ============================================================================

@router.post("/analyze")
async def full_analysis(
    request: AnalyzeRequest,
):
    """
    Analyze one crash and freeze the exact source state used for analysis.

    The resulting investigation stores:
        original_code
        modified_code
        original_sha256
        modified_sha256

    Approval can therefore apply the exact code that was previewed.
    """

    started = time.time()

    repo_path = normalize_repo_path(
        request.repo_path
    )

    investigation = Investigation(
        repo_path=repo_path
    )

    investigation.status = (
        InvestigationStatus.ANALYZING
    )

    # ========================================================================
    # 1. TRACEBACK
    # ========================================================================

    raw_tb = ""

    if (
        request.crash_result
        and request.crash_result.raw_traceback
    ):

        raw_tb = (
            request.crash_result.raw_traceback
        )

    elif (
        request.traceback_text
        and request.traceback_text.strip()
    ):

        raw_tb = (
            request.traceback_text
        )

    else:

        raise HTTPException(
            status_code=400,
            detail="No traceback provided.",
        )

    if not is_traceback(
        raw_tb
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Input does not contain "
                "a Python traceback."
            ),
        )

    parsed = parse_traceback(
        raw_tb
    )

    investigation.error_type = (
        parsed.error_type
    )

    investigation.error_message = (
        parsed.message
    )

    investigation.file = (
        parsed.file
    )

    investigation.line = (
        parsed.line
    )

    investigation.function = (
        parsed.function
    )

    investigation.raw_traceback = (
        raw_tb
    )

    # ========================================================================
    # 2. SOURCE CONTEXT
    # ========================================================================

    try:

        source_context = (
            get_source_context(
                parsed.file,
                parsed.line,
                repo_path=repo_path,
            )
        )

        investigation.source_context = (
            source_context
        )

    except Exception as exc:

        logger.exception(
            "Source context lookup failed"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not locate source file: "
                f"{exc}"
            ),
        ) from exc

    # ========================================================================
    # 3. FULL ORIGINAL SOURCE SNAPSHOT
    # ========================================================================

    try:

        actual_file = (
            source_context.file_path
            or parsed.file
        )

        # Capture the ENTIRE source file,
        # not only the context snippet.
        original_code = (
            read_file_safe(
                actual_file,
                repo_path=repo_path,
            )
        )

        investigation.original_code = (
            original_code
        )

        investigation.original_sha256 = (
            source_hash(
                original_code
            )
        )

    except Exception as exc:

        logger.exception(
            "Could not capture original source"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not read source file: "
                f"{exc}"
            ),
        ) from exc

    # ========================================================================
    # 4. GIT
    # ========================================================================

    blame_string = ""

    try:

        if (
            parsed.file
            and parsed.line
            and git_service.is_git_repo(
                repo_path
            )
        ):

            blame = (
                git_service.get_blame(
                    repo_path,
                    parsed.file,
                    parsed.line,
                )
            )

            investigation.git_blame = (
                blame
            )

            if blame and blame.author:

                blame_string = (
                    f"Author: {blame.author}, "
                    f"Commit: {blame.commit_hash}, "
                    f"Message: {blame.commit_message}"
                )

    except Exception as exc:

        logger.warning(
            "Git information unavailable: %s",
            exc,
        )

    # ========================================================================
    # 5. AI
    # ========================================================================

    try:

        ai_result = (
            await ollama_service.analyze_crash(
                error_type=parsed.error_type,
                error_message=parsed.message,

                # Give AI the entire file so it can produce a correct patch.
                source_code=(
                    investigation.original_code
                ),

                file_path=(
                    parsed.file
                ),

                line_number=(
                    parsed.line
                ),

                function_name=(
                    source_context.function_name
                    or parsed.function
                ),

                git_blame=blame_string,

                traceback_raw=raw_tb,
            )
        )

        investigation.severity = (
            ai_result.severity
        )

        investigation.confidence = (
            ai_result.confidence
        )

        investigation.root_cause = (
            ai_result.root_cause
        )

        investigation.explanation = (
            ai_result.explanation
        )

        investigation.fix_strategy = (
            ai_result.fix_strategy
        )

        investigation.patch = (
            ai_result.patch
        )

        investigation.test_case = (
            ai_result.test_case
        )

        investigation.potential_risks = (
            ai_result.potential_risks
        )

        investigation.related_files = (
            ai_result.related_files
        )

        investigation.status = (
            InvestigationStatus.PATCH_READY
            if ai_result.patch
            else InvestigationStatus.DIAGNOSED
        )

    except Exception as exc:

        logger.exception(
            "AI analysis failed"
        )

        investigation.status = (
            InvestigationStatus.DIAGNOSED
        )

        investigation.root_cause = (
            f"AI analysis unavailable: {exc}"
        )

        investigation.confidence = 0

    # ========================================================================
    # 6. FREEZE MODIFIED SOURCE PREVIEW
    # ========================================================================

    if (
        investigation.patch
    ):

        try:

            modified_code = (
                _preview_against_snapshot(
                    original_code=(
                        investigation.original_code
                    ),
                    patch=(
                        investigation.patch
                    ),
                    file_path=(
                        parsed.file
                    ),
                    repo_path=repo_path,
                )
            )

            investigation.modified_code = (
                modified_code
            )

            investigation.modified_sha256 = (
                source_hash(
                    modified_code
                )
            )

            investigation.preview_available = (
                modified_code
                != investigation.original_code
            )

            if not investigation.preview_available:

                investigation.preview_error = (
                    "Generated patch produces "
                    "no actual source change."
                )

        except Exception as exc:

            logger.warning(
                "Patch preview failed: %s",
                exc,
            )

            investigation.modified_code = ""

            investigation.preview_available = (
                False
            )

            investigation.preview_error = (
                f"Could not create patch preview: {exc}"
            )

    else:

        investigation.preview_available = (
            False
        )

        investigation.preview_error = (
            "No patch was generated."
        )

    # ========================================================================
    # 7. FINALIZE
    # ========================================================================

    investigation.duration_ms = int(
        (time.time() - started)
        * 1000
    )

    _investigations.append(
        investigation
    )

    return investigation.model_dump()


def _preview_against_snapshot(
    original_code: str,
    patch: str,
    file_path: str,
    repo_path: str,
) -> str:
    """
    Preview patch against the captured source snapshot.

    We temporarily use the repository source only to reuse the normalized
    patch path. The actual transformation is performed against the snapshot.
    """

    from backend.services.patch_service import (
        apply_unified_diff,
        normalize_patch,
    )

    normalized_patch = normalize_patch(
        patch=patch,
        repo_path=repo_path,
        target_file=file_path,
    )

    modified = apply_unified_diff(
        original=original_code,
        patch=normalized_patch,
    )

    if modified is None:
        raise ValueError(
            "Patch does not match the source captured during analysis."
        )

    return modified


# ============================================================================
# DEMO
# ============================================================================

@router.post("/demo/run")
async def run_demo(
    request: DemoRequest,
):

    repo_path = (
        request.repo_path
        or str(DEMO_PROJECT_DIR)
    )

    repo = Path(
        repo_path
    ).resolve()

    auth_file = (
        repo / "auth.py"
    )

    if not repo.is_dir():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Demo repository not found: "
                f"{repo}"
            ),
        )

    if not auth_file.is_file():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Demo file not found: "
                f"{auth_file}"
            ),
        )

    started = time.time()

    try:

        process = subprocess.run(
            [
                sys.executable,
                str(auth_file),
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=30,
        )

    except subprocess.TimeoutExpired:

        raise HTTPException(
            status_code=500,
            detail=(
                "Demo execution timed out."
            ),
        )

    duration_ms = int(
        (time.time() - started)
        * 1000
    )

    result = CrashRunResult(
        stdout=process.stdout,
        stderr=process.stderr,
        exit_code=process.returncode,
        duration_ms=duration_ms,
        crashed=(
            process.returncode != 0
        ),
        raw_traceback=(
            process.stderr
            if process.returncode != 0
            else ""
        ),
    )

    if (
        process.returncode != 0
        and process.stderr
    ):

        try:

            result.traceback = (
                parse_traceback(
                    process.stderr
                )
            )

        except Exception:

            logger.warning(
                "Could not parse demo traceback",
                exc_info=True,
            )

    return result.model_dump()


# ============================================================================
# INVESTIGATIONS
# ============================================================================

@router.get("/investigations")
async def list_investigations():

    return [
        investigation.model_dump()
        for investigation
        in reversed(
            _investigations
        )
    ]


@router.get(
    "/investigations/{investigation_id}"
)
async def get_investigation(
    investigation_id: str,
):

    for investigation in _investigations:

        if (
            investigation.id
            == investigation_id
        ):

            return (
                investigation.model_dump()
            )

    raise HTTPException(
        status_code=404,
        detail="Investigation not found.",
    )