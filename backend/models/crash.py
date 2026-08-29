"""Pydantic models for crash/traceback data."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TracebackFrame(BaseModel):
    """A single frame in a Python traceback."""

    file: str = Field(..., description="Source file path")
    line: int = Field(..., description="Line number")
    function: str = Field(..., description="Function or module name")
    code: str = Field("", description="Source line text")


class ParsedTraceback(BaseModel):
    """Structured representation of a Python traceback."""

    error_type: str = Field(..., description="Exception class name")
    message: str = Field("", description="Error message")
    file: str = Field("", description="File where error occurred (innermost frame)")
    line: int = Field(0, description="Line number of the error")
    function: str = Field("", description="Function where error occurred")
    frames: list[TracebackFrame] = Field(default_factory=list)
    raw: str = Field("", description="Original traceback text")


class CrashRunRequest(BaseModel):
    """Request to run a Python file and capture its crash."""

    file_path: str = Field(..., description="Path to Python file to run")
    args: list[str] = Field(default_factory=list, description="Arguments to pass")
    cwd: Optional[str] = Field(None, description="Working directory")
    timeout: int = Field(30, description="Max seconds to wait")


class CrashRunResult(BaseModel):
    """Result of running a Python file."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    crashed: bool = False
    traceback: Optional[ParsedTraceback] = None
    raw_traceback: str = ""


class CrashAnalyzeRequest(BaseModel):
    """Request to analyze a pasted traceback or log."""

    traceback_text: str = Field("", description="Pasted traceback text")
    repo_path: Optional[str] = Field(None, description="Repository path for source lookup")
