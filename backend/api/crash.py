"""Crash capture and traceback analysis endpoints."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.config import DEFAULT_REPO_PATH, PROJECT_ROOT
from backend.models.crash import CrashAnalyzeRequest, CrashRunRequest, CrashRunResult
from backend.services.traceback_parser import parse_traceback, is_traceback
from backend.services.source_analyzer import validate_path

router = APIRouter(prefix="/crash", tags=["crash"])


@router.post("/run", response_model=CrashRunResult)
async def run_crash(request: CrashRunRequest):
    """Run a Python file and capture the real crash."""
    # Validate the file path
    file_path = request.file_path
    cwd = request.cwd or DEFAULT_REPO_PATH

    # Resolve the file
    target = Path(cwd) / file_path if not Path(file_path).is_absolute() else Path(file_path)

    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not target.suffix == ".py":
        raise HTTPException(status_code=400, detail="Only Python files can be executed")

    # Validate path is within allowed directories
    try:
        validate_path(str(target), cwd)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Run the file
    cmd = [sys.executable, str(target)]
    if request.args:
        cmd.extend(request.args)

    start = time.time()

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=request.timeout,
        )

        duration_ms = int((time.time() - start) * 1000)
        crashed = proc.returncode != 0

        # Parse traceback from stderr
        parsed_tb = None
        raw_tb = ""
        if crashed and proc.stderr:
            raw_tb = proc.stderr
            if is_traceback(raw_tb):
                parsed_tb = parse_traceback(raw_tb)

        return CrashRunResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            duration_ms=duration_ms,
            crashed=crashed,
            traceback=parsed_tb,
            raw_traceback=raw_tb,
        )

    except subprocess.TimeoutExpired:
        return CrashRunResult(
            stderr=f"Execution timed out after {request.timeout}s",
            exit_code=-1,
            duration_ms=request.timeout * 1000,
            crashed=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")


@router.post("/analyze")
async def analyze_traceback(request: CrashAnalyzeRequest):
    """Parse a pasted traceback text."""
    text = request.traceback_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No traceback text provided")

    if not is_traceback(text):
        raise HTTPException(
            status_code=400,
            detail="Input does not appear to contain a Python traceback",
        )

    parsed = parse_traceback(text)
    return {
        "parsed": parsed.model_dump(),
        "repo_path": request.repo_path or DEFAULT_REPO_PATH,
    }


@router.post("/upload")
async def upload_log(file: UploadFile = File(...)):
    """Upload a log/trace file for analysis."""
    allowed_ext = {".log", ".txt", ".trace", ".json"}
    ext = Path(file.filename or "").suffix.lower()

    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_ext}",
        )

    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    if not is_traceback(text):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file does not contain a recognizable Python traceback",
        )

    parsed = parse_traceback(text)
    return {
        "parsed": parsed.model_dump(),
        "filename": file.filename,
        "repo_path": DEFAULT_REPO_PATH,
    }
