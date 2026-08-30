"""
TraceBack Analysis API.

Responsibilities:
- Run the crash-analysis pipeline.
- Capture the exact source used during analysis.
- Store original and modified source.
- Store hashes so stale investigations cannot silently modify files.
"""

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
    apply_unified_diff,
    normalize_patch,
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


# ============================================================================
# IN-MEMORY INVESTIGATION STORE
# ============================================================================

_investigations: list[
    Investigation
] = []


# ============================================================================
# REQUEST MODELS
# ============================================================================

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
    """Return supplied repository path or configured default."""

    value = (
        repo_path or ""
    ).strip()

    if value:
        return value

    return str(
        DEFAULT_REPO_PATH
    )


def source_sha256(
    source: str,
) -> str:
    """Calculate SHA-256 of source text."""

    return hashlib.sha256(
        source.encode(
            "utf-8"
        )
    ).hexdigest()


def find_investigation(
    investigation_id: str,
) -> Optional[Investigation]:
    """Find investigation in memory."""

    for investigation in _investigations:

        if (
            investigation.id
            == investigation_id
        ):
            return investigation

    return None


# ============================================================================
# ANALYZE
# ============================================================================

@router.post("/analyze")
async def full_analysis(
    request: AnalyzeRequest,
):
    """
    Analyze a crash.

    The important state captured here is:

        original_code
        original_sha256
        patch
        modified_code
        modified_sha256

    That frozen state is later used by Approve & Verify.
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
    # 1. GET RAW TRACEBACK
    # ========================================================================

    raw_traceback = ""

    if (
        request.crash_result
        and
        request.crash_result.raw_traceback
    ):

        raw_traceback = (
            request.crash_result.raw_traceback
        )

    elif (
        request.traceback_text
        and
        request.traceback_text.strip()
    ):

        raw_traceback = (
            request.traceback_text
        )

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "No traceback was supplied."
            ),
        )

    if not is_traceback(
        raw_traceback
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Input does not contain "
                "a valid Python traceback."
            ),
        )

    # ========================================================================
    # 2. PARSE TRACEBACK
    # ========================================================================

    try:

        parsed = parse_traceback(
            raw_traceback
        )

    except Exception as exc:

        logger.exception(
            "Traceback parsing failed"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not parse traceback: {exc}"
            ),
        ) from exc

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
        raw_traceback
    )

    # ========================================================================
    # 3. SOURCE CONTEXT
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
                f"Could not locate source for "
                f"{parsed.file}: {exc}"
            ),
        ) from exc

    # ========================================================================
    # 4. CAPTURE COMPLETE ORIGINAL SOURCE
    # ========================================================================

    try:

        actual_file = (
            source_context.file_path
            or parsed.file
        )

        original_code = (
            read_file_safe(
                actual_file,
                repo_path=repo_path,
            )
        )

        if not original_code:
            raise ValueError(
                "Source file is empty or could not be read."
            )

        investigation.original_code = (
            original_code
        )

        investigation.original_sha256 = (
            source_sha256(
                original_code
            )
        )

    except Exception as exc:

        logger.exception(
            "Original source capture failed"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not capture source: {exc}"
            ),
        ) from exc

    # ========================================================================
    # 5. GIT INTELLIGENCE
    # ========================================================================

    blame_text = ""

    try:

        if (
            parsed.file
            and
            parsed.line
            and
            git_service.is_git_repo(
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

                blame_text = (
                    f"Author: {blame.author}\n"
                    f"Commit: {blame.commit_hash}\n"
                    f"Message: {blame.commit_message}"
                )

    except Exception as exc:

        logger.warning(
            "Git intelligence unavailable: %s",
            exc,
        )

    # ========================================================================
    # 6. AI ANALYSIS
    # ========================================================================

    try:

        ai_result = (
            await ollama_service.analyze_crash(
                error_type=(
                    parsed.error_type
                ),
                error_message=(
                    parsed.message
                ),
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
                    or
                    parsed.function
                ),
                git_blame=(
                    blame_text
                ),
                traceback_raw=(
                    raw_traceback
                ),
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
            "AI crash analysis failed"
        )

        investigation.status = (
            InvestigationStatus.DIAGNOSED
        )

        investigation.root_cause = (
            f"AI analysis failed: {exc}"
        )

        investigation.confidence = 0

    # ========================================================================
    # 7. CREATE EXACT MODIFIED SOURCE
    # ========================================================================

    if investigation.patch:

        try:

            normalized_patch = (
                normalize_patch(
                    patch=investigation.patch,
                    repo_path=repo_path,
                    target_file=parsed.file,
                )
            )

            modified_code = (
                apply_unified_diff(
                    original=(
                        investigation.original_code
                    ),
                    patch=normalized_patch,
                )
            )

            if modified_code is None:
                raise ValueError(
                    "Generated patch does not match "
                    "the captured original source."
                )

            if (
                modified_code
                ==
                investigation.original_code
            ):
                raise ValueError(
                    "Generated patch produces no change."
                )

            investigation.modified_code = (
                modified_code
            )

            investigation.modified_sha256 = (
                source_sha256(
                    modified_code
                )
            )

            investigation.preview_available = (
                True
            )

        except Exception as exc:

            logger.warning(
                "Could not create modified-source preview: %s",
                exc,
            )

            investigation.modified_code = ""
            investigation.modified_sha256 = ""

            investigation.preview_available = (
                False
            )

            investigation.preview_error = (
                str(exc)
            )

    else:

        investigation.preview_available = (
            False
        )

        investigation.preview_error = (
            "AI did not produce a patch."
        )

    # ========================================================================
    # 8. FINALIZE
    # ========================================================================

    investigation.duration_ms = int(
        (time.time() - started)
        * 1000
    )

    _investigations.append(
        investigation
    )

    return investigation.model_dump()


# ============================================================================
# DEMO RUNNER
# ============================================================================

@router.post("/demo/run")
async def run_demo(
    request: DemoRequest,
):
    """Run bundled demo crash."""

    repo_path = (
        request.repo_path
        or
        str(DEMO_PROJECT_DIR)
    )

    repo = (
        Path(repo_path)
        .resolve()
    )

    target = (
        repo / "auth.py"
    )

    if not repo.is_dir():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Demo repository not found: {repo}"
            ),
        )

    if not target.is_file():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Demo file not found: {target}"
            ),
        )

    started = time.time()

    try:

        process = subprocess.run(
            [
                sys.executable,
                str(target),
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=30,
        )

    except subprocess.TimeoutExpired as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Demo execution timed out."
            ),
        ) from exc

    result = CrashRunResult(
        stdout=process.stdout,
        stderr=process.stderr,
        exit_code=process.returncode,
        duration_ms=int(
            (time.time() - started)
            * 1000
        ),
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
        and
        process.stderr
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
# INVESTIGATION LIST
# ============================================================================

@router.get("/investigations")
async def list_investigations():

    return [
        item.model_dump()
        for item
        in reversed(
            _investigations
        )
    ]


# ============================================================================
# INVESTIGATION DETAIL
# ============================================================================

@router.get(
    "/investigations/{investigation_id}"
)
async def get_investigation(
    investigation_id: str,
):

    investigation = (
        find_investigation(
            investigation_id
        )
    )

    if investigation is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Investigation not found."
            ),
        )

    return (
        investigation.model_dump()
    )