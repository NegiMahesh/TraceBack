"""Git intelligence endpoints — blame, log, status, diff."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.config import DEFAULT_REPO_PATH
from backend.services import git_service

router = APIRouter(prefix="/git", tags=["git"])


@router.get("/status")
async def git_status(repo_path: str = Query(default=DEFAULT_REPO_PATH)):
    """Get Git status for the repository."""
    return git_service.get_status(repo_path)


@router.get("/blame")
async def git_blame(
    file: str = Query(..., description="File path"),
    line: int = Query(..., description="Line number"),
    repo_path: str = Query(default=DEFAULT_REPO_PATH),
):
    """Get git blame for a specific line."""
    info = git_service.get_blame(repo_path, file, line)
    return info.model_dump()


@router.get("/history")
async def git_history(
    file: str = Query(default=None, description="Optional file path to filter"),
    count: int = Query(default=20, le=100),
    repo_path: str = Query(default=DEFAULT_REPO_PATH),
):
    """Get recent Git history."""
    return {"commits": git_service.get_log(repo_path, max_count=count, file_path=file)}


@router.get("/diff")
async def git_diff(repo_path: str = Query(default=DEFAULT_REPO_PATH)):
    """Get current uncommitted diff."""
    return {"diff": git_service.get_diff(repo_path)}
