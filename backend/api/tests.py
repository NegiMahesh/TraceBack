"""Test execution endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import DEFAULT_REPO_PATH
from backend.services import test_service

router = APIRouter(
    prefix="/tests",
    tags=["tests"],
)


class RunTestRequest(BaseModel):
    target: str = Field(
        default="",
        description="Specific test file or directory",
    )

    repo_path: Optional[str] = Field(
        default=None,
        description="Repository path. Uses default when omitted.",
    )


@router.post("/run")
async def run_tests(
    request: RunTestRequest,
):
    """Run pytest and return real results."""

    repo_path = (
        request.repo_path
        or DEFAULT_REPO_PATH
    )

    result = test_service.run_pytest(
        target=request.target or None,
        cwd=repo_path,
    )

    return result.model_dump()


@router.post("/run-file")
async def run_file(
    file_path: str = Query(...),
    repo_path: Optional[str] = Query(default=None),
):
    """Run a Python file and capture output."""

    working_repo = (
        repo_path
        or DEFAULT_REPO_PATH
    )

    try:
        result = test_service.run_python_file(
            file_path=file_path,
            cwd=working_repo,
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"File execution failed: {exc}",
        ) from exc