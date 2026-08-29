"""Full AI investigation pipeline endpoint."""

from __future__ import annotations

import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import DEFAULT_REPO_PATH
from backend.models.analysis import Investigation, InvestigationStatus
from backend.models.crash import CrashRunResult
from backend.services.traceback_parser import parse_traceback, is_traceback
from backend.services.source_analyzer import get_source_context
from backend.services import git_service
from backend.services.ollama_service import ollama_service

logger = logging.getLogger("traceback.analysis")

router = APIRouter(tags=["analysis"])

# In-memory store (production would use DB)
_investigations: list[Investigation] = []


class AnalyzeRequest(BaseModel):
    traceback_text: str = ""
    crash_result: Optional[CrashRunResult] = None
    repo_path: str = DEFAULT_REPO_PATH
    explanation_mode: str = "developer"


class DemoRequest(BaseModel):
    repo_path: str = DEFAULT_REPO_PATH


@router.post("/analyze")
async def full_analysis(request: AnalyzeRequest):
    """Run the complete TraceBack investigation pipeline.

    Parse → Source → Git → AI → Patch → Test → Return investigation.
    """
    start = time.time()
    investigation = Investigation(repo_path=request.repo_path)
    investigation.status = InvestigationStatus.ANALYZING

    # ── 1. Parse traceback ─────────────────────────────────────────────
    raw_tb = ""
    if request.crash_result and request.crash_result.raw_traceback:
        raw_tb = request.crash_result.raw_traceback
    elif request.traceback_text:
        raw_tb = request.traceback_text
    else:
        raise HTTPException(status_code=400, detail="No traceback provided")

    if not is_traceback(raw_tb):
        raise HTTPException(status_code=400, detail="Input does not contain a Python traceback")

    parsed = parse_traceback(raw_tb)
    investigation.error_type = parsed.error_type
    investigation.error_message = parsed.message
    investigation.file = parsed.file
    investigation.line = parsed.line
    investigation.function = parsed.function
    investigation.raw_traceback = raw_tb

    # ── 2. Get source context ──────────────────────────────────────────
    source_ctx = get_source_context(
        parsed.file, parsed.line, repo_path=request.repo_path
    )
    investigation.source_context = source_ctx

    # ── 3. Git intelligence ────────────────────────────────────────────
    blame_info = None
    blame_str = ""
    if git_service.is_git_repo(request.repo_path) and parsed.file and parsed.line:
        blame_info = git_service.get_blame(request.repo_path, parsed.file, parsed.line)
        investigation.git_blame = blame_info
        if blame_info.author:
            blame_str = (
                f"Author: {blame_info.author}, "
                f"Commit: {blame_info.commit_hash}, "
                f"Message: {blame_info.commit_message}"
            )

    # ── 4. AI Investigation ────────────────────────────────────────────
    try:
        ai_result = await ollama_service.analyze_crash(
            error_type=parsed.error_type,
            error_message=parsed.message,
            source_code=source_ctx.content,
            file_path=parsed.file,
            line_number=parsed.line,
            function_name=source_ctx.function_name or parsed.function,
            git_blame=blame_str,
            traceback_raw=raw_tb,
        )

        investigation.severity = ai_result.severity
        investigation.confidence = ai_result.confidence
        investigation.root_cause = ai_result.root_cause
        investigation.explanation = ai_result.explanation
        investigation.fix_strategy = ai_result.fix_strategy
        investigation.patch = ai_result.patch
        investigation.test_case = ai_result.test_case
        investigation.potential_risks = ai_result.potential_risks
        investigation.status = InvestigationStatus.PATCH_READY if ai_result.patch else InvestigationStatus.DIAGNOSED

    except Exception as e:
        logger.error("AI analysis failed: %s", e)
        investigation.status = InvestigationStatus.DIAGNOSED
        investigation.root_cause = f"AI analysis unavailable: {e}"
        investigation.confidence = 0

    investigation.duration_ms = int((time.time() - start) * 1000)

    # Store investigation
    _investigations.append(investigation)

    return investigation.model_dump()


@router.post("/demo/run")
async def run_demo(request: DemoRequest):
    """Run the demo crash scenario end-to-end."""
    import subprocess
    import sys
    from pathlib import Path
    from backend.config import DEMO_PROJECT_DIR

    repo_path = request.repo_path or str(DEMO_PROJECT_DIR)
    auth_file = Path(repo_path) / "auth.py"

    if not auth_file.is_file():
        raise HTTPException(status_code=404, detail=f"Demo file not found: {auth_file}")

    # Run the buggy file
    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(auth_file)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Demo execution timed out")

    duration_ms = int((time.time() - start) * 1000)

    crash_result = CrashRunResult(
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        duration_ms=duration_ms,
        crashed=proc.returncode != 0,
        raw_traceback=proc.stderr if proc.returncode != 0 else "",
    )

    if proc.returncode != 0 and proc.stderr:
        parsed = parse_traceback(proc.stderr)
        crash_result.traceback = parsed

    return crash_result.model_dump()


@router.get("/investigations")
async def list_investigations():
    """List all investigations."""
    return [inv.model_dump() for inv in reversed(_investigations)]


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str):
    """Get a specific investigation by ID."""
    for inv in _investigations:
        if inv.id == investigation_id:
            return inv.model_dump()
    raise HTTPException(status_code=404, detail="Investigation not found")
