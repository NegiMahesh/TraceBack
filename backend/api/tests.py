"""Test execution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.config import DEFAULT_REPO_PATH
from backend.services import test_service

router = APIRouter(prefix="/tests", tags=["tests"])


class RunTestRequest(BaseModel):
    target: str = Field(default="", description="Specific test file or directory")
    repo_path: str = DEFAULT_REPO_PATH


@router.post("/run")
async def run_tests(request: RunTestRequest):
    """Run pytest and return real results."""
    result = test_service.run_pytest(
        target=request.target or None,
        cwd=request.repo_path,
    )
    return result.model_dump()


@router.post("/run-file")
async def run_file(
    file_path: str = Query(...),
    repo_path: str = Query(default=DEFAULT_REPO_PATH),
):
    """Run a Python file and capture output."""
    result = test_service.run_python_file(file_path, cwd=repo_path)
    return result
